"""
Combined trend analyzer — merges data from all sources.

Usage:
    from trends_analyzer.analyzer import combo_analyze
    result = combo_analyze("AI automation")
"""

import json
from datetime import datetime

from .google_trends import get_related_queries
from .youtube_trends import analyze_competitors
from .yandex_suggest import suggest_keywords
from .cache import get_usage_stats


def combo_analyze(keyword: str, skip_google: bool = False) -> dict:
    """
    Full analysis across all sources.

    Args:
        keyword: Topic to analyze.
        skip_google: Skip Google Trends (useful when rate-limited).

    Returns:
        Dict with results from each source and generated content ideas.
    """
    print("=" * 60)
    print(f"  ANALYZE: {keyword}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    result = {
        'keyword': keyword,
        'timestamp': datetime.now().isoformat(),
        'sources': {},
    }

    # 1. Yandex Suggest (most reliable)
    print("\n  YANDEX SUGGEST")
    print("  " + "-" * 40)
    suggestions = suggest_keywords(keyword)
    result['sources']['yandex'] = {'suggestions': suggestions}

    if suggestions:
        print("\n  Related queries:")
        for s in suggestions[:10]:
            print(f"    - {s}")

    # 2. YouTube (official API)
    print("\n  YOUTUBE")
    print("  " + "-" * 40)
    youtube = analyze_competitors(keyword, max_results=10)
    if youtube:
        result['sources']['youtube'] = youtube

    # 3. Google Trends (if not skipped)
    if not skip_google:
        print("\n  GOOGLE TRENDS")
        print("  " + "-" * 40)
        gtrends = get_related_queries(keyword)
        if gtrends:
            result['sources']['google_trends'] = gtrends
            if gtrends.get('rising'):
                print("\n  Rising queries:")
                for item in gtrends['rising'][:7]:
                    print(f"    - {item['query']} (+{item['value']})")
    else:
        print("\n  GOOGLE TRENDS — skipped (--skip-google)")

    # Ideas
    print("\n" + "=" * 60)
    print("  CONTENT IDEAS")
    print("=" * 60)

    ideas = generate_ideas(result)
    result['ideas'] = ideas
    for i, idea in enumerate(ideas, 1):
        print(f"\n  {i}. {idea}")

    # API usage
    print("\n" + "-" * 60)
    print("  API usage today:")
    stats = get_usage_stats()
    for source, data in stats.items():
        status = "OK" if data['remaining'] > 10 else "LOW" if data['remaining'] > 0 else "EMPTY"
        print(f"    [{status}] {source}: {data['today']}/{data['limit']}")

    return result


def generate_ideas(data: dict) -> list:
    """Generate content ideas based on collected data."""
    ideas = []
    keyword = data['keyword']

    # From Yandex
    yandex = data['sources'].get('yandex', {})
    suggestions = yandex.get('suggestions', [])
    if suggestions:
        specific = [s for s in suggestions if len(s) > len(keyword) + 5]
        if specific:
            ideas.append(f"Specific topic: \"{specific[0]}\"")

    # From YouTube
    youtube = data['sources'].get('youtube', {})
    if youtube and youtube.get('videos'):
        top = youtube['videos'][0]
        ideas.append(f"Top format: {top['views']:,} views — {top['channel']}")

        patterns = youtube.get('patterns', {})
        tips = []
        if patterns.get('emoji', 0) > 5:
            tips.append("emoji in title")
        if patterns.get('numbers', 0) > 5:
            tips.append("numbers (top N, X ways)")
        if tips:
            ideas.append(f"Patterns: {', '.join(tips)}")

    # From Google Trends
    gtrends = data['sources'].get('google_trends', {})
    if gtrends and gtrends.get('rising'):
        rising = gtrends['rising'][0]
        ideas.append(f"Rising trend: \"{rising['query']}\" (+{rising['value']})")

    if not ideas:
        ideas.append(f"Create an overview on \"{keyword}\"")

    return ideas


def analyze_to_json(keyword: str, skip_google: bool = False) -> str:
    """Run analysis and return JSON string."""
    result = combo_analyze(keyword, skip_google=skip_google)
    return json.dumps(result, ensure_ascii=False, indent=2)
