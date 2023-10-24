#!/bin/bash
set -euo pipefail
arch=${1:-$(./github-arch.sh)}

set -x
curl -sSL https://github.com/actions/python-versions/raw/main/versions-manifest.json |
  jq '
      .[]
    | .files |= map(select(.arch == "'"$arch"'"))
    | select((.files | length > 0) and .stable)
    | .version
  ' -r |
  # sort by version, best-first
  sort -rV |
  # show nonempty lines, or else fail
  grep ^. \
;
