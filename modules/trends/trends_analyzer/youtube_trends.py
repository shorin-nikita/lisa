"""
YouTube Trends — competitor video analysis.

Uses YouTube Data API v3 (official).
Quota: 10,000 units/day. search.list = 100 units, videos.list = 1 unit.
Results cached for 6 hours.
"""

import os
import time

import requests

from .cache import can_request, record_request, get_cached, set_cached

BASE_URL = 'https://www.googleapis.com/youtube/v3'

_access_token = None


def _get_tokens() -> dict:
    """Load YouTube API tokens from environment."""
    return {
        'access_token': os.environ.get('YOUTUBE_ACCESS_TOKEN', ''),
        'refresh_token': os.environ.get('YOUTUBE_REFRESH_TOKEN', ''),
        'client_id': os.environ.get('YOUTUBE_CLIENT_ID', ''),
        'client_secret': os.environ.get('YOUTUBE_CLIENT_SECRET', ''),
    }


def _headers() -> dict:
    global _access_token
    tokens = _get_tokens()
    token = _access_token or tokens['access_token']
    return {'Authorization': f'Bearer {token}'}


def _refresh_token() -> bool:
    global _access_token
    tokens = _get_tokens()
    response = requests.post('https://oauth2.googleapis.com/token', data={
        'client_id': tokens['client_id'],
        'client_secret': tokens['client_secret'],
        'refresh_token': tokens['refresh_token'],
        'grant_type': 'refresh_token',
    })
    data = response.json()
    if 'access_token' in data:
        _access_token = data['access_token']
        return True
    return False


def search_videos(query: str, max_results: int = 15) -> dict | None:
    """Search YouTube videos (100 units per request)."""
    cache_key = f"search_{query}_{max_results}"

    cached = get_cached('youtube', cache_key)
    if cached:
        print("  [cache] YouTube search")
        return cached

    can, reason = can_request('youtube')
    if not can:
        print(f"  [wait] {reason}")
        return None

    response = requests.get(f'{BASE_URL}/search', headers=_headers(), params={
        'part': 'snippet',
        'q': query,
        'type': 'video',
        'order': 'viewCount',
        'maxResults': max_results,
        'regionCode': 'RU',
        'relevanceLanguage': 'ru',
    })

    if response.status_code == 401:
        _refresh_token()
        return search_videos(query, max_results)

    record_request('youtube')
    data = response.json()

    if 'items' in data:
        set_cached('youtube', cache_key, data)

    return data


def get_video_stats(video_ids: list) -> dict | None:
    """Get video statistics (1 unit per request)."""
    ids_str = ','.join(video_ids)
    cache_key = f"stats_{ids_str[:50]}"

    cached = get_cached('youtube', cache_key)
    if cached:
        return cached

    can, reason = can_request('youtube')
    if not can:
        return None

    response = requests.get(f'{BASE_URL}/videos', headers=_headers(), params={
        'part': 'statistics,snippet,contentDetails',
        'id': ids_str,
    })

    record_request('youtube')
    data = response.json()

    if 'items' in data:
        set_cached('youtube', cache_key, data)

    return data


def analyze_competitors(query: str, max_results: int = 10) -> dict | None:
    """Full competitor analysis for a topic."""
    full_cache_key = f"analysis_{query}_{max_results}"
    cached_analysis = get_cached('youtube', full_cache_key)
    if cached_analysis:
        print("  [cache] Full analysis")
        _print_analysis(cached_analysis)
        return cached_analysis

    print(f"  YouTube: {query}\n")

    search_result = search_videos(query, max_results)
    if not search_result or 'items' not in search_result:
        print(f"  [error] Search failed: {search_result}")
        return None

    video_ids = [item['id']['videoId'] for item in search_result['items']]

    time.sleep(2)

    stats = get_video_stats(video_ids)
    if not stats:
        return None

    videos = []
    for item in stats.get('items', []):
        snippet = item['snippet']
        statistics = item['statistics']
        videos.append({
            'id': item['id'],
            'title': snippet['title'],
            'channel': snippet['channelTitle'],
            'published': snippet['publishedAt'][:10],
            'views': int(statistics.get('viewCount', 0)),
            'likes': int(statistics.get('likeCount', 0)),
            'comments': int(statistics.get('commentCount', 0)),
            'url': f"https://youtube.com/watch?v={item['id']}",
        })

    videos.sort(key=lambda x: x['views'], reverse=True)

    print("  Top videos:\n")
    for i, v in enumerate(videos[:7], 1):
        print(f"  {i}. {v['title'][:60]}")
        print(f"     {v['views']:,} views | {v['likes']:,} likes | {v['channel']}")
        print()

    patterns = {
        'numbers': sum(1 for v in videos if any(c.isdigit() for c in v['title'])),
        'questions': sum(1 for v in videos if '?' in v['title']),
        'caps': sum(1 for v in videos if any(
            word.isupper() and len(word) > 2 for word in v['title'].split()
        )),
        'emoji': sum(1 for v in videos if any(ord(c) > 127 for c in v['title'])),
    }

    print("  Title patterns:")
    for pattern, count in patterns.items():
        print(f"    {pattern}: {count}/{len(videos)}")

    result = {'query': query, 'videos': videos, 'patterns': patterns}
    set_cached('youtube', full_cache_key, result)

    return result


def _print_analysis(data: dict):
    videos = data.get('videos', [])
    patterns = data.get('patterns', {})
    print("\n  Top videos:\n")
    for i, v in enumerate(videos[:7], 1):
        print(f"  {i}. {v['title'][:60]}")
        print(f"     {v['views']:,} views | {v['likes']:,} likes | {v['channel']}")
        print()
    print("  Title patterns:")
    for pattern, count in patterns.items():
        print(f"    {pattern}: {count}/{len(videos)}")
