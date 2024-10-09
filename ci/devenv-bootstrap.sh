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
darwin_x86_64 = https://github.com/lima-vm/lima/releases/download/v0.23.2/lima-0.23.2-Darwin-x86_64.tar.gz
darwin_x86_64_sha256 = bdb833f4ccd76255a4718bc4c0014b898acbc0a1c249731baf441d3c5070e567
darwin_arm64 = https://github.com/lima-vm/lima/releases/download/v0.23.2/lima-0.23.2-Darwin-arm64.tar.gz
darwin_arm64_sha256 = 8b75ccfb166df348430df7ebd15cd50b6f980d40ed4b765ee3b14a6e805ae311
linux_x86_64 = https://github.com/lima-vm/lima/releases/download/v0.23.2/lima-0.23.2-Linux-x86_64.tar.gz
linux_x86_64_sha256 = 5d0034316096e3f3ceedcb2e1dcac7c7d380e26defb59a5894eaf1e3265b191e
linux_arm64 = https://github.com/lima-vm/lima/releases/download/v0.23.2/lima-0.23.2-Linux-aarch64.tar.gz
linux_arm64_sha256 = 299d36898204a0e9c1b3b8a4ae750c129ed7b84ce062e2c51cd5224da4874a43
# used for autoupdate
version = 0.23.2
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
