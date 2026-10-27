---
name: travel-orchestrator
description: Orchestrate serious flight, hotel, rental-car, award, and trip searches plus confirmed-booking reconciliation. Use Travel Hacking Toolkit first for research, trvl CLI JSON as a selective cross-check, browser automation only for gaps/final verification, and authorized confirmation evidence for existing bookings.
---

# Travel Orchestrator

Route travel research through structured sources in a deliberate order, keep a provenance trail for every decision-relevant result, and reconcile confirmed bookings without turning recommendations into reservations.

## Routing policy

Use this order:

1. **Primary — Travel Hacking Toolkit.** Start every nontrivial flight, hotel, rental-car, award, or trip search with the highest-level Toolkit orchestration skill available in the active runtime (`plan-trip`, `trip-planner`, `compare-flights`, `compare-hotels`, `award-calendar`, or `trip-calculator`). Let it fan out only to sources the runtime actually exposes. For rental cars, use only car-capable Toolkit sources the runtime actually exposes; do not infer a named portal integration from Toolkit marketing/examples. Load `flight-search-strategy` and `lessons-learned` before award or complex cash searches; load `points-valuations` for cash-versus-points decisions.
2. **Secondary — `trvl` CLI JSON.** Never invoke the `trvl` MCP server. Do not mirror the entire primary search. Run the installed `trvl` binary with `--format json` when primary coverage is thin or contradictory, dates/airports/trip length need a broader matrix, positioning/split-ticket/multimodal alternatives matter, apartment or local lodging needs independent coverage, the user asks for exhaustive search, or an expensive finalist merits an independent cross-check. Use its raw search results to challenge the strongest primary candidates.
3. **Tertiary — active-harness web/browser automation.** Use only web/browser/computer controls actually exposed by the current harness, and only when structured sources cannot answer a decision-relevant question or a finalist needs direct verification. Do not drive Google Flights or booking sites when structured coverage is adequate.

If the Travel Hacking Toolkit plugin or one of its sources is unavailable, record the failure and continue with the next tier; never imply that a skipped source was searched.

Before invoking any named source from Toolkit guidance, inspect the current runtime capabilities. A Toolkit template is desired coverage, not proof that a named MCP, CLI, browser, or skill exists in this harness. Record absent capabilities as `tool_unavailable` and intentionally skipped coverage as `not_searched`; never invent a call. The local rules in [airport-coverage.md](references/airport-coverage.md), [airfare-search.md](references/airfare-search.md), [lodging-search.md](references/lodging-search.md), [rental-cars.md](references/rental-cars.md), [trip-budget.md](references/trip-budget.md), [booking-reconciliation.md](references/booking-reconciliation.md), [provenance.md](references/provenance.md), [verification.md](references/verification.md), and [trip-state.md](references/trip-state.md) override upstream examples when they conflict. In particular, Toolkit `trip-planner`/`plan-trip` examples assume one origin, one departure/return pair, and one hotel occupancy window; treat those as templates only. Never flatten distinct traveler groups to fit them. Toolkit `lessons-learned`/`flight-search-strategy` examples that prefer a cheapest bookable fare class are discovery anchors only; for ranking, preserve fare family and benefits per leg and apply the local all-in airfare rules even when the user did not name a fare preference. Toolkit `compare-hotels` source lists, sample tables, and benefit-adjusted totals are also discovery guidance: honor requested lodging platforms first, compare the exact dated room/unit for the real party, and apply the local fee, board-basis, review, and safety rules before ranking. Toolkit rental-car examples and experimental car-capable portal skills are candidate generation only: they do not prove Costco Travel, Hotwire, Priceline, Expedia, or a direct supplier was searched, and their headline price does not establish matched payment, cancellation, coverage, or return logistics. Toolkit `trip-calculator`/`plan-trip` totals are component subtotals until [trip-budget.md](references/trip-budget.md) accounts for every applicable trip cost; outbound + return + lodging alone is never a complete trip total when other components apply.

## Prerequisites and recovery

Skillfleet does not install native travel tools during bootstrap. The primary tier requires the Travel Hacking Toolkit to be available in the active agent runtime. The secondary wrapper requires Bash, `jq`, and the `trvl` CLI on `PATH`; check them before starting a search:

```bash
missing=0
for tool in bash jq trvl; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Missing required command: $tool" >&2
    missing=1
  fi
done
if [ "$missing" -ne 0 ]; then
  echo "Record the unavailable tier and continue with the next source." >&2
  exit 1
fi
jq --version
trvl version
```

Install `jq` with the machine's approved package manager (for example, `brew install jq` on macOS or `apt-get install jq` on Debian/Ubuntu). Install `trvl` from its reviewed official setup or release instructions; do not run an unreviewed download script. Re-run the checks above after installation. If a prerequisite is unavailable, record the exact missing tool, skip that tier, and never imply that it was searched; use the next permitted source or explain that coverage is incomplete.

## Search workflow

1. Build or update one current trip constraint record using [trip-state.md](references/trip-state.md): destination, generic traveler groups/counts, each group's origin and travel dates, lodging occupancy, shared-car responsibility, hard arrival deadlines/buffers, event dates, planning deadlines, cabin/bags, cancellation and ground-transport constraints, points mode/balances when relevant, scoped preferences, and booked-versus-planned status. When school/team/tournament dates matter, verify the current season from official team and linked event sources before searching; preserve user-confirmed constraints alongside any official discrepancy.
2. Build the bounded airport/date/carrier coverage matrix in [airport-coverage.md](references/airport-coverage.md) from that record. Search each distinct group's relevant departure/return combinations rather than coercing the whole party into one date pair; for flexible dates, cover the stated window (or a defensible reduced grid), adjacent trip lengths, and relevant origin/destination airports. Record searched, skipped-with-reason, and unavailable coverage separately. Never use “Tuesday is cheapest” or another fixed weekday rule as a substitute for searching.
3. Search structured sources through the Toolkit orchestration layer first. For every decisive observation, use the record in [provenance.md](references/provenance.md): source, queried-at time, exact query match (dates/party/currency/product), price scope, freshness/cache status, terms, source/booking link, availability state, and confidence.
4. Expand selectively with the bundled `trvl-search.sh` wrapper when `trvl`'s optimizer, date matrix, nearby-airport, split-ticket, rail/ferry, lodging, or rental-car coverage could change the decision. Label `trvl` as a secondary result, not a duplicate confirmation. The wrapper validates and compacts the JSON; do not place the full response in model context.
5. Normalize itinerary risk: distinguish protected connections from self-transfers; include airport changes, terminal changes, overnight gaps, separate-ticket baggage recheck, minimum connection time, visa/entry exposure, and missed-connection protection. Penalize unreasonable schedules.
6. Build and validate the candidate component ledger in [trip-budget.md](references/trip-budget.md), using the normalized flight, airport-logistics, lodging, rental and award records rather than re-pricing them. Every applicable component must be quoted, explicitly estimated, included elsewhere, or unresolved; missing never means zero. Keep payable expense separate from refundable cash exposure, optional charges, contingent credits, and hypothetical benefit value, and do not rank a materially unresolved candidate as the cheaper trip.
7. For lodging, follow [lodging-search.md](references/lodging-search.md): compare neighborhoods first, then equivalent dated/party/room needs across requested or preferred platforms before useful alternatives. Do not rank a lead-in property price. Verify the exact room/unit, bedrooms versus beds, bathrooms, complete expense versus refundable cash exposure, cancellation cutoff in property-local time, board basis, pool/beach/parking access, family-relevant reviews, safety holds, and actual availability.
8. For rental cars, follow [rental-cars.md](references/rental-cars.md): compare identical pickup/drop-off locations and local times, party/luggage needs, and vehicle requirements across requested channels and decision-relevant direct suppliers. Verify supplier versus booking channel, all-in mandatory expense, payment/cancellation, coverage/deposit/fuel/toll/additional-driver terms, and terminal/walkable versus shuttle/after-hours return logistics before ranking. Reconcile early return with the flight deadline and add decision-relevant rental, relocation, parking, shuttle, ride, or airport-hotel cost to the trip budget; keep refundable deposits separate from expense.
9. Cross-check finalists only where the result affects the recommendation. Compare inspected evidence, not source brand: preserve disagreements, diagnose timing/currency/product/party/seller/caching differences, and obtain a third/direct check when material. Exact current seller detail observed in the browser can outrank a cached aggregate and is not automatically a low-confidence price ceiling. Do not describe a fare as currently bookable without current exact provider/seller evidence.
10. Report the winning option and trade-offs. Include concrete flight and lodging finalists (or near-ties) with source/booking links and freshness, plus the [trip-budget.md](references/trip-budget.md) comparison: approximate payable expense for each feasible or budget-rejected candidate, separate cash exposure/options/credits/value, exclusions, uncertainty, completeness, and unresolved items. Include the coverage matrix/status, departure and return logistics, usable vacation time, risk/protection labels, provenance, freshness timestamp, and what remains unverified. Every current overview, table, total, ranking, recommendation, and provenance block must derive from the same current constraint revision. Archive superseded dates/prices unmistakably and keep them out of current ranking; preserve unrelated destination research and user-confirmed booked groups. Say “currently bookable” only when a current provider or room-level verification supports it.

## Post-booking reconciliation

Before updating a persisted trip or importing bookings, load the user's explicitly configured travel-record skill and private preferences when available. Preserve confirmed ownership, traveler identities, payer allocations and source evidence. Research recommendations remain separate from confirmed records; agent conventions are not automatic application settings.

When the user explicitly asks to check, record, or reconcile an existing booking, follow [booking-reconciliation.md](references/booking-reconciliation.md). This is not a candidate-search tier: inspect only authorized confirmation evidence from capabilities the current harness actually exposes, keep booked facts separate from search recommendations, and update the current trip revision from confirmed evidence. A cheaper current lead never replaces a confirmed reservation. Do not create labels, calendar entries, cloud sheets, uploads, or reservation changes unless separately authorized.

## Tool-specific guardrails

- The `trvl` MCP registration is intentionally disabled because trvl 1.21.4 emits `resource_link` blocks that the current Codex MCP bridge rejects. Do not add, enable, or call it. Use the CLI only.
- Treat IATA codes supplied in the query as authoritative unless an independent aviation source disproves them. Never replace an airport code with a semantic entity inferred from its letters; `SJU` means Luis Muñoz Marín International Airport.
- Treat `trvl` raw search results as evidence. Retain price, currency, provider, itinerary, dates/times, duration, stops, airlines, booking URL/source, baggage when present, and provider status.
- Do not trust `trvl` generated advice, route classification, destination/airport enrichment, optimal-booking-window claims, or hack-detector prose without independent validation. Known bad examples include mapping `SJU` to Saint Joseph's University and classifying EWR–SJU as European short-haul. Ignore advance-purchase advice when its geography is unsupported or wrong.
- `trvl` hotel discovery is not a final price. Use the appropriate CLI hotel discovery and room/detail commands, and do not combine the price from one seller with cancellation terms from another.
- Use `trvl` `--deep`/optimization expansion only when the expected decision value justifies extra calls; label hidden-city and split-ticket ideas as risky and never present them as ordinary protected itineraries.
- Keep browser-cookie reuse and tier-2 CDP fallback disabled by default: the wrapper sets `TRVL_NO_BROWSER_COOKIES=1`, `TRVL_NO_TIER2_CDP=1`, and `TRVL_NO_TELEMETRY=1` only when those variables are unset. An explicit user opt-in such as `TRVL_NO_BROWSER_COOKIES=0` is preserved for the child process.
- For browser recovery, reuse the user-designated working browser/tab/profile through the active harness controls. Retry a transient navigation/tool failure at most once with the same criteria. On login, CAPTCHA, or bot-wall blocks, stop automation, record the blocker, and hand control to the user; do not swap profiles, bypass warnings, or install/launch alternate browser tooling because an upstream template suggests `agent-browser`, Patchright, or Docker.
- Quote verification stops before booking, holds, payment, transfers, cancellations, account changes, or external messages. Search/booking links should reproduce the query criteria; they do not reserve or prove inventory.
- Do not book, hold, cancel, transfer points, or expose credentials unless explicitly authorized. Manual handoff links are fine.

## trvl CLI execution contract

Run the Toolkit/Borski primary search first. Invoke `trvl` only afterward and only when it could change the recommendation. Always request JSON and compact it before reading. Use the bundled wrapper by its absolute path (the directory containing this `SKILL.md`) so the compactor does not depend on the caller's working directory:

```bash
bash /path/to/travel-orchestrator/scripts/trvl-search.sh \
  flights EWR SJU 2026-12-20 --return 2026-12-30 --format json
```

The wrapper resolves `scripts/trvl-compact.jq` relative to itself, checks `mktemp`, the `trvl` exit status, and JSON validity, and removes its temporary raw file on exit. Check its exit status before using any result.

Choose the CLI command that matches the decision:

```bash
# Nearby airports
bash /path/to/travel-orchestrator/scripts/trvl-search.sh \
  flights EWR,JFK,LGA SJU,BQN 2026-12-20 \
  --return 2026-12-30 --format json

# Flexible dates at fixed trip length
bash /path/to/travel-orchestrator/scripts/trvl-search.sh \
  dates EWR SJU \
  --from 2026-12-18 --to 2026-12-23 \
  --duration 10 --round-trip --format json

# Explicit departure/return matrix
bash /path/to/travel-orchestrator/scripts/trvl-search.sh \
  grid EWR SJU \
  --depart-from 2026-12-18 --depart-to 2026-12-23 \
  --return-from 2026-12-28 --return-to 2027-01-03 \
  --format json

# Rental-car secondary check
bash /path/to/travel-orchestrator/scripts/trvl-search.sh \
  cars SJU 2027-04-10 2027-04-15 \
  --pickup-time 14:30 --dropoff-time 04:30 \
  --passengers 4 --vehicle-class compact --currency USD --format json

# Expensive finalist or meaningful alternative-routing opportunity
bash /path/to/travel-orchestrator/scripts/trvl-search.sh \
  flights EWR SJU 2026-12-20 \
  --return 2026-12-30 --deep --format json
```

Use network-enabled CLI execution when the sandbox blocks DNS. Keep the raw file out of the final artifact and model context.

## Reference navigation

Load only the references needed for the request:

- [airport-coverage.md](references/airport-coverage.md) for bounded airport/carrier coverage, direct carrier gap checks, local logistics, and usable vacation time.
- [airfare-search.md](references/airfare-search.md) for cash fares, date matrices, baggage, and connection risk.
- [lodging-search.md](references/lodging-search.md) for neighborhoods, hotels, apartments, fees, rooms, and cancellation.
- [rental-cars.md](references/rental-cars.md) for matched rental terms, source diagnostics, coverage, and early-return logistics.
- [trip-budget.md](references/trip-budget.md) for complete component ledgers, arithmetic checks, payable expense, cash exposure, and comparable ranking.
- [booking-reconciliation.md](references/booking-reconciliation.md) for confirmation evidence, source-email links, booked-component identity, and organizer updates.
- [points-awards.md](references/points-awards.md) for award search, transfer risk, points valuation, and direct verification.
- [local-discovery.md](references/local-discovery.md) for local-language and independent-property discovery.
- [itinerary-design.md](references/itinerary-design.md) for open jaws, multimodal routing, positioning, and trip bundles.
- [trip-state.md](references/trip-state.md) for split-party constraints, event verification, scoped preferences, and current-versus-archived trip state.
- [verification.md](references/verification.md) for freshness, direct-provider checks, discrepancies, and provenance fields.
- [anti-patterns.md](references/anti-patterns.md) for traps and failure modes.
- [provenance.md](references/provenance.md) for source hierarchy, confidence labels, and citation format.
- [evaluation-set.md](references/evaluation-set.md) for routing and output-discipline tests.

## Evaluation smoke test

> Find the best airfare and lodging for a family trip with dates flexible by ±2 days. Search nearby airports, compare mainstream hotels with apartment-style lodging, calculate total trip cost, use Travel Hacking Toolkit first, use trvl only as an independent secondary search where it can improve confidence or coverage, and use browser automation only for missing data or final verification.
