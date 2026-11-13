import pytest

from app.mock_backend.fares import fare_for, fee_for, route_scope


@pytest.mark.parametrize(
    ("origin", "destination", "expected"),
    [
        ("DEL", "BOM", "domestic"),
        ("BLR", "DXB", "international"),
        ("DXB", "BLR", "international"),  # origin abroad, destination domestic
        ("XXX", "YYY", "international"),
    ],
)
def test_route_scope(origin: str, destination: str, expected: str) -> None:
    assert route_scope(origin, destination) == expected


@pytest.mark.parametrize(
    ("scope", "fare_class", "hours_left", "expected"),
    [
        ("domestic", "Economy Flex", 100, 500),
        ("domestic", "Economy Flex", 73, 500),
        ("domestic", "Economy Flex", 72, 1000),  # boundary goes to the later band
        ("domestic", "Economy Flex", 48, 1000),
        ("domestic", "Economy Flex", 24, 2000),
        ("domestic", "Economy Flex", 3, None),
        ("domestic", "Economy Flex", 2, None),
        ("domestic", "Business Flex", 2, 2500),
        ("domestic", "Economy Lite", 100, 2000),
        ("international", "Economy Flex", 191, 3500),
        ("international", "Economy Flex", 4, None),
        ("international", "Business Flex", 3, 7000),
    ],
)
def test_fee_for(scope: str, fare_class: str, hours_left: float, expected) -> None:
    assert fee_for(scope, fare_class, hours_left) == expected


def test_fee_for_restricted_fare_is_a_data_error() -> None:
    with pytest.raises(KeyError):
        fee_for("domestic", "Economy Lite Restricted", 100)


@pytest.mark.parametrize(
    ("route", "fare_class", "iso_date", "expected"),
    [
        (("BLR", "DXB"), "Economy Flex", "2026-11-20", 24000),
        (("BLR", "DXB"), "Economy Flex", "2026-11-21", 24800),
        (("BLR", "DXB"), "Economy Flex", "2026-11-22", 23500),
        (("BOM", "DEL"), "Economy Flex", "2026-12-11", 8000),
        (("DEL", "BOM"), "Economy Lite Restricted", "2026-11-21", 6000),  # alias
    ],
)
def test_fare_for(route: tuple, fare_class: str, iso_date: str, expected: int) -> None:
    assert fare_for(*route, fare_class, iso_date) == expected


def test_fare_for_unknown_route_is_a_data_error() -> None:
    with pytest.raises(KeyError):
        fare_for("XXX", "YYY", "Economy Flex", "2026-11-21")
