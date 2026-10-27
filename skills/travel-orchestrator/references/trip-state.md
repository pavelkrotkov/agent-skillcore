# Current trip state

Keep one authoritative current constraint record for a trip. Search plans, comparisons, totals, rankings, recommendations, and provenance are derived from that record; they are not independent memories that may drift.

## Constraint record

Use generic traveler labels and counts. Record only what affects planning:

- a constraint revision identifier;
- destination(s) and trip-wide component constraints such as cabin, bags, cancellation, ground transport, and points mode/balances when relevant;
- each traveler group's label/count, origin, departure and return dates, booked-versus-planned status;
- each confirmed component's type, generic party scope, and booked status; keep its detailed confirmation fields in [booking-reconciliation.md](booking-reconciliation.md);
- lodging check-in/check-out and occupancy for each overlapping group;
- shared-car responsibility or handoff;
- hard arrival/departure deadlines and required buffers;
- event dates separately from travel dates and planning deadlines;
- scoped preferences and explicit exclusions;
- source-backed event observations and user-confirmed planning constraints.

Do not merge groups merely because they share a destination. A booked group is invariant across a refresh unless the user explicitly changes that booking. Confirmation for one group or component never proves another group's booking.

## Verify the actual season

When school, team, tournament, conference, or similar dates constrain travel:

1. inspect the official current-season team/organization source and the event source it links to;
2. never roll a prior season's dates forward;
3. deduplicate observations that describe the same event while retaining every source, retrieval date, and observed value;
4. classify the event as `confirmed`, `tentative`, or `conflicting`;
5. preserve a user-confirmed planning constraint even when official sources disagree, and show the discrepancy instead of silently selecting a winner.

Use the provenance record in [provenance.md](provenance.md) for source URL/tool, `queried_at`, observed value, and confidence. Event identity and source identity are different: deduplicating two pages about one event must not erase either observation.

## Refresh semantics

Any change to dates, groups, origin, occupancy, shared-car duty, hard deadline, applicable preference, or confirmed booking fact creates a new current constraint revision. Recompute every current overview, table, total, ranking, recommendation, and provenance block from that revision.

A newly confirmed or corrected component invalidates contradictory current labels: a confirmed rental cannot coexist with a current “no car booked” recommendation. Keep the prior recommendation only as archived research.

Move superseded date/price comparisons under an unmistakable `ARCHIVED — superseded` heading. Archived research is evidence, not a current candidate. Preserve destination facts and other research whose truth does not depend on the changed constraint.

Never mutate an already booked group's dates just to make a comparison matrix uniform. Never extend a later group's return to another group's return date. A hard deadline plus buffer is a feasibility boundary, not a soft scoring preference.

## Preference scope

Attach preferences to the narrowest useful scope: trip/season, component, traveler group, or decision. Do not treat a preference as a permanent rule unless the user made it one.

Examples:

- a Christmas ski-duration preference does not constrain a spring trip;
- a preferred rental platform is not an exclusion, especially after the user asks to compare another platform;
- a group's cabin preference does not silently apply to a different group unless stated.

## Toolkit reconciliation

Toolkit `trip-planner` and `plan-trip` examples model one origin, one departure/return pair, one traveler count, and one hotel window. For split parties, use those templates separately for each group/window and then combine the resulting components under this record. Local hard constraints, booked groups, and current-versus-archived state take precedence over template defaults.

Source deduplication is not idea deduplication: two sources describing the same event may collapse to one event record with two observations, while two materially different itinerary or lodging ideas remain separate candidates even when one source produced both.
