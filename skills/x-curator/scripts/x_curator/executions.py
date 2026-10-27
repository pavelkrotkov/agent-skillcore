"""Only the controller records roles and sessions from actual executor event streams."""
import json
import time
import uuid

from .evidence import bundle
from .model_events import result
from .model_trace import verify_request
from .leases import require_lease
from .receipts import digest, encoded
from .storage import sha256
from .worker_errors import WorkerFailure
from .deadlines import DeadlineExceeded
from .verification_details import require_receipt


def execute(db, token, role, model, runner, proposal=None, feedback=None):
    if role not in ("research", "review", "discover"):
        raise ValueError("unsupported execution role")
    evidence = bundle(db, token)
    request = {"role": role, "bundle": evidence, "bundle_sha": digest(evidence),
               "proposal": proposal, "review_feedback": feedback}
    return recorded(db, token, role, model, runner, request)


def recorded(db, token, slot, model, runner, request):
    identity = uuid.uuid4().hex
    with db:
        db.execute("BEGIN IMMEDIATE")
        require_lease(db, token, time.time())
        db.execute("INSERT INTO executions(id,token,role,model,input,input_sha,started) VALUES (?,?,?,?,?,?,?)",
                   (identity, token, slot, model, encoded(request).decode(), digest(request), time.time()))
    try:
        log = runner(request)
    except (WorkerFailure, DeadlineExceeded) as exc:
        record_log(db, identity, getattr(exc, 'log', b''))
        raise
    record_log(db, identity, log)
    session, output = result(log)
    with db:
        db.execute("UPDATE executions SET finished=?,session=?,output=?,output_sha=?,log=?,log_sha=? WHERE id=?",
                   (time.time(), session, encoded(output).decode(), digest(output), log, sha256(log), identity))
    return identity


def record_log(db, identity, log):
    with db:
        db.execute("UPDATE executions SET log=?,log_sha=? WHERE id=?", (log, sha256(log), identity))
    from .native_search import record
    record(db, identity, log)


def verified_execution(db, identity, role, token, semantic_role=None):
    row = db.execute("SELECT * FROM executions WHERE id=? AND role=? AND token=? AND finished IS NOT NULL",
                     (identity, role, token)).fetchone()
    if row is None:
        raise ValueError("missing controller execution receipt")
    request, output = json.loads(row["input"]), json.loads(row["output"])
    verify_request(row["log"], request)
    session, actual = result(row["log"])
    require_receipt((digest(request), digest(output), sha256(row["log"]), session, actual, request['role']),
                    (row["input_sha"], row["output_sha"], row["log_sha"], row["session"], output, semantic_role or role))
    return dict(row), request, output
