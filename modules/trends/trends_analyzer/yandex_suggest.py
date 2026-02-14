"""
Yandex Suggest — related search queries.

Uses the public Suggest API (no auth required).
Practically unlimited, but we cache results for 12 hours.
"""

import requests

from .cache import can_request, record_request, get_cached, set_cached


def suggest_keywords(keyword: str) -> list:
    """Fetch related search suggestions from Yandex."""
    cache_key = f"suggest_{keyword}"

    cached = get_cached('yandex', cache_key)
    if cached:
        print("  [cache] Yandex Suggest")
        return cached

    can, reason = can_request('yandex')
    if not can:
        print(f"  [wait] {reason}")
        return []

    try:
        url = 'https://suggest.yandex.ru/suggest-ff.cgi'
        params = {
            'part': keyword,
            'uil': 'ru',
            'n': 10,
            'sn': 5,
            'v': 4,
        }

        response = requests.get(url, params=params, timeout=10)
        record_request('yandex')

        data = response.json()
        suggestions = data[1] if len(data) > 1 else []

        set_cached('yandex', cache_key, suggestions)
        print("  [ok] Yandex Suggest")

        return suggestions

    except Exception as e:
        print(f"  [error] {e}")
        return []
