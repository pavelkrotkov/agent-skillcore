"""Reuse TweetHoarder's authentication and URL construction, never its archive."""
import json
from urllib.parse import unquote, urlencode


class XClient:
    def __init__(self):
        import httpx
        from tweethoarder.auth.cookies import resolve_cookies
        from tweethoarder.client.base import TwitterClient
        from tweethoarder.config import get_config_dir
        from tweethoarder.query_ids.store import QueryIdStore

        cookies = resolve_cookies()
        self.account = unquote(cookies.get("twid", "")).removeprefix("u=")
        if not self.account.isdecimal():
            raise ValueError("existing X session lacks a valid account identity")
        self.client = httpx.Client(headers=TwitterClient(cookies).get_base_headers(), timeout=30)
        self.queries = QueryIdStore(get_config_dir() / "query-ids-cache.json")

    def fetch(self, kind, cursor):
        from tweethoarder.client.timelines import build_bookmarks_url, build_likes_url
        from tweethoarder.query_ids.store import get_query_id_with_fallback

        if kind == "likes":
            query = get_query_id_with_fallback(self.queries, "Likes")
            url = build_likes_url(query, self.account, cursor)
        else:
            query = get_query_id_with_fallback(self.queries, "Bookmarks")
            url = build_bookmarks_url(query, cursor)
        response = self.client.get(url)
        return response.status_code, response.content

    def close(self):
        self.client.close()

    def detail(self, source_id):
        from tweethoarder.client.timelines import build_tweet_detail_url
        from tweethoarder.query_ids.store import get_query_id_with_fallback
        query = get_query_id_with_fallback(self.queries, "TweetDetail")
        fields = {"withArticleRichContentState": True, "withArticlePlainText": True}
        url = build_tweet_detail_url(query, source_id) + "&" + urlencode({"fieldToggles": json.dumps(fields)})
        response = self.client.get(url)
        return response.status_code, response.content
