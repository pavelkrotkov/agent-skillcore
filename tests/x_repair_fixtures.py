from x_quick_recovery_fixtures import RecoveryCase
import repair_history
import repair_manifest
import repair_eligibility
from x_curator.receipts import digest


class QualificationCase(RecoveryCase):
    def manifest(self):
        check = self.affected()
        job = repair_eligibility.job(self.db, dict(account=check['account'], source=check['source']))
        item = dict(category='irrelevant_search', account=check['account'], source=check['source'],
                    revision=check['revision'], original=check['id'], job_sha=digest(job),
                    attempts=job['attempts'], max_attempts=job['max_attempts'],
                    **repair_history.snapshot(self.db, dict(original=check['id'])))
        return dict(repair_release='synthetic-reviewed-release', items=[item], scope=dict(repair_manifest.SCOPE, count=1))
