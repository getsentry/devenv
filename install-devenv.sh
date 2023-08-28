#!/bin/bash

if [[ "$(uname -s)" != Darwin ]]; then
    echo "Only macs are supported for now."
    exit 1
fi

# TODO: idempotent

devenv_root="${HOME}/.config/sentry-dev"
devenv_python_root="${devenv_root}/python"
mkdir -p "$devenv_python_root"

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

curl -fsSL \
    "https://github.com/indygreg/python-build-standalone/releases/download/20230726/${archive}" \
    -o "${tmpd}/${archive}"

echo "${sha256}  ${tmpd}/${archive}" | /usr/bin/shasum -a 256 --check --status

tar --strip-components=1 -C "$devenv_python_root" -x -f "${tmpd}/${archive}"

# install latest devenv tool, which should be able to self-update
git clone -C "$devenv_root" --depth=1 git@github.com:getsentry/devenv

devenv () {
    _pwd="$PWD"
    (
        cd "$devenv_root" || echo "failed to cd to ${devenv_root}"; exit 1
        "${devenv_python_root}/bin/python3" -m devenv.main "$_pwd" "$@"
    )
}
