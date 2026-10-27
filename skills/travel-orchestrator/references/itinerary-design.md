# Itinerary design

## Procedure

1. Start from the current constraint revision in [trip-state.md](trip-state.md). Separate hard constraints from scoped preferences and build candidate bundles per traveler group plus shared components: ordinary round trip, open jaw, multi-city, rail/ferry plus flight, alternate gateway, and (only if worthwhile) positioning or split tickets.
2. For open jaws, price the arrival and departure gateways independently and add intercity transport, luggage, overnight stops, and airport access. Compare the result to a conventional round trip before claiming savings.
3. For positioning or split tickets, calculate buffer time, airport/terminal changes, immigration, baggage reclaim/recheck, missed-connection exposure, and the cost of an overnight fallback. Mark the itinerary as self-transfer and apply a risk penalty.
4. Prefer protected connections with sensible buffers. Penalize overnight airport waits, very early departures, long backtracks, two-ticket tight connections, and itineraries requiring a visa or border crossing the traveler may not satisfy. Reject any candidate that violates a group's hard arrival deadline or required buffer even if it is cheaper.
5. Use Toolkit `plan-trip`/`trip-planner` first, but fan out distinct groups and lodging occupancy windows explicitly instead of inheriting their single-party examples. Use `trvl` `plan-all`, `multimodal`, `multi-city`, `route`, or optimizer expansion when it can price a missing leg or test an alternative. Browser-verify only the chosen bundle’s material legs.

## Sources and confidence

- High: [Toolkit trip-planner skill](https://github.com/borski/travel-hacking-toolkit/blob/main/plugins/travel-hacking-toolkit/skills/trip-planner/SKILL.md); [trvl complete setup](https://raw.githubusercontent.com/MikkoParkkola/trvl/main/AGENTS.md).
- Medium: [Google Flights official guidance on airport and convenience trade-offs](https://support.google.com/travel/answer/7664728?hl=en).
- Safety inference: a lower headline fare cannot outrank a protected itinerary until the full failure cost is modeled.
