"""Short model references expand to the exact immutable canonical publications."""


def prefix(identities):
    value = '@'
    while any(key.startswith(value) for key in identities):
        value += '@'
    return value


def aliases(inputs):
    if inputs.get('publication_references') != 'short/v1':
        return {}
    identities = sorted(set(inputs['sources']) | {item['reference']['publication']
                        for page in inputs['catalog'] for item in page['evidence']})
    start = prefix(identities)
    return {key: start + str(index) for index, key in enumerate(identities, 1)}


def replace(value, mapping):
    if isinstance(value, dict):
        return {key: mapping.get(item, item) if key == 'publication' and isinstance(item, str)
                else replace(item, mapping) for key, item in value.items()}
    if isinstance(value, list):
        return [replace(item, mapping) for item in value]
    return value


def canonical(packet, inputs):
    names = aliases(inputs)
    return replace(packet, {short: key for key, short in names.items()}) if names else packet
