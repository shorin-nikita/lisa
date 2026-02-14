"""CLI entry point: python -m trends_analyzer <keyword>"""

import sys
from .analyzer import combo_analyze


def main():
    if len(sys.argv) < 2 or '--help' in sys.argv:
        print("""
Lisa Trends Analyzer — multi-source trend analysis

Usage:
  lisa trends <keyword>
  lisa trends <keyword> --skip-google

Examples:
  lisa trends "AI automation"
  lisa trends "claude code" --skip-google

Sources:
  - Yandex Suggest — related queries (free, no limits)
  - YouTube API — top videos, title patterns
  - Google Trends — rising topics (50/day limit)

Data is cached. Repeated queries don't consume API limits.
""")
        sys.exit(0)

    skip_google = '--skip-google' in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    keyword = ' '.join(args)

    combo_analyze(keyword, skip_google=skip_google)


if __name__ == '__main__':
    main()
