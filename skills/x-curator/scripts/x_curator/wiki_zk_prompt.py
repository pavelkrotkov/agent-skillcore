"""Editorial scope and research limits for concept-first organization."""
ZK = '''Build an interconnected Zettelkasten: likes point to ideas, not one note per post.
These ZK rules replace the earlier batch-only membership and description-retention rules.
Prefer an existing coherent concept; create a note only for a genuinely distinct idea. Preserve
entity identity. Use a small set of broad concept entry points (entry:true) with narrower concepts
connected by explained relationships. Avoid post titles, author-specific workflow clones and generic
"related" links. Explain supports, extends, contradicts, applies, or a concrete shared mechanism.
The organizer may use bounded live search (three-query TARGET, not an enforceable count cap) only
to understand the topic, grouping and connections. Its execution has a hard 120-second limit, including
search, drafting and validation. Stop searching early enough to validate and submit. Search is not
a new fact-check or deep research approval. Newly found factual claims cannot enter the wiki through
organization. Use only approved input claims as support; if a relationship needs new evidence,
record it as an open question instead. Actual search use is retained in the execution trace.
Each page must include synthesis:[{text,claims:[{publication,claim}]}]; optional questions use the same shape,
and optionally entry:boolean and replaces:[{kind,title}]. Both synthesis and question blocks require
nonempty supporting claim references. Write a concise explanation across sources, preserve attribution,
uncertainty, disagreements and limitations, and explain practical relevance without inventing consensus.
Questions identify gaps or possible connections, never assert unverified answers. They do not schedule
research; deeper analysis requires a later explicit user approval in the originating chat.
For ZK inputs, page.claims may also include exact references from the supplied catalog evidence.
When refreshing synthesis, include ALL existing target evidence in page.claims and rewrite the note
coherently, not as an appended list of post summaries. Complete catalog evidence is mandatory.
Existing related edges are retained by default and included in catalog context; propose additional
connections without silently replacing the reviewed graph. Review synthesis against retained links too.
Consolidate equivalent notes using replaces only when their complete evidence is visible; include
all their claims and synthesize the combined material. Preserve genuinely different scopes. Never
replace a proposed page, reuse a retired identity, or assign one old page to multiple replacements.
For a refresh request, reorganize only the selected sources and explicitly supplied catalog notes;
preserve all underlying fact-checks, publications, attempts and approval history.
The independent reviewer must reject source-list prose, unsupported synthesis, misleading connections,
unjustified consolidation, unsupported answers to open questions, and near-duplicate note proliferation.
The reviewer has no live search; review only the exact supplied evidence and proposal.
'''


LINKS = '''Plan scope before drafting: equivalent notes can consolidate; a general concept and
its narrower application are different scopes and should remain connected notes. A coding example
does not make general agent-loop guidance coding-specific. Retain distinct recommendations and
product outlooks; do not absorb them into a narrower title to avoid a rejected relationship.
For each connection, cite approved evidence supporting BOTH sides of the explanation in
related.claims. Include target-side references in the originating page.claims too; this cross-reference
supports the relationship, not equivalence of the notes. For example, connecting general feedback
loops with incremental coding needs both the general-loop and coding-workflow evidence. The draft
validator requires at least one reference present in the exact target's proposed claims or catalog
evidence; independent review must still assess all the prose, both sides and their shared mechanism.
Repair valid review findings locally: correct citations or narrow the link wording while keeping
distinct scopes. Do not merge distinct topics or discard a supportable connection to avoid repair.
If approved evidence cannot support a connection, omit it rather than invent support.
Feedback can be mistaken. Compare replacement identities using the documented normalization, which
does not remove punctuation: hyphenated and space-separated titles can be distinct keys. Do not
invent self-replacement based on visual similarity; still assess semantic equivalence independently.
Before submitting, validate the corrected proposal within the same execution deadline. A valid draft
does not establish editorial approval or grant another attempt. These rules grant no research approval.
'''


COMPACT = '''Catalog projection 2 avoids duplicating approved claim prose. A catalog evidence item
containing only reference:{publication,claim} resolves to that exact claim in sources[publication].packet.claims.
Read its full text, attribution, kind and limitations there. Other catalog evidence remains inline.
Controller-only identity lists and corpus digests are omitted from the model view; the supplied input_sha
still binds the full inputs. Draft validation enforces those hidden collision and retirement guards.
This is the same complete evidence, not permission to infer missing facts or omit claims.
'''


def instructions(inputs, final=False):
    text = ZK if inputs.get('organization') == 'zettelkasten/v1' else ''
    text += LINKS if inputs.get('link_support') == 'target-evidence/v1' else ''
    text += COMPACT if inputs.get('catalog_projection') == 2 else ''
    if final:
        from .wiki_final import INSTRUCTIONS
        text += INSTRUCTIONS
    return text


MAPPING = '''Proposed pages are incremental assignments of the current batch's approved claims, not a
replacement catalog. Page identity is its kind plus normalized title (Unicode NFKC, casefolded,
whitespace collapsed); descriptions do not create a new identity. An entry with the existing
catalog kind/title assigns new claims to that same page. The controller merges those memberships
with prior claims, retaining the existing page's description; do not copy prior claims into the batch.
Thus a same-key assignment is reuse, not a second entity merely because it appears in proposed pages.
A matching key does not establish semantic compatibility: independently check entity identity,
topic meaning, scope and claim placement against the catalog. Reject incompatible same-key merges,
distinct keys that duplicate an existing entity, misleading labels and unsupported relationships.
Preserve approved claim wording, attribution and limitations. These rules grant no approval.
'''

ORGANIZE = '''Organize every approved source claim into coherent concept or entity pages.
Prior rejected-mapping feedback, when supplied, is advisory context for these exact inputs.
Address valid findings without inventing new claims or treating earlier feedback as approval.
Do not rewrite, strengthen, omit or invent factual claims. Reuse existing catalog titles when their
meaning matches; distinct meanings must stay separate. The catalog includes descriptions and claims
so identical words do not force a merge. Titles and descriptions are topic labels, not new factual claims.
Return {input_sha,pages:[{kind:'concept' or 'entity',title,description,claims:[{publication,claim}],
related:[{kind,title,reason,claims:[{publication,claim}]}]}]}.
Every source claim must appear at least once. In each reference, publication MUST be the explicit
source.publication field (the enclosing sources object key). NEVER use packet.bundle_sha, source.sha,
or the X source ID as publication. Copy claim IDs exactly from that publication packet. Duplicate membership within a page is forbidden.
Related links are optional, require a meaningful evidence-supported explanation, and must target an
existing catalog page or another proposed page. Every related.claims reference MUST also appear in
the originating page.claims list; add its supporting claim to that page when appropriate.
Never link a page to itself, including a title variant that normalizes to the same page key.
Before final submission, call validate(proposal) and correct any errors within this execution.
Use only exact catalog or proposed targets. Omit optional related links when no valid target exists.
Validation feedback grants neither more time nor approval; the final proposal is checked again.
Do not invent contradiction, causation or consensus.
Use exact existing titles for reused pages. Claims retain their source revision and original attribution.
Return the supplied input_sha. Include only pages receiving claims from the current source batch.
Use at most 30 pages and at most 100,000 characters of compact JSON output.
Projection version 1 preserves every approved claim's prose, kind, attribution and limitations.
Citation excerpts are omitted from this organization view; original evidence and citations remain
in canonical source publications. Do not infer new facts from this view.
'''

VERIFY = '''Independently review the proposed organization against the supplied approved claims and catalog.
Check topic coherence, accidental meaning/identity merges, misleading titles/descriptions, every claim's
assignment and every related-link explanation. Evidence IDs alone do not prove a relationship.
Preserve uncertainty and conflicting viewpoints; never imply a reconciled conclusion without evidence.
Return exactly {verdict:'approve' or 'reject',input_sha,proposal_sha,findings:[specific problems]}.
Approval requires empty findings. Use the supplied hashes exactly. Do not rewrite the proposal.
'''
