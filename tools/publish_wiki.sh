#!/usr/bin/env bash
# Copy docs/ into the GitHub wiki of this repo. Needs the wiki enabled (a public repo, or a paid plan for a
# private one) and one page created through the web page first, so the wiki repository exists.
#   tools/publish_wiki.sh https://github.com/OWNER/REPO.wiki.git
set -euo pipefail
WIKI="${1:?usage: publish_wiki.sh https://github.com/OWNER/REPO.wiki.git}"
SRC="$(cd "$(dirname "$0")/.." && pwd)/docs"
TMP="$(mktemp -d)"
git clone "$WIKI" "$TMP"
cp "$SRC"/*.md "$TMP"/
sed -i -E 's/\]\(([A-Za-z-]+)\.md\)/](\1)/g' "$TMP"/*.md       # wiki links have no .md
cd "$TMP"
git add -A
git commit -m "Update wiki from docs/" || { echo "Nothing to publish."; exit 0; }
git push
rm -rf "$TMP"
