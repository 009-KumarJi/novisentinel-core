"""CLI to purge disk-persisted anonymization-map sessions.

Usage:
  python scripts/purge_sessions.py          # delete only expired sessions
  python scripts/purge_sessions.py --all    # delete all sessions regardless of TTL
"""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Purge NoviSentinel session files from disk.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Remove all sessions (not just expired ones).",
    )
    args = parser.parse_args()

    from app.core.session_store import get_session_store

    store = get_session_store()
    if args.all:
        n = store.purge_all()
        print(f"Purged {n} session file(s) (all).")
    else:
        n = store.purge_expired()
        print(f"Purged {n} expired session file(s).")


if __name__ == "__main__":
    sys.exit(main())
