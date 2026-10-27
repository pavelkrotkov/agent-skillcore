"""Content changes invalidate research; engagement counters do not."""
VOLATILE = frozenset('''views favorite_count retweet_count reply_count quote_count bookmark_count
bookmarked favorited retweeted conversation_muted is_translatable followers_count fast_followers_count
friends_count listed_count media_count normal_followers_count statuses_count favourites_count
verified_followers_count profile_image_url_https pinned_tweet_ids_str'''.split())


def revision(entry):
    result = entry['content']['itemContent']['tweet_results']['result']
    tweet = result.get('tweet', result)
    visibility = {key: value for key, value in result.items() if key not in ('tweet', '__typename')} if 'tweet' in result else {}
    return scrub({'tweet': tweet, 'visibility': visibility})


def scrub(value):
    if isinstance(value, dict):
        return {key: scrub(item) for key, item in value.items() if key not in VOLATILE}
    if isinstance(value, list):
        return [scrub(item) for item in value]
    return value
