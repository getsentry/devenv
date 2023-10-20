#!/bin/bash
# Manual test:
#   export DEBUG=1
#   export SNTY_DEVENV_REPO=file://$PWD
#   export SNTY_DEVENV_BRANCH="$(git branch --show-current)"
#   ./install-devenv.sh
set -euo pipefail

## functions
# let users see important commands
show() {(set -x; "$@")}
# check if a command exists
has() { command -v "$@" >/dev/null; }
# tell the user something
info() { colorize "$ansi_teal" "$@"; }
# warn the user
warn() { colorize "$ansi_yellow" "$@"; }
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

## constants
XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
# a few color codes
ansi_yellow=$'\x1b[33m'
ansi_green=$'\x1b[1;34m'
ansi_teal=$'\x1b[36m'
ansi_reset=$'\x1b[m'
# fancy "prompt" for xtrace log
export PS4="+ $ansi_green\$$ansi_reset "

parseopt() {  # argument (and environment-var) processing
  # control install behavior
  SNTY_DEVENV_REPO="${SNTY_DEVENV_REPO:-https://github.com/getsentry/devenv.git}"
  SNTY_DEVENV_BRANCH="${1:-${SNTY_DEVENV_BRANCH:-main}}"
  SNTY_DEVENV_HOME="${SNTY_DEVENV_HOME:-$XDG_DATA_HOME/sentry-devenv}"
  if [[ "${DEBUG:-}" || "${SNTY_DEVENV_DEBUG:-}" ]]; then
    set -x
  fi
}

main() {
  parseopt "$@"
  devenv_bin="$SNTY_DEVENV_HOME/bin"
  devenv_venv="$SNTY_DEVENV_HOME/venv"

  info "Installing dependencies..."

  if ! has brew; then
    if yesno "This tool requires Homebrew. Install now?"; then
      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
      return 1
    fi
  fi

  # NB: eval separately to avoid gobbling errors
  eval="$(brew shellenv)"
  eval "$eval"
  show brew install python@3.11 git

  show python3.11 -m venv --clear "$devenv_venv"

  show "$devenv_venv"/bin/pip install "git+$SNTY_DEVENV_REPO@$SNTY_DEVENV_BRANCH"

  mkdir -p "$SNTY_DEVENV_HOME/bin"
  ln -sf "$devenv_venv/bin/devenv" "$devenv_bin/"
  info "devenv installed at $devenv_bin/devenv"

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

main "$@"
