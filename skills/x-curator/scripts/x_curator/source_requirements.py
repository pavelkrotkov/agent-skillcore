"""Visible source links and media remain obligations even when the worker omits them."""


def requirements(entry):
    result = entry["content"]["itemContent"]["tweet_results"]["result"]
    tweet = result.get("tweet", result)
    return tweet_requirements(tweet)


def links(entry):
    result = entry["content"]["itemContent"]["tweet_results"]["result"]
    tweet = result.get("tweet", result)
    return tweet_links(tweet)


def tweet_links(tweet):
    legacy = tweet.get("legacy", {})
    note = tweet.get("note_tweet", {}).get("note_tweet_results", {}).get("result", {})
    entities = legacy.get("entities", {}).get("urls", []) + note.get("entity_set", {}).get("urls", [])
    return sorted({item["expanded_url"] for item in entities})


def tweet_requirements(tweet):
    legacy = tweet.get("legacy", {})
    urls = tweet_links(tweet)
    media = legacy.get("extended_entities", {}).get("media", [])
    urls.extend(media_url(item) for item in media)
    urls.extend(context_urls(tweet, legacy))
    return sorted(set(urls))


def context_urls(tweet, legacy):
    quoted = tweet.get("quoted_status_result", {}).get("result", {})
    quoted = quoted.get("tweet", quoted)
    ids = [legacy.get("in_reply_to_status_id_str"), legacy.get("quoted_status_id_str"), quoted.get("rest_id")]
    return ["https://x.com/i/status/" + identity for identity in ids if identity]


def media_url(item):
    if item["type"] == "photo":
        return item["media_url_https"]
    variants = [v for v in item.get("video_info", {}).get("variants", []) if v.get("content_type") == "video/mp4"]
    if not variants:
        raise ValueError("source media has no retrievable variant")
    return max(variants, key=lambda v: v.get("bitrate", 0))["url"]
