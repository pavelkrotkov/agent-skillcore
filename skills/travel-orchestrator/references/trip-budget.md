# Complete trip budgets

A candidate may be ranked on trip cost only after every component applicable to the current constraint revision is accounted for. A Toolkit or source total that only combines flights and lodging is a component subtotal unless the ledger below proves the trip total complete.

## Component ledger

For each candidate, record the party/group/date scope and one row for every applicable category: flights/taxes/mandatory fees; lodging and local taxes/fees; bags; seats; origin-airport parking or overnight; arrival/departure transfers; rental car; fuel/tolls/destination parking; rail/ferries; food; and trip-specific activities such as ski lifts, lessons/rentals, park admission, tours, or event tickets.

Each row records quantity/unit scope, currency, amount, evidence status, source/booking link and `queried_at`/freshness, plus:
- resolution: `quoted`, `estimated`, `included`, `unresolved`, or `not_applicable`;
- financial class: `expense`, `refundable_cash_exposure`, `optional`, `contingent_credit`, or `benefit_value`;
- for `included`, the owning row/package so it cannot be counted twice.

A missing applicable row is an error, never zero. Prefer a labeled allowance when a defensible estimate exists. Every feasible or budget-rejected candidate gets a final approximate payable-expense number when all material components can be quoted or estimated, with exclusions and uncertainty stated. If a material component cannot even be estimated, show the known subtotal and unresolved list, mark the candidate `insufficient_data`/incomparable, and never call the subtotal a complete verified total.

## Arithmetic and scope checks

Before ranking:
1. Recompute line extensions and subtotal sums from quantity × unit price; validate traveler counts, shared versus per-traveler charges, directions, room count, nights, rental days, activity days, and date boundaries.
2. Normalize currencies explicitly with the FX rate/source/time used, or keep the candidates incomparable. Keep points/miles and their valuation assumptions visible rather than silently converting them into cash.
3. Reconcile packages and inclusions. If a package contains lodging, transfers, meals, lift tickets, or another component, mark those rows `included` and do not add them again.
4. Sum only `expense` rows into payable expense. Show refundable deposits/authorizations as cash tied up, optional charges separately, and contingent credits/benefit value separately. Never subtract an unused or conditional credit, lounge/upgrade value, or other hypothetical benefit as cash savings.
5. Derive applicability and quantities from the current trip revision and scoped preferences. A Christmas-only Saturday-to-Saturday/six-ski-day rule does not alter another school-break trip.

## Comparison and output

Apply hard fit constraints first, then compare complete expense, usable time and risk. A materially unresolved candidate cannot outrank a complete one merely because its known subtotal is lower. Preserve materially different itinerary, lodging or package ideas even when their evidence comes from the same source; deduplicate duplicate observations, not distinct options.

For each candidate, report the concrete flight and accommodation records (or a few near-ties), booking/source links, query scope and freshness, approximate payable expense, separate cash exposure/options/credits/value, completeness, exclusions/uncertainty, and any unresolved components. Budget rejection still requires the defensible approximate total that caused the rejection.
