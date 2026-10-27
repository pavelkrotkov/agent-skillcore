# Points and awards

## Procedure

1. Start with Toolkit `trip-planner` or `compare-flights`; for awards load `lessons-learned`, `seats-aero`, `partner-awards`, `award-calendar`, `award-holds`, and `points-valuations` as relevant. Search several programs that can ticket the operating carrier, not just the user’s preferred currency.
2. Search a date range and nearby gateways when possible. Treat aggregator availability as a candidate, not a seat guarantee. Recheck the operating carrier and the program that will issue the ticket before calling it bookable.
3. Compute real value in cents per point: `((comparable cash fare - award taxes/surcharges/fees) / points used) * 100`. For example, `$1,400` of net value on `100,000` points is `1.4 cpp`, not `0.014 cpp`. Include transfer-bonus effects, opportunity cost, positioning flights, hotel/ground add-ons, and the cash value of companion benefits. Do not treat a large mileage number with high surcharges as a good redemption by default.
4. Check routing, connection protection, mixed-cabin segments, married-segment behavior, change/cancel terms, and award holds before transferring points. Never transfer speculatively when the program cannot hold the space and transfers are irreversible.
5. Use `trvl` `awards` or `points-value` only as a selective independent scan/cross-check. Preserve both program and source prices when they differ, and verify the final award on the issuer’s live site or app.

## Interpretation

Seats.aero’s own guide describes a continuously refreshed availability database, but community reports show phantom/stale results and direct-program mismatches. The Toolkit’s local points skill explicitly requires total out-of-pocket cost, surcharge checks, transfer-bonus checks, and freshness checks for valuation data. These are high-confidence workflow rules; program-specific rates and hold policies are dynamic and need live verification.

## Sources and confidence

- High: [Seats.aero getting started](https://seats.aero/guides/gettingstarted); [Toolkit points-valuations skill](https://github.com/borski/travel-hacking-toolkit/blob/main/plugins/travel-hacking-toolkit/skills/points-valuations/SKILL.md); [Toolkit lessons-learned skill](https://github.com/borski/travel-hacking-toolkit/blob/main/plugins/travel-hacking-toolkit/skills/lessons-learned/SKILL.md).
- Medium/community: [awardtravel guidance to verify aggregator space directly](https://www.reddit.com/r/awardtravel/comments/1r26fus/award_finder_tools_are_they_worth_it/) and [Flying Blue freshness report](https://www.reddit.com/r/awardtravel/comments/1cxi1z0/seatsaero_is_not_reliable_for_flying_blue_klm_award_flights/).
