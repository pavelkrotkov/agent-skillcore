"""Retain bounded stage outcomes without retaining full corpus reports."""


def fields(value, names):
    return {key: item[:300] if isinstance(item, str) else item
            for key in names if key in value
            and isinstance(item := value[key], (str, int, float, bool, type(None)))}


def wiki(value):
    return fields(value, ('state', 'action', 'generation', 'sources', 'pages'))


def organization(value):
    result = fields(value, ('state', 'action', 'generation', 'proof_audited', 'sources_published',
                           'sources_indexed', 'sources_mapped', 'sources_unmapped', 'sources_awaiting_index',
                           'mapping_eligible', 'mapping_exhausted'))
    if 'mapping_failure_reasons' in value:
        result['mapping_failure_reasons'] = [fields(item, ('action', 'sources'))
                                              for item in value['mapping_failure_reasons'][:5]]
    return result


def report(value):
    result = {key: value[key] for key in ('selected_sources', 'counts') if key in value}
    result['generation'] = value.get('wiki', {}).get('manifest', {}).get('generation', value.get('generation'))
    if 'organization' in value:
        result['organization'] = organization(value['organization'])
    if 'notifications' in value:
        result['notifications'] = fields(value['notifications'], ('state', 'prepared', 'observed', 'unobserved',
            'recorded_failures', 'last_observed_prepared_at', 'pending_since_last_observed', 'failures_since_last_observed'))
    return result
