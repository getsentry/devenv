#!/bin/bash
exec </dev/null  # no interactive input
exec >&2  # helps keeps stdout/stderr outputs in order with each other
set -euxo pipefail

# we don't have permissions to clone getsentry which is a good thing
# eventually we should move this bootstrap testing over to getsentry repo
# in the meantime, mock it so that pip install -e has something to chew on
mkdir -p "$HOME/code/getsentry"
cat <<EOF > "$HOME/code/getsentry/pyproject.toml"
[project]
name = "getsentry-mock"
version = "0.0.0"
EOF

# devenv should ignore npm's prefix even if it's changed via config
cat <<EOF > "$HOME/.npmrc"
prefix = ${HOME}/.local/lib/nodejs
EOF

: PATH: "$PATH"

# doesn't functionally do anything, just exercises
devenv update

cd "$HOME"
# note: colima will be used and is necessary for a docker runtime on
#       macos GitHub runners
devenv bootstrap
devenv fetch sentry

cd "$HOME/code/sentry"

# check that sentry's post_fetch ran
grep -Fxq 'ignorerevsfile = .git-blame-ignore-revs' .git/config

expected="${HOME}/.local/share/sentry-devenv/bin/direnv"
got=$(command -v direnv)
if [[ "$got" != "$expected" ]]; then
    echo "unexpected direnv location ${got}, expected ${expected}"
    exit 1
fi

# XXX: direnv allow/reload weirdly just exits 0 in GHA after writing
# the allow file, and using delve (gdb for go binaries) with action-tmate
# is painful because you get logged out for no reason after a few minutes,
# strace also doesn't reveal anything obvious

# so instead, just do here the essentials that sentry's .envrc does
export PATH="${HOME}/code/sentry/.devenv/bin:${HOME}/code/sentry/node_modules/.bin:${HOME}/.local/share/sentry-devenv/bin:${PATH}"
export VIRTUAL_ENV="${HOME}/code/sentry/.venv"

# overwrite sentry's devenv config and resync
# so we don't break when upstream config is updated
cat <<EOF > "devenv/config.ini"
[venv.sentry]
python = 3.13.1
path = .venv
requirements = requirements-dev.txt
editable =
  .
# sourced by direnv
# bins =

[python3.13.1]
darwin_x86_64 = https://github.com/astral-sh/python-build-standalone/releases/download/20250106/cpython-3.13.1+20250106-x86_64-apple-darwin-install_only.tar.gz
darwin_x86_64_sha256 = 4c4dafe2d59bb58e8d3ad26af637b7ae9c8141bb79738966752976861bdb103d
darwin_arm64 = https://github.com/astral-sh/python-build-standalone/releases/download/20250106/cpython-3.13.1+20250106-aarch64-apple-darwin-install_only.tar.gz
darwin_arm64_sha256 = bbfc96038d0b6922fd783f6eb2c9bf9abb648531d23d236bc1a0c16bdd061944
linux_x86_64 = https://github.com/astral-sh/python-build-standalone/releases/download/20250106/cpython-3.13.1+20250106-x86_64-unknown-linux-gnu-install_only.tar.gz
linux_x86_64_sha256 = bb4696825039a2b5dc7fea2c6aeb085c89fd397016b44165ec73b4224ccc83e2
linux_arm64 = https://github.com/astral-sh/python-build-standalone/releases/download/20250106/cpython-3.13.1+20250106-aarch64-unknown-linux-gnu-install_only.tar.gz
linux_arm64_sha256 = d37aef7bdf5c27f7d006918f7cedb31f4ba07c88f61baac4ffbe0bee6d4b5248

[node]
darwin_x86_64 = https://storage.googleapis.com/sentry-dev-infra-assets/node/node-v20.13.1-darwin-x64.tar.xz
darwin_x86_64_sha256 = c83bffeb4eb793da6cb61a44c422b399048a73d7a9c5eb735d9c7f5b0e8659b6
darwin_arm64 = https://storage.googleapis.com/sentry-dev-infra-assets/node/node-v20.13.1-darwin-arm64.tar.xz
darwin_arm64_sha256 = e8a8e78b91485bc95d20f2aa86201485593685c828ee609245ce21c5680d07ce
linux_x86_64 = https://storage.googleapis.com/sentry-dev-infra-assets/node/node-v20.13.1-linux-x64.tar.xz
linux_x86_64_sha256 = efc0f295dd878e510ab12ea36bbadc3db03c687ab30c07e86c7cdba7eed879a9
# used for autoupdate
version = v20.13.1

[colima]
darwin_x86_64 = https://github.com/abiosoft/colima/releases/download/v0.7.5/colima-Darwin-x86_64
darwin_x86_64_sha256 = 53f78b4aaef5fb5dab65cae19fba4504047de1fdafa152fba90435d8a7569c2b
darwin_arm64 = https://github.com/abiosoft/colima/releases/download/v0.7.5/colima-Darwin-arm64
darwin_arm64_sha256 = 267696d6cb28eaf6daa3ea9622c626697b4baeb847b882d15b26c732e841913c
linux_x86_64 = https://github.com/abiosoft/colima/releases/download/v0.7.5/colima-Linux-x86_64
linux_x86_64_sha256 = a3d440033776b2fb0cdd6139a2dbebf6764aabf78a671d4aa13b45c26df21a8a
linux_arm64 = https://github.com/abiosoft/colima/releases/download/v0.7.5/colima-Linux-aarch64
linux_arm64_sha256 = 330e11a4b2e5ce69ee6253635308c9f0f49195f236da01718ede35cdb2729901
# used for autoupdate
version = v0.7.5

[lima]
# upstream github releases aren't built for macOS 14, so we use homebrew binaries
# from https://formulae.brew.sh/api/formula/lima.json
darwin_x86_64 = https://ghcr.io/v2/homebrew/core/lima/blobs/sha256:c2e69a572afa3a3cf895643ede988c87dc0622dae4aebc539d5564d820845841
darwin_x86_64_sha256 = c2e69a572afa3a3cf895643ede988c87dc0622dae4aebc539d5564d820845841
darwin_arm64 = https://ghcr.io/v2/homebrew/core/lima/blobs/sha256:be8e2b92961eca2f862f1a994dbef367e86d36705a705ebfa16d21c7f1366c35
darwin_arm64_sha256 = be8e2b92961eca2f862f1a994dbef367e86d36705a705ebfa16d21c7f1366c35
linux_x86_64 = https://ghcr.io/v2/homebrew/core/lima/blobs/sha256:741e9c7345e15f04b8feaf5034868f00fc3ff792226c485ab2e7679803411e0c
linux_x86_64_sha256 = 741e9c7345e15f04b8feaf5034868f00fc3ff792226c485ab2e7679803411e0c
# used for autoupdate
version = 0.23.2
EOF

devenv sync

expected="${HOME}/code/sentry/.devenv/bin/node"
got=$(command -v node)
if [[ "$got" != "$expected" ]]; then
    echo "unexpected node location ${got}, expected ${expected}"
    exit 1
fi

# devenv-bootstrap.sh overrides sentry devenv config.ini with this version
expected="v20.13.1"
# more rigorous check than node --version
got=$(node -e 'console.log(process.version);')
if [[ "$got" != "$expected" ]]; then
    echo "unexpected node version ${got}, expected ${expected}"
    exit 1
fi
