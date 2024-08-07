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

: PATH: "$PATH"

cd "$HOME"
# note: colima will be used and is necessary for a docker runtime on
#       macos GitHub runners
export DEVENV_FETCH_BRANCH=master
devenv bootstrap
devenv fetch sentry

# overwrite sentry's devenv config so we don't break
cat <<EOF > "$HOME/code/sentry/devenv/config.ini"
[venv.sentry]
python = 3.11.8
path = .venv
requirements = requirements-dev.txt
editable =
  .

[python3.11.8]
darwin_x86_64 = https://github.com/indygreg/python-build-standalone/releases/download/20240224/cpython-3.11.8+20240224-x86_64-apple-darwin-install_only.tar.gz
darwin_x86_64_sha256 = 097f467b0c36706bfec13f199a2eaf924e668f70c6e2bd1f1366806962f7e86e
darwin_arm64 = https://github.com/indygreg/python-build-standalone/releases/download/20240224/cpython-3.11.8+20240224-aarch64-apple-darwin-install_only.tar.gz
darwin_arm64_sha256 = 389a51139f5abe071a0d70091ca5df3e7a3dfcfcbe3e0ba6ad85fb4c5638421e
linux_x86_64 = https://github.com/indygreg/python-build-standalone/releases/download/20240224/cpython-3.11.8+20240224-x86_64-unknown-linux-gnu-install_only.tar.gz
linux_x86_64_sha256 = 94e13d0e5ad417035b80580f3e893a72e094b0900d5d64e7e34ab08e95439987
linux_arm64 = https://github.com/indygreg/python-build-standalone/releases/download/20240224/cpython-3.11.8+20240224-aarch64-unknown-linux-gnu-install_only.tar.gz
linux_arm64_sha256 = 389b9005fb78dd5a6f68df5ea45ab7b30d9a4b3222af96999e94fd20d4ad0c6a

[node]
darwin_x86_64 = https://storage.googleapis.com/sentry-dev-infra-assets/node/node-v20.13.1-darwin-x64.tar.xz
darwin_x86_64_sha256 = c83bffeb4eb793da6cb61a44c422b399048a73d7a9c5eb735d9c7f5b0e8659b6
darwin_arm64 = https://storage.googleapis.com/sentry-dev-infra-assets/node/node-v20.13.1-darwin-arm64.tar.xz
darwin_arm64_sha256 = e8a8e78b91485bc95d20f2aa86201485593685c828ee609245ce21c5680d07ce
linux_x86_64 = https://storage.googleapis.com/sentry-dev-infra-assets/node/node-v20.13.1-linux-x64.tar.xz
linux_x86_64_sha256 = efc0f295dd878e510ab12ea36bbadc3db03c687ab30c07e86c7cdba7eed879a9
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
version = v0.6.6
EOF

bash --login ci/devenv-post-bootstrap.sh
