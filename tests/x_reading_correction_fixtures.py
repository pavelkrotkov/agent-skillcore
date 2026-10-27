from x_reading_fixtures import ReadingCase
from x_trace_fixtures import proof
from x_curator.model_events import result
from x_curator.receipts import digest


class CorrectionCase(ReadingCase):
    reject_again = False
    findings = ['Preserve the qualification in the claim.']

    def model(self, request):
        log = super().model(request)
        if request['reading']['stage'] != 'segment' or request['reading']['index'] != 0:
            return log
        if request['role'] == 'research':
            return self.author(request, log)
        return self.reviewer(request, log)

    def author(self, request, log):
        if not request['reading'].get('correction'):
            return log
        packet = result(log)[1]
        packet['claims'][0]['limitations'] = ['Synthetic qualification retained.']
        return proof(request, packet)

    def reviewer(self, request, log):
        if request['reading'].get('correction') and not self.reject_again:
            return log
        verdict = dict(verdict='reject', proposal_sha=digest(request['proposal']),
                       bundle_sha=request['bundle_sha'], findings=self.findings)
        return proof(request, verdict)
