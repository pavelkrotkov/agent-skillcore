# Provenance and confidence

Confidence follows inspected evidence, not source brand.

## Evidence quality

1. **Current exact seller/provider detail:** matches the requested dates, party/occupancy, currency, and fare/room/product, with total price and material terms.
2. **Current exact structured detail:** same query match and scope, but one material checkout detail may remain unverified.
3. **Current aggregate/search result:** useful corroboration or discovery, but not exact seller detail.
4. **Cached, estimated, lead-in, or stale result:** candidate generation only.
5. **Documentation/community/discovery source:** policy, tactics, or route leads; never inventory proof.

Browser and API observations use the same scale. A source named Duffel, an airline, Toolkit, `trvl`, or a browser does not win by label alone.

## Evidence status

Track factual status separately from confidence: `estimated`, `observed`, `seller_verified`, or `booked`. `booked` requires reservation confirmation tied to the exact component and party scope; a cheaper current search result or an organizer parser cannot promote a lead to booked. A confirmation lookup that finds nothing is `confirmation_not_located`, not proof that no booking exists and not an inventory availability state.

## Decisive observation record

For every observation that can change ranking, cost, or availability, record:

- `source` and `queried_at`;
- `evidence_status`;
- `query_match`: dates, party/occupancy, currency, and product/fare/room/seller;
- `price_scope`: per traveler/night/stay/party and which taxes/mandatory fees are included;
- `freshness`: live/cached/estimated plus source timestamp when known;
- `terms`: baggage, cancellation/change, occupancy, payment or other material conditions;
- `source_link` and `booking_link` when available;
- `availability_state`;
- `confidence` and a short `confidence_reason`.

For schedule or booking calendars also record the observed date range, including `observed_through`, so a query beyond the open horizon is not mistaken for negative inventory.

## Availability states

- `not_searched`: no attempt was made.
- `tool_unavailable`: the required tool/capability is absent or failed before a valid query could run.
- `blocked`: login, CAPTCHA, bot wall, or access warning prevented inspection.
- `unsupported_coverage`: the source/tool does not cover the requested carrier, market, property, or product.
- `calendar_not_open`: the requested date is beyond the source's observed searchable/booking horizon.
- `no_result`: a valid search ran but returned nothing; this does not prove sold-out inventory or discontinued service.
- `unavailable_exact_dates`: a capable source searched the exact matching dates/product inside open coverage and explicitly reported no inventory.
- `available`: a matching offer or unit was observed.
- `verified_discontinued`: current authoritative provider/schedule evidence explicitly shows the service/product ended or ends before the requested dates.

Wikipedia absence, a search snippet, or a fare query alone can never establish `verified_discontinued`. If a calendar retrieved on April 1 is open only through April 5, an April 12 query is `calendar_not_open`; preserve April 5 and the retrieval time.

## Confidence and disagreement

- **High:** current exact seller/provider detail with complete query match, price scope, and material terms, or exact reservation confirmation for booked facts. Exact browser-observed seller detail may be high confidence.
- **Medium:** current exact evidence with one material field unresolved, or multiple compatible observations that still lack final seller/provider detail.
- **Low:** cached/aggregate/estimated/lead evidence, incomplete query match, or unresolved comparable disagreement.

Before choosing a winner, compare query match, seller, fare/room/product, price scope, taxes/fees, timestamp, and cache state. Currency/product/party mismatches are not competing quotes until normalized or re-queried. If materially comparable observations still disagree, keep both, seek a third/direct check when practical, and lower confidence if the cause remains unresolved.

Primary references: [Travel Hacking Toolkit](https://github.com/borski/travel-hacking-toolkit), [trvl setup guide](https://raw.githubusercontent.com/MikkoParkkola/trvl/main/AGENTS.md), [Google Flights help](https://support.google.com/travel/answer/7664728?hl=en), and [FTC fee rule](https://www.ftc.gov/news-events/news/press-releases/2025/05/ftc-rule-unfair-or-deceptive-fees-take-effect-may-12-2025).
