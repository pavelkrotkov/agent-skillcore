# Airport coverage and usable time

Build airport coverage from the current constraint revision, then rank feasible options by complete travel logistics rather than airfare or road distance alone.

## Coverage matrix

Derive a bounded airport set for each traveler group from the airports the user named or accepted, practical metro airports inside the stated access tolerance, materially different carrier/service options just outside that default set, and alternate arrival gateways that can change a road-trip or shared-ground plan. Do not freeze an illustrative airport list as universal. For a NY/NJ-origin request, for example, EWR/JFK/LGA may be the obvious starting set while PHL/ABE/SWF/HPN are considered only when the group's access tolerance, carrier evidence, schedule, or fare makes them relevant.

For flexible road-trip/open-jaw geography, search both gateway directions when the trip order is not fixed. For split groups, keep separate matrices and reconcile only shared ground components.

Expose one row per material group × airport pair × direction × date/length window × carrier/source combination:

`group | origin | destination | direction | date_or_length_window | carrier | source | attempt | reason | availability_state | observed_through | evidence`

- `attempt=searched` only after a valid query ran.
- `attempt=skipped` requires a reason and `availability_state=not_searched`.
- `attempt=unavailable` requires the unavailable/blocked/unsupported reason and the matching state from [provenance.md](provenance.md).
- Preserve `calendar_not_open`, `no_result`, `unavailable_exact_dates`, and other availability states exactly; do not collapse them into “no flights.”

Bound the matrix before searching: include alternatives that can plausibly change the decision, not every airport or carrier within an arbitrary radius.

## Carrier blind spots

Structured-source omission is not proof that a carrier does not serve a route. After the Toolkit search and any useful `trvl` expansion, directly inspect a materially relevant carrier's current route/schedule/calendar when a missing ULCC or small-airport option could change the recommendation. This is gap verification, not a browser-first replacement for structured search.

Keep service evidence separate from exact dated inventory:

- a current carrier route map or schedule can establish that service exists or is planned, but not that seats exist on the target dates;
- exact inventory requires a matching dated search inside the carrier's observed booking horizon;
- record the retrieval time and `observed_through`; a target beyond that horizon is `calendar_not_open`, not unavailable or discontinued;
- `no_result` never proves discontinued service without current authoritative schedule evidence.

## Logistics and ranking

For each feasible flight candidate compare the same travel-component scope:

- fare plus required bags/seats and other flight add-ons from [airfare-search.md](airfare-search.md);
- origin access time/cost, tolls, parking, and any user-permitted airport hotel/overnight or early-departure logistics;
- destination transfer, rental/ride/rail cost and time, one-way/drop or airport-relocation costs where relevant;
- outbound and return door-to-door elapsed time, including layovers and required buffers;
- connection protection, separate-ticket/positioning exposure, baggage recheck, and fallback burden.

Report usable vacation time alongside cost: the trip window minus outbound/return travel and mandatory airport/ground repositioning that consumes the trip. Use hours when partial days matter and do not count a transit-heavy calendar day as fully usable.

Apply hard constraints first. Among feasible candidates, compare all-in travel-component cost, usable time, and risk; do not reject a user-accepted airport merely because its drive is slightly longer if it avoids a much worse flight schedule. A permitted overnight or very early flight stays in the comparison with its explicit cost/time burden instead of being silently discarded. Do not invent a dollar value for vacation time unless the user supplies one; expose the cost/time frontier when neither option dominates.

For shared cars or transfers across split groups, a candidate is compatible only when the handoff/return airports and times work, or when the relocation cost/time is explicitly modeled. Never rank each group's cheapest flight independently and assume the shared ground plan still works.

## Toolkit reconciliation

Toolkit nearby-airport, trip-planner, and cheapest-flight examples are candidate generation only. This matrix controls local coverage and ranking when those templates omit accepted airports, carrier-specific service, reversed open jaws, split-group ground compatibility, or complete access/transfer time.

## Sources and confidence

- High: [Google Flights fare-search help](https://support.google.com/travel/answer/7664728?hl=en) for airport/date and price-versus-convenience search dimensions.
- High: [trvl setup and search protocol](https://raw.githubusercontent.com/MikkoParkkola/trvl/main/AGENTS.md) for nearby-airport/date-grid/route expansion behavior.
- Carrier route maps, schedules, and calendars are authoritative only for the service/horizon actually observed; exact dated inventory still requires an exact matching search.
