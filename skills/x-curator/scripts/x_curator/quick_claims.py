"""Bind retained assertions to their checked status, wording and citations."""

def citations(sources):
    return [{key: value for key, value in source.items() if key in ('capture', 'quote', 'observation')}
            for source in sources]


def retained(claim, checked):
    refs = claim['checks']
    if not refs or not set(refs) <= checked.keys() or claim['independently_useful'] is not True:
        raise ValueError('retained material needs useful checked support')
    allowed = {'supported'} if claim['kind'] == 'fact' else {'supported', 'subjective'}
    if {checked[key]['status'] for key in refs} - allowed:
        raise ValueError('unsupported factual details cannot hide inside an attributed claim')


    factual_binding(claim, checked)


def factual_binding(claim, checked):
    if claim['kind'] != 'fact':
        return
    check, = (checked[key] for key in claim['checks'])
    if check['text'] != claim['text']:
        raise ValueError('retained fact must be the exact checked assertion')
    required = {(s['capture'], s['quote']) for s in check['sources']}
    cited = {(s['capture'], s['quote']) for s in claim['citations']}
    if not required <= cited:
        raise ValueError('retained fact must cite its checked support')
