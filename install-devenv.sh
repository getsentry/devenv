#!/bin/bash

if [[ "$(uname -s)" != Darwin ]]; then
    echo "Only macs are supported for now."
    exit 1
fi

# TODO: idempotent

devenv_root="${HOME}/.sentry-dev"
devenv_bin="${devenv_root}/bin"
devenv_python_root="${devenv_root}/python"

mkdir -p "$devenv_python_root" "$devenv_bin"

platform=x86_64
sha256=47e1557d93a42585972772e82661047ca5f608293158acb2778dccf120eabb00

case "$(uname -m)" in
    arm64)
      platform=aarch64
      sha256=cb6d2948384a857321f2aa40fa67744cd9676a330f08b6dad7070bda0b6120a4
      ;;
esac

archive="cpython-3.11.4+20230726-${platform}-apple-darwin-install_only.tar.gz"

tmpd=$(mktemp -d)
trap 'rm -rf "$tmpd"' EXIT

echo "Installing devenv..."

curl -fsSL \
    "https://github.com/indygreg/python-build-standalone/releases/download/20230726/${archive}" \
    -o "${tmpd}/${archive}"

echo "${sha256}  ${tmpd}/${archive}" | /usr/bin/shasum -a 256 --check --status

tar --strip-components=1 -C "$devenv_python_root" -x -f "${tmpd}/${archive}"

uri='git@github.com:getsentry/devenv'
[[ $CI ]] && uri='https://github.com/getsentry/devenv.git'
git -C "$devenv_root" clone -q --depth=1 "$uri"

if [[ ":$PATH:" != *":$devenv_bin:"* ]]; then
    echo "export PATH=\"$devenv_bin:\$PATH\"" >> ~/.bashrc
    echo "export PATH=\"$devenv_bin:\$PATH\"" >> ~/.zshrc
fi
ln -sf "${devenv_root}/devenv/devenv" "${devenv_bin}/devenv"

echo "devenv installed at ${devenv_bin}/devenv"

export PATH="${devenv_bin}:${PATH}"
devenv update

echo "All done! Open a new terminal and begin using devenv."
