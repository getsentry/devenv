#!/bin/bash

if [[ "$(uname -s)" != Darwin ]]; then
    echo "Only macs are supported for now."
    exit 1
fi

branch=${1:-main}

devenv_cache="${HOME}/.cache/sentry-devenv"
devenv_root="${HOME}/.local/share/sentry-devenv"
devenv_bin="${devenv_root}/bin"
devenv_python_root="${devenv_root}/python"

mkdir -p "$devenv_cache" "$devenv_python_root" "$devenv_bin"

platform=x86_64
sha256=47e1557d93a42585972772e82661047ca5f608293158acb2778dccf120eabb00

case "$(uname -m)" in
    arm64)
      platform=aarch64
      sha256=cb6d2948384a857321f2aa40fa67744cd9676a330f08b6dad7070bda0b6120a4
      ;;
esac

archive="cpython-3.11.4+20230726-${platform}-apple-darwin-install_only.tar.gz"

echo "Installing devenv..."

[[ -f "${devenv_cache}/${archive}" ]] || \
    curl -fsSL \
    "https://github.com/indygreg/python-build-standalone/releases/download/20230726/${archive}" \
    -o "${devenv_cache}/${archive}"

echo "${sha256}  ${devenv_cache}/${archive}" | /usr/bin/shasum -a 256 --check --status

tar --strip-components=1 -C "$devenv_python_root" -x -f "${devenv_cache}/${archive}"

if ! [[ -d "${devenv_root}/devenv" ]]; then
    git -C "$devenv_root" clone -q -b "$branch" --depth=1 'https://github.com/getsentry/devenv.git'
fi

if [[ $CI ]]; then
    echo "export PATH=\"$devenv_bin:\$PATH\"" >> ~/.bashrc
else
    while ! /usr/bin/grep -qF "export PATH=\"${devenv_bin}:\$PATH\"" "${HOME}/.zshrc"; do
        read -r -p "Modify PATH in your .zshrc? If you use a different shell or prefer to modify PATH in your own way, say no [y/n]: " REPLY
        case $REPLY in
            [yY])
                echo "export PATH=\"$devenv_bin:\$PATH\"" >> ~/.zshrc
                ;;
            [nN])
                echo "Okay. Make sure ${devenv_bin} is in your PATH then."
                break
                ;;
            *) ;;
        esac
    done
fi

ln -sf "${devenv_root}/devenv/bin/devenv" "${devenv_bin}/devenv"
echo "devenv installed at ${devenv_bin}/devenv"

export PATH="${devenv_bin}:${PATH}"
devenv update

echo "All done! Open a new terminal and run 'devenv bootstrap' to create your development environment."
