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
export DEVENV_FETCH_BRANCH=master
devenv bootstrap
devenv fetch sentry

# overwrite sentry's devenv config so we don't break when upstream config is updated
cat <<EOF > "$HOME/code/sentry/devenv/config.ini"
[venv.sentry]
python = 3.12.3
path = .venv
requirements = requirements-dev.txt
editable =
  .

[python3.12.3]
darwin_x86_64 = https://github.com/indygreg/python-build-standalone/releases/download/20240415/cpython-3.12.3+20240415-x86_64-apple-darwin-install_only.tar.gz
darwin_x86_64_sha256 = c37a22fca8f57d4471e3708de6d13097668c5f160067f264bb2b18f524c890c8
darwin_arm64 = https://github.com/indygreg/python-build-standalone/releases/download/20240415/cpython-3.12.3+20240415-aarch64-apple-darwin-install_only.tar.gz
darwin_arm64_sha256 = ccc40e5af329ef2af81350db2a88bbd6c17b56676e82d62048c15d548401519e
linux_x86_64 = https://github.com/indygreg/python-build-standalone/releases/download/20240415/cpython-3.12.3+20240415-x86_64-unknown-linux-gnu-install_only.tar.gz
linux_x86_64_sha256 = a73ba777b5d55ca89edef709e6b8521e3f3d4289581f174c8699adfb608d09d6
linux_arm64 = https://github.com/indygreg/python-build-standalone/releases/download/20240415/cpython-3.12.3+20240415-aarch64-unknown-linux-gnu-install_only.tar.gz
linux_arm64_sha256 = ec8126de97945e629cca9aedc80a29c4ae2992c9d69f2655e27ae73906ba187d

[node]
darwin_x86_64 = https://storage.googleapis.com/sentry-dev-infra-assets/node/node-v20.13.1-darwin-x64.tar.xz
darwin_x86_64_sha256 = c83bffeb4eb793da6cb61a44c422b399048a73d7a9c5eb735d9c7f5b0e8659b6
darwin_arm64 = https://storage.googleapis.com/sentry-dev-infra-assets/node/node-v20.13.1-darwin-arm64.tar.xz
darwin_arm64_sha256 = e8a8e78b91485bc95d20f2aa86201485593685c828ee609245ce21c5680d07ce
linux_x86_64 = https://storage.googleapis.com/sentry-dev-infra-assets/node/node-v20.13.1-linux-x64.tar.xz
linux_x86_64_sha256 = efc0f295dd878e510ab12ea36bbadc3db03c687ab30c07e86c7cdba7eed879a9
# used for autoupdate
version = v20.13.1
yarn_version = 1.22.22

[colima]
darwin_x86_64 = https://github.com/abiosoft/colima/releases/download/v0.6.6/colima-Darwin-x86_64
darwin_x86_64_sha256 = 84e72678945aacba5805fe363f6c7c87dc73e05cbbfdfc09f9b57cedf110865d
darwin_arm64 = https://github.com/abiosoft/colima/releases/download/v0.6.6/colima-Darwin-arm64
darwin_arm64_sha256 = b2729edcf99470071240ab6986349346211e25944a5dc317bba8fa27ed0f25e5
linux_x86_64 = https://github.com/abiosoft/colima/releases/download/v0.6.6/colima-Linux-x86_64
linux_x86_64_sha256 = bf9e370c4bacbbebdfaa46de04d0e01fe2649a8e366f282cf35ae7dd84559a25
linux_arm64 = https://github.com/abiosoft/colima/releases/download/v0.6.6/colima-Linux-aarch64
linux_arm64_sha256 = 6ecba675e90d154f22e20200fa5684f20ad1495b73c0462f1bd7da4e9d0beaf8
# used for autoupdate
version = v0.6.6
EOF

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

expected="${HOME}/code/sentry/.devenv/bin/node"
got=$(command -v node)
if [[ "$got" != "$expected" ]]; then
    echo "unexpected node location ${got}, expected ${expected}"
    exit 1
fi

expected="${HOME}/code/sentry/.devenv/bin/yarn"
got=$(command -v yarn)
if [[ "$got" != "$expected" ]]; then
    echo "unexpected yarn location ${got}, expected ${expected}"
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

# devenv-bootstrap.sh overrides sentry devenv config.ini with this version
expected="1.22.22"
got=$(yarn --version)
if [[ "$got" != "$expected" ]]; then
    echo "unexpected yarn version ${got}, expected ${expected}"
    exit 1
fi

devenv delete

ls -lah "${HOME}/code/sentry/.devenv" || true

#if [[ ! -e "${HOME}/code/sentry/.devenv" ]]; then
#    echo "${HOME}/code/sentry/.devenv still exists"
#    exit 1
#fi

#if [[ ! -e "${HOME}/code/sentry/.venv" ]]; then
#    echo "${HOME}/code/sentry/.venv still exists"
#    exit 1
#fi

devenv delete --uninstall

if [[ ! -e "${HOME}/.local/share/sentry-devenv" ]]; then
    echo "${HOME}/.local/share/sentry-devenv still exists"
    exit 1
fi
