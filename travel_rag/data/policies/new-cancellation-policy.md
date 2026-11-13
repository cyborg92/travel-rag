# SkyTrail Airways Cancellation and Refund Policy

> **Training notice:** This is a fictional policy created for a synthetic TravelAssist RAG dataset. It does not represent a real airline.

## 1. Scope

This policy applies to voluntary cancellation of tickets issued on SkyTrail Airways ticket stock. Airline-caused cancellations are handled under `disruption-policy.md`.

## 2. Domestic cancellation fees

| Time before scheduled departure | Economy Lite | Economy Flex | Business Flex |
|---|---:|---:|---:|
| More than 72 hours | INR 2,500 | INR 1,000 | No fee |
| 24 to 72 hours | INR 3,500 | INR 1,750 | INR 750 |
| 3 to 24 hours | INR 4,500 | INR 2,500 | INR 1,500 |
| Less than 3 hours or after departure | Non-refundable | Non-refundable | INR 3,000 |

The cancellation fee is limited to the base fare plus carrier surcharge. Government taxes that are refundable by law remain eligible for refund.

## 3. International cancellation fees

| Time before scheduled departure | Economy Lite | Economy Flex | Business Flex |
|---|---:|---:|---:|
| More than 72 hours | Up to INR 8,000 | Up to INR 4,000 | INR 1,500 |
| 24 to 72 hours | Up to INR 11,000 | Up to INR 6,000 | INR 3,000 |
| 4 to 24 hours | Up to INR 14,000 | Up to INR 8,000 | INR 5,000 |
| Less than 4 hours or after departure | Non-refundable | Non-refundable | Up to INR 8,000 |

Country-specific consumer rules may override these amounts. When a sector-specific rule is available in the fare record, that rule takes priority.

## 4. Refund calculation

The refundable amount is calculated as:

`amount paid - cancellation fee - non-refundable add-ons + refundable taxes`

A refund may be zero when the applicable fee equals or exceeds the refundable fare component.

## 5. Refund method and timeline

1. Refunds are returned to the original form of payment.
2. Card refunds are initiated within 7 business days after approval.
3. Bank or wallet settlement times may add a further 5 to 10 business days.
4. Agency-issued tickets must normally be refunded by the issuing agency.

## 6. Special cases

### Duplicate booking

A duplicate booking reported within 4 hours of purchase may be cancelled without a fee when the passenger, route, and travel date are identical.

### Medical or bereavement request

A passenger may request a fee waiver with supporting documents. Approval is discretionary and must not be promised before review.

### Partially used ticket

For a partially used ticket, the flown-sector value and applicable fees are deducted before any refund is calculated.

### No-show

A passenger is treated as a no-show when cancellation is not completed before the minimum cut-off shown in the tables. No-show rules may also cause onward sectors in the same booking to be cancelled.

## 7. Non-refundable items

The following are normally non-refundable after use or after the service cut-off:

- seat-selection fees;
- priority boarding;
- lounge access;
- meals already supplied;
- travel-protection fees charged by a third party.

Unused prepaid baggage may be refunded only when cancellation occurs more than 24 hours before departure.

## 8. Examples

- A Domestic Economy Flex ticket cancelled 50 hours before departure attracts an INR 1,750 fee.
- A Domestic Business Flex ticket cancelled 80 hours before departure has no cancellation fee.
- An Economy Lite passenger who cancels after departure receives only taxes that remain refundable under applicable rules.

## 9. Related policies

For date or flight changes, see `ticket-change-policy.md`. For airline-caused cancellation, misconnection, or major delay, see `disruption-policy.md`.

## 10. Waiver reference codes

Agents record the reason for a fee waiver using a waiver reference code.

| Code | Meaning | Condition |
|---|---|---|
| CXL-DUP-4H | Duplicate-booking waiver | Reported within 4 hours of purchase, with identical passenger, route, and travel date. |
| CXL-MED-DOC | Medical or bereavement waiver | Supporting documents were submitted. Approval is discretionary and manual review is required. |
| CXL-IROP | Involuntary disruption | Airline-caused cancellation handled under `disruption-policy.md`. |
