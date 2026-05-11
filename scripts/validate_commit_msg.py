#!/usr/bin/env python3
"""
NoviSentinel — Commit Message Validator

Enforces the project's Conventional Commits convention:

    <type>(<scope>): <summary>

Rules:
  - Type must be from the official list
  - Scope is optional but must be lowercase alphanumeric + hyphens
  - Summary must be lowercase, imperative mood, under 100 chars
  - Forbidden words are rejected (wip, temp, misc, fixes, etc.)
  - Breaking changes use '!' after scope: feat(api)!: ...

Usage:
  python scripts/validate_commit_msg.py <commit-msg-file>
  (called automatically by pre-commit on commit-msg stage)
"""

import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# ── Official types ───────────────────────────────────────────────────────
VALID_TYPES = {
    "feat",
    "fix",
    "perf",
    "refactor",
    "security",
    "ai",
    "infra",
    "docs",
    "test",
    "build",
    "ci",
    "chore",
}

# ── Forbidden words in commit subjects ───────────────────────────────────
FORBIDDEN_WORDS = {
    "fixes",
    "updates",
    "temp",
    "misc",
    "working",
    "final",
    "wip",
    "stuff",
    "things",
    "changes",
}

# ── Commit message pattern ───────────────────────────────────────────────
# Matches: type(scope)!: summary  OR  type!: summary  OR  type: summary
COMMIT_PATTERN = re.compile(
    r"^(?P<type>[a-z]+)"  # type (lowercase)
    r"(?:\((?P<scope>[a-z0-9-]+)\))?"  # optional (scope)
    r"(?P<breaking>!)?"  # optional ! for breaking change
    r":\s"  # colon + space
    r"(?P<summary>.+)$"  # summary
)

MAX_SUBJECT_LENGTH = 100


def validate_commit_message(message: str) -> list[str]:
    """Validate a commit message. Returns list of errors (empty = valid)."""
    errors = []

    # Strip comments (lines starting with #) and get first non-empty line
    lines = [line for line in message.strip().splitlines() if not line.startswith("#")]

    if not lines:
        return ["Commit message is empty."]

    subject = lines[0].strip()

    # ── Allow merge commits ──────────────────────────────────────────────
    if subject.startswith("Merge "):
        return []

    # ── Check format ─────────────────────────────────────────────────────
    match = COMMIT_PATTERN.match(subject)
    if not match:
        errors.append(
            f'Invalid format: "{subject}"\n'
            f"  Expected: <type>(<scope>): <summary>\n"
            f"  Example:  feat(scanner): add YARA rule support"
        )
        return errors

    commit_type = match.group("type")
    summary = match.group("summary")

    # ── Validate type ────────────────────────────────────────────────────
    if commit_type not in VALID_TYPES:
        errors.append(f'Invalid type: "{commit_type}"\n  Valid types: {", ".join(sorted(VALID_TYPES))}')

    # ── Validate subject length ──────────────────────────────────────────
    if len(subject) > MAX_SUBJECT_LENGTH:
        errors.append(f'Subject is {len(subject)} chars (max {MAX_SUBJECT_LENGTH}):\n  "{subject}"')

    # ── Summary must start lowercase ─────────────────────────────────────
    if summary and summary[0].isupper():
        errors.append(
            f'Summary must start with a lowercase letter:\n  ❌ "{summary}"\n  ✅ "{summary[0].lower() + summary[1:]}"'
        )

    # ── Summary must not end with a period ───────────────────────────────
    if summary and summary.endswith("."):
        errors.append("Summary must not end with a period.")

    # ── Check for forbidden words ────────────────────────────────────────
    summary_words = set(summary.lower().split())
    found_forbidden = summary_words & FORBIDDEN_WORDS
    if found_forbidden:
        errors.append(
            f"Forbidden words in summary: {', '.join(sorted(found_forbidden))}\n"
            f"  These are too vague. Be specific about what changed."
        )

    # ── Check body formatting (if present) ───────────────────────────────
    if len(lines) > 1 and lines[1].strip():
        errors.append("Second line must be blank (separate subject from body).")

    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: validate_commit_msg.py <commit-msg-file>")
        return 1

    commit_msg_file = sys.argv[1]

    try:
        with open(commit_msg_file, encoding="utf-8") as f:
            message = f.read()
    except FileNotFoundError:
        print(f"File not found: {commit_msg_file}")
        return 1

    errors = validate_commit_message(message)

    if errors:
        print("\n╔══════════════════════════════════════════════════════════╗")
        print("║          COMMIT MESSAGE VALIDATION FAILED              ║")
        print("╚══════════════════════════════════════════════════════════╝\n")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}\n")
        print("Format: <type>(<scope>): <summary>")
        print(f"Types:  {', '.join(sorted(VALID_TYPES))}")
        print("\nSee CONTRIBUTING.md for full commit convention.\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
