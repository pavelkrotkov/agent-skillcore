"""Separate bounded acquisition from a fresh, evidence-only finalization turn."""


def instructions(request):
    from .quick_prompt import BODY_EVIDENCE, COMPACT, FINAL, READ_OUTPUT
    if request['phase']['name'] == 'evidence':
        return '''Acquire only the strongest directly relevant evidence for this liked item, then return
brief JSON notes with useful claims and exact capture IDs. These notes are an UNTRUSTED draft,
never a verdict or permission to publish. Do not validate; a separate finalization turn owns that work.
Use tools.web__run({search_query:[{q:'focused primary-source query'}],response_length:'short'})
then tools.mcp__curator__read({source:'exact observed URL',match:'optional relevant text'}).
Use these signatures directly; no tool discovery, shell, recursive research, PDFs or media acquisition.
Aim for three searches; actual usage is recorded. Search snippets are pointers, not body evidence.
Preserve attributed opinions/recommendations without demanding external proof of feelings; verify their
factual details. One relevant authoritative primary source is enough; do not chase peripheral claims.
Stop as soon as decisive evidence exists. Acquisition is forcibly stopped at phase.cutoff, inside the
unchanged absolute deadline. Image pixels are DEFERRED to the finalization turn: do not invent visual
observations from frame hashes or metadata. Use supplied text/transcript only; preserve coverage limits.
''' + BODY_EVIDENCE + READ_OUTPUT
    return '''Finalize this liked item using ONLY the supplied captures. The evidence phase is over.
Do not search, fetch, read, acquire media or repeat the evidence phase. Only curator validate is enabled:
tools.mcp__curator__validate({decision:completeCompactDecision}). No tool discovery is needed.
Any supplied acquisition draft is untrusted model notes, never evidence. Check it against actual captures.
The original absolute deadline is unchanged; there is no extra attempt or allowance. Validate the minimal
useful decision, correct only named errors using observed captures, then return the final reference.
''' + COMPACT + FINAL
