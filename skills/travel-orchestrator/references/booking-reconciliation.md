# Booking reconciliation

Use this path only for an explicitly authorized request to check, record, or correct an existing booking. Confirmation evidence is not a search recommendation, and a travel organizer's parsed fields are not authoritative when the underlying receipt says otherwise.

## Procedure

1. Inspect only confirmation evidence the active harness can actually reach: supported mail/document connectors, provider detail, or the user's observed UI. Search inventory is optional context, never proof of an existing reservation. If confirmation cannot be found, report `confirmation_not_located`; do not conclude that no booking exists.
2. Create one booked-component record per reservation component and one line item per repeated dated activity. Record component type, `booked` status, supplier, booking channel, generic party scope, local dates/times and timezone when stated, currency, stated total, amount paid, balance due and due date, refundable deposit/authorization exposure, cancellation deadline, and `verified_at`. Keep absent fields unknown. If paid plus due is derived into a total, label it derived and verify same scope/currency; a refundable deposit is separate cash exposure.
3. Keep supplier and booking channel separate. Preserve platform identity as a namespaced key such as `vrbo:<id>` or `kayak:<id>`; matching numeric IDs across platforms prove nothing. Cross-platform lodging identity requires compatible name, locality, dates/unit evidence, and no material mismatch. Mark conflicts explicitly and never invent an address.
4. Preserve every receipt line item. Three lessons on consecutive days at 09:00 remain three activities. A title such as “4-hour lesson” does not establish an exact end time when breaks or the session schedule are unknown.
5. Retain an original message/thread URL exactly when a supported connector or observed UI supplies it. Never synthesize mailbox deep links or claim an untested link works. Keep the source-email link separate from provider/booking/manage links; state when mailbox access or login is required, and never expose credentials or auth tokens.
6. Apply confirmation only to the party/component it covers. Do not infer a later group's flights, lodging, car, or activities from an earlier group's receipt. A cheaper current quote stays research and cannot replace a confirmed reservation without a separately authorized booking change.
7. On an authorized artifact correction, update the current constraint revision and every current overview, comparison, total, recommendation, and provenance view that depends on the booking; preserve prior research under `ARCHIVED — superseded`. Verify the write by reloading the artifact and checking all requested fields. A partial note/name update or a silently ignored rename is not success.
8. Organizer edits are not reservation changes. Do not cancel, rebook, rename with the supplier, or otherwise alter the real reservation unless that separate action is explicitly authorized. If fixing the organizer would require irreversible deletion/recreation, stop and request new authority.
9. Logging and side effects remain opt-in. Do not create cloud sheets, Gmail labels, calendar entries, uploads, messages, or new organizer artifacts unless requested. Keep fixtures and CI synthetic and free of real guest names, confirmation codes, payment data, email links, or credentials.

## Current-state rule

Booked facts and recommendation facts may coexist only when their roles are explicit. Current planning must treat confirmed components as invariants until the user changes them; historical candidates may remain for provenance, but they cannot reappear as the current “best” alternative or as “not booked.”
