"""Render approved source knowledge without copying evidence excerpts into the wiki."""
from .receipts import digest
from .pdf_links import target, label


def render(packet, evidence):
    parts = ["# " + packet["title"]["text"], packet["summary"]["text"]]
    for claim in packet["claims"]:
        links = [target(evidence["captures"][c["capture"]]["url"], c) + label(c) for c in claim["citations"]]
        parts.extend(["## " + claim["id"], claim["text"], "Attribution: " + claim["attribution"],
                      "Assessment: " + claim["kind"], "Sources: " + ", ".join(links),
                      "Limitations: " + "; ".join(claim["limitations"])])
    parts.extend(["## Limitations", "; ".join(packet["limitations"]),
                  "Evidence bundle: " + digest(evidence)])
    return "\n\n".join(parts) + "\n"
