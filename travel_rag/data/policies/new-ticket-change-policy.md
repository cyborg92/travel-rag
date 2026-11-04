# SkyTrail Airways Ticket Change Policy

> **Training notice:** This is a fictional policy created for a synthetic TravelAssist RAG dataset. It does not represent a real airline.

## 1. Scope

This policy covers voluntary changes to travel date, flight, time, or routing. Name correction and airline-caused changes follow separate rules.

A voluntary change normally requires payment of:

`change fee + positive fare difference + applicable tax difference`

If the new fare is lower, the difference is not refunded for Economy Lite tickets. For Economy Flex and Business Flex, the difference is issued as a travel credit valid for 12 months from the original ticket issue date.

## 2. Domestic change fees

| Time before scheduled departure | Economy Lite | Economy Flex | Business Flex |
|---|---:|---:|---:|
| More than 72 hours | INR 2,000 | INR 500 | No fee |
| 24 to 72 hours | INR 3,000 | INR 1,000 | INR 500 |
| 3 to 24 hours | INR 4,000 | INR 2,000 | INR 1,000 |
| Less than 3 hours | Not permitted | Not permitted | INR 2,500 |

## 3. International change fees

| Time before scheduled departure | Economy Lite | Economy Flex | Business Flex |
|---|---:|---:|---:|
| More than 72 hours | Up to INR 7,000 | Up to INR 3,500 | INR 1,000 |
| 24 to 72 hours | Up to INR 10,000 | Up to INR 5,000 | INR 2,500 |
| 4 to 24 hours | Up to INR 12,500 | Up to INR 7,000 | INR 4,000 |
| Less than 4 hours | Not permitted | Not permitted | Up to INR 7,000 |

A sector-specific fare rule stored with the ticket takes priority over the general international fee table.

## 4. Fare difference

The passenger must pay any increase between the original fare and the currently available fare. A fee waiver does not automatically waive the fare difference.

### Worked example

An Economy Flex passenger changes a domestic flight 40 hours before departure:

- change fee: INR 1,000;
- old fare: INR 6,500;
- new available fare: INR 7,300;
- fare difference: INR 800;
- total additional collection: INR 1,800, excluding any tax adjustment.

## 5. Same-day flight change

Business Flex passengers may request standby on an earlier flight on the same route and date without a change fee. Confirmation depends on seat availability. A confirmed move to another flight may still require a fare difference.

## 6. Name corrections

Minor corrections of up to three characters may be permitted once without a change fee when the passenger remains the same person. Transfer of a ticket to another person is not permitted.

## 7. Multi-sector and return bookings

1. A change to one sector may recalculate the fare for the complete journey.
2. Missing an outbound sector may automatically cancel later sectors unless protected by an agent.
3. For a return fare, changing the outbound flight can affect the price and validity of the return flight.
4. Partner-operated sectors require confirmation from the operating carrier.

## 8. Change process and confirmation

A quoted option is not a completed change. The system must present the new itinerary, fee, fare difference, and total amount, then obtain explicit passenger confirmation before ticket reissue.

A quote may expire if availability or price changes. The final stored proposal, rather than client-supplied replacement parameters, must be used during confirmation.

## 9. Exceptions

- Changes caused by a qualifying disruption are handled under `disruption-policy.md` and may be free of charge.
- Medical waiver requests require documentation and manual review.
- Tickets marked non-changeable cannot be changed unless an involuntary-disruption rule applies.

## 10. Related policies

See `cancellation-policy.md` if the passenger no longer intends to travel, and `baggage-policy.md` because baggage allowance may change with the new route, cabin, or operating carrier.
