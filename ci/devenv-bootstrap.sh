#!/bin/bash
set -euxo pipefail
# we don't have permissions to clone getsentry which is a good thing
# eventually we should move this bootstrap testing over to getsentry repo
# in the meantime, mock it so that pip install -e has something to chew on
mkdir -p "$HOME/repo/getsentry"
cat <<EOF > "$HOME/repo/getsentry/pyproject.toml"
[project]
name = "getsentry-mock"
version = "0.0.0"
EOF

: PATH: "$PATH"
cat ~/.bashrc || : just looking

# note: colima will be used and is necessary for a docker runtime on
#       macos GitHub runners
devenv bootstrap

cd "$HOME/repo/sentry"
direnv allow
