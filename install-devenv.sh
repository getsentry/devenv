#!/bin/bash
# Manual test:
#   export DEBUG=1
#   export SNTY_DEVENV_REPO=file://$PWD
#   export SNTY_DEVENV_BRANCH="$(git branch --show-current)"
#   ./install-devenv.sh
PATH=/usr/bin:/bin:/usr/sbin:/sbin
#HERE="$(cd "$(dirname "$0")"; pwd)"
ME="$(basename "$0")"

## functions
# let users see important commands
show() {(set -x; "$@")}
# check if a command exists
has() { command -v "$@" >/dev/null; }
# tell the user something
info() { colorize "$ansi_teal" "$@"; }
# warn the user
warn() { colorize "$ansi_yellow" "$@"; }
error() { colorize "$ansi_red" "$@"; exit 1; }
yesno() { # ask a question
  prompt="$1$ansi_green [y/n]$ansi_reset: "
  while :; do
    if [[ "${CI:-}" ]]; then
      REPLY="yes"
      echo -n "$prompt"
      info "$REPLY"
    else
      read -r -p "$prompt"
    fi

    case $REPLY in
        [yY]*) return 0 ;;
        [nN]*) return 1 ;;
        *) warn "Unrecognized response.";;
    esac
  done
}
# show a colorized message
colorize() {
  color="$1"
  shift 1
  message="$*"
  echo >&2 "$color$message$ansi_reset"
}
http-get() {(
  # print the content of a (https) URL to stdout
  url="$1"
  if has curl; then
    curl -q -sSLf "$url"
  elif has wget; then
    wget -nv -O- "$url"
  else
    error 'Please install `curl` or `wget` and try again'
  fi
)}

constants() {
  # a few color codes
  ansi_yellow=$'\x1b[33m'
  ansi_red=$'\x1b[31m'
  ansi_green=$'\x1b[1;34m'
  ansi_teal=$'\x1b[36m'
  ansi_reset=$'\x1b[m'
  # fancy "prompt" for xtrace log
  export PS4="+ $ansi_green\$$ansi_reset "

  if [[ "${DEBUG:-}" || "${SNTY_DEVENV_DEBUG:-}" ]]; then
    set -x
    colorize() { :; }  # show messages just once
  fi

  # default values for system environment variables
  USER=$(id -un)
  HOME=$(eval 'echo ~')
  XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
  XDG_CACHE_HOME="${XDG_DATA_HOME:-$HOME/.cache}"
  OSTYPE="${OSTYPE:-$(uname -s | tr -d '0-9.' | tr '[:upper:]' '[:lower:]')}"
  CPUTYPE="${CPUTYPE:-$(uname -m)}"
}

parseopt() {  # argument (and environment-var) processing
  appname="sentry-devenv"
  # control install behavior
  SNTY_DEVENV_REPO="${SNTY_DEVENV_REPO:-https://github.com/getsentry/devenv.git}"
  SNTY_DEVENV_BRANCH="${1:-${SNTY_DEVENV_BRANCH:-main}}"
  SNTY_DEVENV_HOME="${SNTY_DEVENV_HOME:-$XDG_DATA_HOME/$appname}"
  SNTY_DEVENV_CACHE="${SNTY_DEVENV_CACHE:-$XDG_CACHE_HOME/$appname}"
  SNTY_DEVENV_PY_RELEASE="${SNTY_DEVENV_PY_RELEASE:-20230726}"
  SNTY_DEVENV_PY_VERSION="${SNTY_DEVENV_PY_VERSION:-3.11.4}"
}

# translate from uname output to indygreg release tags:
# e.g. https://github.com/indygreg/python-build-standalone/releases
indygreg_os() {
  case "$OSTYPE" in
    darwin) echo apple-darwin ;;
    linux|linux-gnu) echo unknown-linux-gnu ;;
    *) echo '??' ;;
  esac
}
indygreg_cpu() {
  case "$CPUTYPE" in
    arm64)
      echo aarch64 ;;
    aarch64|x86_64)
      echo "$CPUTYPE" ;;
    *)
      echo '??' ;;
  esac
}

_check_checksum() {
  if has shasum; then
    shasum -a 256 --check --status
  elif has openssl; then
    "$openssl" dgst -sha256
  fi
}

check_checksum() {
  sha256="$1"
  path="$2"
  test -f "$path"
  echo "${sha256}  $path" | shasum -a 256 --check --status
}

install_python() {
  release="$1"
  version="$2"
  platform="$OSTYPE-$CPUTYPE"
  indygreg_platform="$(indygreg_cpu)-$(indygreg_os)"

  case "$platform" in
    darwin-arm64) sha256=cb6d2948384a857321f2aa40fa67744cd9676a330f08b6dad7070bda0b6120a4;;
    darwin-x86_64) sha256=47e1557d93a42585972772e82661047ca5f608293158acb2778dccf120eabb00;;
    linux-gnu-x86_64) sha256=e26247302bc8e9083a43ce9e8dd94905b40d464745b1603041f7bc9a93c65d05;;
    linux-gnu-aarch64) sha256=e26247302bc8e9083a43ce9e8dd94905b40d464745b1603041f7bc9a93c65d05;;
    *)
      error "Unexpected platform; please contact <team-devenv@sentry.io>: ($platform -> $indygreg_platform)"
      ;;
  esac


  tarball="cpython-$version+$release-$indygreg_platform-install_only.tar.gz"
  src="https://github.com/indygreg/python-build-standalone/releases/download/$release/$tarball" \
  dst="$SNTY_DEVENV_CACHE/${tarball}"
  if check_checksum "$sha256" "$dst"; then
    echo "Using cached python download..."
  else
    mkdir -p "$(dirname "$dst")"
    http-get "$src" > "$dst"
    check_checksum "$sha256" "$dst"
  fi

  mkdir -p "$SNTY_DEVENV_HOME/python${version}"
  tar --strip-components=1 -C "$SNTY_DEVENV_HOME/python" -x -f "${SNTY_DEVENV_CACHE}/${tarball}"
  ln -sfn "$SNTY_DEVENV_HOME/python${version}" "$SNTY_DEVENV_HOME/python"
}

main() {
  constants
  parseopt "$@"
  devenv_bin="${SNTY_DEVENV_HOME:?}/bin"  # :? causes an error on empty-string
  devenv_venv="$SNTY_DEVENV_HOME/venv"

  info "Installing dependencies..."
  install_python "$SNTY_DEVENV_PY_RELEASE" "$SNTY_DEVENV_PY_VERSION"

  export PATH="$SNTY_DEVENV_HOME/python/bin:$PATH"
  show "$(which python)" -m venv --clear "$devenv_venv"

  show "$devenv_venv"/bin/pip install "git+$SNTY_DEVENV_REPO@$SNTY_DEVENV_BRANCH"

  rm -rf "$devenv_bin"
  mkdir -p "$devenv_bin"
  ln -sfn "$devenv_venv/bin/devenv" "$devenv_bin/"
  info "devenv installed, at: $devenv_bin/devenv"

  export="export PATH=\"\$PATH:$devenv_bin\""
  if [[ -e ~/.profile ]] && grep -qFx "$export" ~/.profile; then
    : 'already done!'
  elif yesno "Modify PATH in your ~/.profile? If you use a different shell or prefer to modify PATH in your own way, say no"; then
    echo "$export" >> ~/.profile
  else
    info "Okay. Make sure $devenv_bin is in your PATH then."
  fi

  ## fin
  info "All done! Run 'devenv bootstrap' to create your development environment."
  show "$SHELL" -l  # start a new login shell, to get fresh env
}

if [[ "$ME" = "install-devenv.sh" ]]; then
  set -eEuo pipefail
  main "$@"
else
  : This file is being sourced as a library, for testing.
fi
