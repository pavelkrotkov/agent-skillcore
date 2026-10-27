"""Selected media stays complete; optional thread photos fit the existing cap."""


def bounded_urls(recovered, source, limit=32):
    focal = {url for post in recovered if post.get('rest_id') == source for url in photo_urls(post)}
    if len(focal) > limit:
        raise ValueError('selected-post photos exceed the native attachment budget')
    context = {url for post in recovered for url in photo_urls(post)} - focal
    urls = sorted(focal) + sorted(context)
    return urls[:limit], max(0, len(urls) - limit)


def photo_urls(tweet):
    media = tweet.get('legacy', {}).get('extended_entities', {}).get('media', [])
    return {item['media_url_https'] for item in media if item['type'] == 'photo'}
