# Anti-patterns

- “Tuesday is always cheapest.” Search the actual date matrix; booking-day folklore is not a search result.
- Headline fare ranking. Add bags, seats, transfers, parking, fees, and the party multiplier.
- Metro-airport omission. A nearby airport can lower the fare but lose after rail, parking, time, baggage, or an overnight.
- Treating self-transfer as a connection. Separate tickets have separate failure responsibility and baggage rules.
- Award-aggregator certainty. Availability can be stale, phantom, married-segment-limited, or program-specific; verify directly.
- Hotel lead-in prices. A hotel list price is not a room-level, tax-inclusive, cancellable offer.
- Cross-seller term mixing. Never pair seller A’s price with seller B’s cancellation or breakfast.
- Browser-first search. Browser automation is slower, brittle, and often less structured; reserve it for gaps/final verification.
- False exhaustiveness. Say which airports, dates, sources, room types, and programs were searched and which were unavailable.
- Unmarked estimates. Label cached, inferred, currency-converted, or modeled values and downgrade confidence.
- Silent disagreement resolution. Preserve both observations and investigate; do not silently choose the cheaper quote.
- Credential or cookie overreach. Do not reuse browser cookies, install optional keys, book, transfer points, or expose data without explicit permission.

Sources: [Google’s official fare-search guidance](https://support.google.com/travel/answer/7664728?hl=en), [trvl’s documented cookie and price behavior](https://github.com/MikkoParkkola/trvl), [Toolkit lessons learned](https://github.com/borski/travel-hacking-toolkit/blob/main/plugins/travel-hacking-toolkit/skills/lessons-learned/SKILL.md), and [FTC lodging-fee guidance](https://www.ftc.gov/news-events/news/press-releases/2025/05/ftc-rule-unfair-or-deceptive-fees-take-effect-may-12-2025). Confidence: high for the procedural safeguards; market-specific prices remain dynamic.
