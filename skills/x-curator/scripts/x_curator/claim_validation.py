"""Check attribution and exact excerpt support for every claim."""
from difflib import get_close_matches


def captured(captures, identity):
    try:
        return captures[identity]
    except KeyError:
        choices = get_close_matches(str(identity), captures, n=3, cutoff=0)
        raise ValueError(f'Unknown capture {identity!r}; available exact IDs: {choices}. Copy an observed ID; never guess.') from None


def nonempty(value, field='text'):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"nonempty {field} required")
    return value



def validate_claim(claim, captures):
    for key in ("id", "text", "attribution"):
        nonempty(claim[key])
    if claim["kind"] not in ("fact", "opinion", "prediction", "anecdote", "recommendation", "humor"):
        raise ValueError("unknown epistemic assessment")
    if not isinstance(claim["limitations"], list) or not claim["citations"]:
        raise ValueError("claim citations and limitations required")
    for cite in claim["citations"]:
        validate_citation(cite, captured(captures, cite["capture"]))


def validate_citation(cite, capture):
    if capture['kind'] == 'pdf':
        from .pdf_citations import validate
        validate(cite, capture)
        return
    if {'pdf_pages', 'pdf_offsets', 'pdf_image'} & cite.keys():
        raise ValueError('PDF citation metadata requires acquired PDF evidence')
    # Visual claims need actual pixels and an observation, not a fabricated textual quote.
    if not cite.get("quote") and capture["kind"] in ("image", "video"):
        nonempty(cite.get("observation"), 'observation')
        if not capture.get("images"):
            raise ValueError("visual claim has no acquired model input")
        return
    quote = nonempty(cite["quote"])
    if ' '.join(quote.split()) not in ' '.join(capture['text'].split()):
        raise ValueError("excerpt is absent from authentic evidence")



def validate_claims(claims, captures):
    identities = {c["id"] for c in claims}
    if not claims or len(identities) != len(claims):
        raise ValueError("distinct supported claims required")
    for claim in claims:
        validate_claim(claim, captures)
    return identities
