"""
Cache and rate limiting for API requests.

Stores cached responses as JSON files. Tracks daily usage per source.
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

# Default cache directory — can be overridden via LISA_CACHE_DIR env
_cache_dir = None

RATE_LIMITS = {
    'google_trends': {
        'min_interval_seconds': 60,
        'cache_hours': 24,
        'daily_limit': 50,
    },
    'youtube': {
        'min_interval_seconds': 2,
        'cache_hours': 6,
        'daily_limit': 100,
    },
    'yandex': {
        'min_interval_seconds': 1,
        'cache_hours': 12,
        'daily_limit': 200,
    },
}


def _get_cache_dir() -> Path:
    global _cache_dir
    if _cache_dir is None:
        import os
        base = os.environ.get('LISA_CACHE_DIR', '')
        if base:
            _cache_dir = Path(base) / 'trends'
        else:
            _cache_dir = Path(__file__).resolve().parent.parent / 'data' / 'cache'
    _cache_dir.mkdir(parents=True, exist_ok=True)
    return _cache_dir


def get_cache_path(source: str, key: str) -> Path:
    safe_key = key.replace(' ', '_').replace('/', '_')[:50]
    return _get_cache_dir() / f"{source}_{safe_key}.json"


def get_state_path(source: str) -> Path:
    return _get_cache_dir() / f"_state_{source}.json"


def load_state(source: str) -> dict:
    path = get_state_path(source)
    if path.exists():
        with open(path) as f:
            state = json.load(f)
            today = datetime.now().strftime('%Y-%m-%d')
            if state.get('date') != today:
                state = {'date': today, 'count': 0, 'last_request': 0}
            return state
    return {'date': datetime.now().strftime('%Y-%m-%d'), 'count': 0, 'last_request': 0}


def save_state(source: str, state: dict):
    with open(get_state_path(source), 'w') as f:
        json.dump(state, f)


def can_request(source: str) -> tuple:
    """Check if a request is allowed. Returns (allowed: bool, reason: str)."""
    limits = RATE_LIMITS.get(source, {})
    state = load_state(source)
    now = time.time()

    if state['count'] >= limits.get('daily_limit', 100):
        return False, f"Daily limit reached ({state['count']}/{limits['daily_limit']})"

    min_interval = limits.get('min_interval_seconds', 5)
    elapsed = now - state.get('last_request', 0)
    if elapsed < min_interval:
        wait = min_interval - elapsed
        return False, f"Wait {wait:.0f}s (rate limit)"

    return True, "OK"


def record_request(source: str):
    state = load_state(source)
    state['count'] += 1
    state['last_request'] = time.time()
    save_state(source, state)


def get_cached(source: str, key: str):
    path = get_cache_path(source, key)
    if not path.exists():
        return None
    with open(path) as f:
        data = json.load(f)
    cache_hours = RATE_LIMITS.get(source, {}).get('cache_hours', 24)
    cached_at = datetime.fromisoformat(data.get('_cached_at', '2000-01-01'))
    if datetime.now() - cached_at > timedelta(hours=cache_hours):
        return None
    return data.get('_data')


def set_cached(source: str, key: str, data):
    path = get_cache_path(source, key)
    with open(path, 'w') as f:
        json.dump({
            '_cached_at': datetime.now().isoformat(),
            '_key': key,
            '_data': data,
        }, f, ensure_ascii=False, indent=2)


def get_usage_stats() -> dict:
    stats = {}
    for source in RATE_LIMITS:
        state = load_state(source)
        limits = RATE_LIMITS[source]
        stats[source] = {
            'today': state['count'],
            'limit': limits['daily_limit'],
            'remaining': limits['daily_limit'] - state['count'],
            'cache_hours': limits['cache_hours'],
        }
    return stats
