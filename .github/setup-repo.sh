#!/usr/bin/env bash
# Run once after `gh auth login` to wire up branch protection and labels.
# Usage: bash .github/setup-repo.sh

set -euo pipefail

REPO="009-KumarJi/novisentinel-core"

echo "==> Configuring branch protection for: $REPO"

# ── main — strictest rules ────────────────────────────────────────────────────
echo "--> main: require PR + all CI checks + your review + linear history"
gh api "repos/$REPO/branches/main/protection" \
  -X PUT \
  -H "Accept: application/vnd.github+json" \
  --field required_status_checks='{
    "strict": true,
    "contexts": [
      "Test (Python)",
      "Test (Python SDK)",
      "Lint",
      "Frontend (TypeScript)"
    ]
  }' \
  --field enforce_admins=false \
  --field required_pull_request_reviews='{
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_last_push_approval": true,
    "require_code_owner_reviews": true
  }' \
  --field restrictions=null \
  --field required_linear_history=true \
  --field allow_force_pushes=false \
  --field allow_deletions=false \
  > /dev/null
echo "    done."

# ── develop — lighter: CI required, review required, force-push allowed ───────
echo "--> develop: require PR + CI checks + review; allow force-push for rebases"
gh api "repos/$REPO/branches/develop/protection" \
  -X PUT \
  -H "Accept: application/vnd.github+json" \
  --field required_status_checks='{
    "strict": true,
    "contexts": [
      "Test (Python)",
      "Test (Python SDK)",
      "Lint",
      "Frontend (TypeScript)"
    ]
  }' \
  --field enforce_admins=false \
  --field required_pull_request_reviews='{
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true
  }' \
  --field restrictions=null \
  --field required_linear_history=false \
  --field allow_force_pushes=true \
  --field allow_deletions=false \
  > /dev/null
echo "    done."

# ── Labels ───────────────────────────────────────────────────────────────────
echo "--> Creating / updating labels"

gh label create "feature"         --color "0075ca" --description "New feature"                              --repo "$REPO" --force
gh label create "bug"             --color "d73a4a" --description "Something isn't working"                  --repo "$REPO" --force
gh label create "enhancement"     --color "a2eeef" --description "Improvement to an existing feature"      --repo "$REPO" --force
gh label create "documentation"   --color "0075ca" --description "Documentation only"                      --repo "$REPO" --force
gh label create "security"        --color "e4e669" --description "Security vulnerability or hardening"     --repo "$REPO" --force
gh label create "performance"     --color "fbca04" --description "Performance improvement"                 --repo "$REPO" --force
gh label create "refactor"        --color "cfd3d7" --description "Code refactor, no behaviour change"      --repo "$REPO" --force
gh label create "good first issue" --color "7057ff" --description "Good for newcomers"                     --repo "$REPO" --force
gh label create "help wanted"     --color "008672" --description "Extra attention needed"                   --repo "$REPO" --force
gh label create "breaking-change" --color "b60205" --description "Breaking API or behaviour change"        --repo "$REPO" --force
gh label create "wip"             --color "ededed" --description "Work in progress — do not merge"         --repo "$REPO" --force
gh label create "needs-review"    --color "fbca04" --description "Waiting for code review"                 --repo "$REPO" --force

echo "    done."
echo ""
echo "All done. Branch protection and labels are configured."
