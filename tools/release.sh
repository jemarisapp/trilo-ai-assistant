#!/usr/bin/env bash
set -euo pipefail

if [[ ${1-} == "" || ${2-} == "" ]]; then
  echo "Usage: $0 <version> \"message\"" >&2
  echo "Example: $0 1.5.0 'Trilo 1.5.0 – summary of changes'" >&2
  exit 1
fi

VERSION="$1"
MESSAGE="$2"

# Ensure we run from repo root regardless of where script is called
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

echo "Checking out main and pulling latest..."
git checkout main >/dev/null 2>&1
git pull --ff-only

TAG="v${VERSION}"

if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Tag $TAG already exists. Aborting." >&2
  exit 2
fi

echo "Creating annotated tag $TAG..."
git tag -a "$TAG" -m "$MESSAGE"

echo "Pushing tag $TAG to origin..."
git push origin "$TAG"

echo "Done. Latest tag is: $(git describe --tags --abbrev=0)"

