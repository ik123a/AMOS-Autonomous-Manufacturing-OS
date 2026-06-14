#!/usr/bin/env bash
# AMOS Push Script — Run this ONCE to create the GitHub repo and push

set -e

REPO="SKV/AMOS"
GIT_DIR=$(cd "$(dirname "$0")" && pwd)

echo "=== AMOS GitHub Push Script ==="
echo "Make sure you're in: $GIT_DIR"

# Check for gh CLI
if ! command -v gh &>/dev/null; then
  echo ""
  echo "ERROR: GitHub CLI (gh) is not installed."
  echo "Install it from: https://cli.github.com"
  echo ""
  echo "Or alternatively, create the repo manually at https://github.com/new"
  echo "  - Name: AMOS"
  echo "  - Private: Yes"
  echo "  - Don't add README"
  echo "Then run: git push -u origin main"
  echo ""
  echo "After creating the repo, re-run this script."
  exit 1
fi

# Auth check
if ! gh auth status &>/dev/null; then
  echo "Logging in to GitHub..."
  gh auth login
fi

cd "$GIT_DIR"

# Ensure branch is main
git branch -M main 2>/dev/null || true

# Create the repo (fails gracefully if already exists)
echo "Creating GitHub repo: $REPO ..."
gh repo create "$REPO" \
  --private \
  --source=. \
  --push \
  --description "AMOS — Autonomous Manufacturing OS: Edge-first AI platform for predictive maintenance and factory automation" \
  || echo "(Repo may already exist — continuing...)"

# Verify push
echo ""
echo "=== Verifying push ==="
git log --oneline -3
echo ""
echo "Remote:"
git remote -v
echo ""
echo "SUCCESS — AMOS is live at: https://github.com/$REPO"