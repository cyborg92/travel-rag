from app.mock_backend import bookings, fares


def test_every_booking_fare_class_has_a_fare_code_and_rule() -> None:
    for booking in bookings._BOOKINGS.values():
        code = fares.FARE_CODE_BY_CLASS[booking.fare_class]
        assert code in fares.FARE_RULES


def test_every_booking_route_has_a_base_fare_for_its_class() -> None:
    for booking in bookings._BOOKINGS.values():
        pricing_class = fares.FARE_CLASS_PRICING_ALIAS.get(
            booking.fare_class, booking.fare_class
        )
        route = (booking.origin, booking.destination)
        assert pricing_class in fares.BASE_FARE_INR[route]


def test_fee_tables_cover_every_changeable_class_in_every_band() -> None:
    changeable = {
        cls
        for cls, code in fares.FARE_CODE_BY_CLASS.items()
        if fares.FARE_RULES[code].changeable
    }
    for table in (fares.DOMESTIC_CHANGE_FEES, fares.INTERNATIONAL_CHANGE_FEES):
        bounds = [bound for bound, _ in table]
        assert bounds == sorted(bounds, reverse=True)
        for _, fees in table:
            assert set(fees) == changeable


def test_only_restricted_fare_is_non_changeable() -> None:
    non_changeable = [c for c, r in fares.FARE_RULES.items() if not r.changeable]
    assert non_changeable == ["FARE-K"]
