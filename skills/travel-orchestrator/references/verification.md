# Verification and recovery

## Finalist verification

Use the weakest sufficient evidence for discovery, then inspect exact detail for any decision that depends on price, terms, or availability:

1. **Lead:** cached, estimated, or list-level result. Candidate generation only.
2. **Exact structured detail:** matching itinerary/unit/seller with price scope, terms, and source/booking link.
3. **Direct seller/provider detail:** re-query the exact dates, party, currency, fare/room/product, bags/occupancy, and material terms.
4. **Active-harness browser check:** use only for a material structured-data gap or to inspect the same exact seller/provider detail. Browser evidence is judged by query match and freshness, not automatically demoted because it came from a browser.

Use the observation record and availability states in [provenance.md](provenance.md). Say “currently bookable” only when current exact seller/provider evidence supports it.

## Runtime capability and browser recovery

Inspect the current harness's available skills/tools/controls before following Toolkit source or fallback examples. Do not assume a named MCP, `agent-browser`, Patchright, Docker image, or other browser control exists merely because upstream guidance mentions it.

For browser recovery:

- reuse the user-designated working browser/tab/profile through the active harness's supported controls; if none was designated, prefer an already-supported current session rather than introducing alternate tooling;
- retry a transient navigation/tool failure at most once with the same criteria;
- if login, CAPTCHA, bot-wall, or warning interstitial blocks inspection, record `blocked`, stop automated retries, and hand the same session back to the user when the harness supports it;
- do not swap profiles, bypass warnings, or install/run alternate browser tooling solely to evade the block;
- if an API/tool is inaccessible but the user's working browser reaches exact current seller detail, score that evidence by the same match/freshness rules as any other exact seller observation.

An absent tool is `tool_unavailable`, not “searched.” A present source that does not cover the requested carrier/product is `unsupported_coverage`.

## Availability discipline

Preserve the observed booking/search horizon and retrieval time. A calendar open through April 5 says nothing about April 12 inventory: mark an April 12 query `calendar_not_open`, not `unavailable_exact_dates` or `verified_discontinued`.

A valid fare search returning nothing is `no_result` unless the source explicitly establishes exact-date unavailability. Wikipedia is route discovery/sanity-check evidence only; its omission cannot prove that service is discontinued. Reserve `verified_discontinued` for current authoritative provider/schedule evidence.

## Discrepancies

Preserve competing observations. Check date/time, party, currency, tax inclusion, seller, fare family/room type, cancellation, cache age, inventory source, married segment, and per-unit versus full-party/stay scope. Re-query mismatches before comparing them. If a comparable difference changes the recommendation, obtain a third/direct check when practical and explain any unresolved cause.

## Quote boundary

Verification stops before booking, holds, payment, transfers, cancellations, account changes, or external messages. A search/booking link should reproduce the search criteria where possible; it is a handoff aid, not an inventory hold or proof that the quote remains available.
