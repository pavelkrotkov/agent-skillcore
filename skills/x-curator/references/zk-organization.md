# Concept-first knowledge organization

A like is a pointer into a Zettelkasten. Concept notes explain ideas across
sources, link to other notes with a reason, and keep supporting likes as children.
Entity notes retain distinct identities. Accepted opinions, recommendations and
predictions retain their attribution and limitations; synthesis is not consensus.

## Future intake

The ordinary mapping path uses `zettelkasten/v1`. The organizer reuses existing
concepts, creates genuinely new concepts, and can consolidate equivalent notes.
It receives complete evidence for included catalog notes, not just their titles.
For an explicitly focused refresh, optional catalog notes match whole words in approved claim text against note titles or aliases.
Exact named matches rank first; other candidates need all their topic words to match (half for broad entry points).
Numeric version identifiers in canonical titles must match even for broad entry points.
Embedded CJK names can match within unspaced text; Latin names keep whole-word boundaries.
Descriptions, limitations and schema metadata do not establish topic relevance. Required notes
and their retained connection targets remain complete regardless of lexical overlap.
Ordinary intake keeps broad bounded candidates so new claims can find concepts with different wording. The catalog remains bounded at 100,000 characters; explicitly required notes fail
closed if their complete context cannot fit. Partition a large editorial change
rather than truncate evidence or silently exceed the model envelope.

The organizer can use native search to understand placement and connections:
a three-query **target**, with actual usage retained in its execution receipt.
The entire organizer process, including tools, drafting and validation, has a
hard **120-second** limit. The whole organization attempt, including independent
review, has a hard **600-second** window. There is no automatic deep research,
provider fallback, fact-check retry, or new factual admission through this path.
Search discoveries can inform grouping; published prose and connections require
approved claim support. Unproven connections remain supported open questions.

New organization inputs opt into the existing `curator-validated-decision-v1` final schema.
The full proposal goes to `validate` once; a passing result supplies the exact small `final_answer`
to return immediately. That completed authenticated final hash selects the matching successful
curator validation from the same execution. The controller revalidates the expanded proposal
and sends it unchanged to independent review. Missing completion, mismatched hashes, failed or
foreign validation cannot publish. Historical unmarked full-proposal receipts retain their contract.
This removes duplicate output, without extending the120-second organizer or600-second combined window.

## Note contract and review

In addition to the existing `kind`, `title`, `description`, `claims`, and `related`:

- `synthesis`: nonempty list of `{text, claims:[{publication,claim}]}` paragraphs.
- `questions`: optional list with the same shape, phrased as gaps, not answers.
- `entry`: optional boolean for a broad concept entry point.
- `replaces`: optional list of existing `{kind,title}` notes to consolidate.

All prose support must belong to the page. New ZK proposals may reuse exact
references from the supplied catalog evidence. Revising a note or consolidating
another note requires its complete reviewed evidence and retains every claim.
The independent reviewer checks the exact proposal and input hashes, synthesis,
coherence, attribution, limitations, connections, and accidental duplicate notes.
Draft validation does not grant approval or more time. Retained legacy mapping
receipts remain readable under their original request shape.

New organization inputs record `link_support: target-evidence/v1`. Each proposed
connection must cite evidence also belonging to its exact proposed or catalog
target; include those references in the originating note's claims. The reviewer
still checks that the explanation is supported on both sides. General concepts
and narrower applications stay separate and connected. Repairing a citation must
not collapse their scopes. Historical inputs retain their original contract;
this marker does not reset organization-only or source attempt allowances.

Catalog projection 2 keeps selected-source claim prose once, in the source
packet. Catalog notes reference those exact claims; nonselected evidence stays
complete and inline. The model view omits controller-only identity lists and
corpus digests, while its input hash and execution receipt still bind the full
controller request. Collision, retirement and evidence checks remain mandatory.
Historical inline catalogs and unprojected receipts keep their original shape.

Projection replays accepted history. A consolidation changes the current view,
not historical captures, checks or receipts. Old note URLs remain navigable to
the consolidated note; incoming connections follow its canonical identity. Existing
reviewed connections survive new-source updates and consolidation, and their reasons
and support are included in catalog context for the next independent review. Model
output cannot supply controller-owned redirect paths. Source revisions that leave
the active corpus no longer support synthesized paragraphs in the current view.

The homepage shows at most twelve concept entry points. The complete note index
and source index stay reachable without duplicating the catalog on detail pages.
Notes show the idea and connections first, then open questions, supporting likes,
and the retained dated evidence ledger. Open questions never schedule research or
create approval: the user requests deeper analysis in the originating chat.

## Bounded migration of existing notes

Validate a small multi-source slice before any full-corpus migration:

```sh
python -m x_curator --state "$STATE" zk-refresh \
  --publication "$PUBLICATION_A" --publication "$PUBLICATION_B" \
  --page "$EXISTING_NOTE_KEY" --reason 'Approved concept organization slice'
```

Select one to ten distinct, already-organized, currently accepted publications.
Repeat `--page` for context that must be visible. Other current catalog evidence
can provide context; the source selection is not a fact-check selection.
This explicit command shares the wiki lock, preserves source attempt counters,
and journals organization-only attempts separately (three lifetime attempts per
exact immutable publication selection). Unrelated corpus/catalog changes, ordering,
reason text and review feedback cannot reset that allowance. There are no automatic
refresh retries; a deliberately different source selection is a separate manual slice.
It does not reset spent checks or ordinary mapping allowances. Failed proposals
or reviews cannot activate a generation. A successful mapping uses the existing
immutable rebuild, proof fence, link checks and checkpoint path.

Check conceptual coherence, explained peer links, all source memberships, old
note URLs and concept-to-like-to-original provenance. Then verify a later source
reuses the concept. A successful synthetic test proves mechanics, not editorial
quality of the private corpus. Do not claim the corpus migrated until an actual
reviewed slice and its completed wiki generation have been inspected.
