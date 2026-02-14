"""
Google Trends — trending and related queries.

Uses pytrends (unofficial). Google blocks at ~50 requests/day.
Results are cached for 24 hours.
"""

from .cache import can_request, record_request, get_cached, set_cached


def get_related_queries(keyword: str, geo: str = 'RU') -> dict | None:
    """Fetch related queries (top + rising) for a keyword."""
    cache_key = f"related_{keyword}_{geo}"

    cached = get_cached('google_trends', cache_key)
    if cached:
        print("  [cache] Google Trends")
        return cached

    can, reason = can_request('google_trends')
    if not can:
        print(f"  [wait] {reason}")
        return None

    try:
        from pytrends.request import TrendReq

        pytrends = TrendReq(hl='ru-RU', tz=180, timeout=(10, 25))
        pytrends.build_payload([keyword], cat=0, timeframe='today 3-m', geo=geo)

        related = pytrends.related_queries()
        record_request('google_trends')

        result = {}
        if keyword in related:
            data = related[keyword]
            if data['top'] is not None:
                result['top'] = data['top'].to_dict('records')
            if data['rising'] is not None:
                result['rising'] = data['rising'].to_dict('records')

        set_cached('google_trends', cache_key, result)
        print("  [ok] Google Trends (cached 24h)")
        return result

    except Exception as e:
        if '429' in str(e):
            print("  [blocked] Google rate limit. Try again in 1 hour.")
        else:
            print(f"  [error] {e}")
        return None


def get_trending_now(geo: str = 'russia') -> list | None:
    """Fetch today's trending searches."""
    cache_key = f"trending_{geo}"

    cached = get_cached('google_trends', cache_key)
    if cached:
        return cached

    can, reason = can_request('google_trends')
    if not can:
        print(f"  [wait] {reason}")
        return None

    try:
        from pytrends.request import TrendReq

        pytrends = TrendReq(hl='ru-RU', tz=180)
        df = pytrends.trending_searches(pn=geo)
        record_request('google_trends')

        result = df[0].tolist()
        set_cached('google_trends', cache_key, result)
        return result
    except Exception as e:
        print(f"  [error] {e}")
        return None
