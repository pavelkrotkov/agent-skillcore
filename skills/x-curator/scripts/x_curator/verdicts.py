"""Bind a separate review execution to this exact proposal and evidence revision."""
from .evidence import bundle
from .publication_currentness import validate as validate_revision
from .executions import verified_execution
from .packets import validate
from .receipts import digest
from .source_evidence import selected_source


def approved(db, token, proposal_id, review_id):
    return validate_approval(db, token, proposal_id, review_id, bundle(db, token))


def validate_approval(db, token, proposal_id, review_id, evidence):
    if (row := db.execute('SELECT role FROM executions WHERE id=?', (proposal_id,)).fetchone()) and row['role'] == 'factcheck':
        from .quick_proof import verify
        packet, evidence = verify(db, token, proposal_id, review_id, evidence)
    else:
        _, request, _ = verified_execution(db, proposal_id, 'research', token)
        if request.get('reading'):
            from .reading_audit import approved as segmented_approval
            packet, evidence = segmented_approval(db, token, proposal_id, review_id, evidence)
        else:
            packet, verdict = reviewed(db, token, proposal_id, review_id, evidence)
            if verdict != {"verdict": "approve", "proposal_sha": digest(packet), "bundle_sha": digest(evidence), "findings": []}:
                raise ValueError("independent review has not approved the exact proposal")
    validate_revision(db, token, evidence['captures'], selected_source(db, db.execute(
        'SELECT * FROM jobs WHERE account=? AND id=?', (evidence['account'], evidence['source'])).fetchone()), packet)
    return packet, evidence


def reviewed(db, token, proposal_id, review_id, evidence):
    author, request, packet = verified_execution(db, proposal_id, "research", token)
    reviewer, review_request, verdict = verified_execution(db, review_id, "review", token)
    if author["session"] == reviewer["session"]:
        raise ValueError("review must use a separate model session")
    if request["bundle"] != evidence or review_request["bundle"] != evidence:
        raise ValueError("evidence revision changed after model execution")
    if review_request["proposal"] != packet:
        raise ValueError("review input is not this proposal")
    validate(packet, evidence)
    return packet, verdict
