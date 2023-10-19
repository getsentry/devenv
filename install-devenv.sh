#!/bin/bash
set -euo pipefail
PS4='+\033]33;1m$\033m ' 

# let users see important commands
show() {(set -x; "$@"); }
# check if a command exists
has() { command -v "$@" >/dev/null; }
yesno() { # ask a question
  prompt="$1 [y/n]: "
  while :; do
    if [[ "$CI" ]]; then
      REPLY="yes"
      echo "$prompt$REPLY"
    else
      read -r -p "$prompt"
    fi

    case $REPLY in
        [yY]*) return 0 ;;
        [nN]*) return 1 ;;
        *) echo "Unrecognized response.";;
    esac
  done
}

SNTY_DEVENV_REPO="${SNTY_DEVENV_REPO:-https://github.com/getsentry/devenv.git}"
SNTY_DEVENV_BRANCH="${1:-${SNTY_DEVENV_BRANCH:-main}}"

XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
SNTY_DEVENV_HOME="${SNTY_DEVENV_HOME:-$XDG_DATA_HOME/sentry-devenv}"
devenv_bin="$SNTY_DEVENV_HOME/bin"
devenv_venv="$SNTY_DEVENV_HOME/venv"

if [[ "${DEBUG:-}" || "${SNTY_DEVENV_DEBUG:-}" ]]; then
  set -x
fi

if ! has brew; then
  if yesno "This tool requires Homebrew. Install now?"; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  else
    return 1
  fi
fi

echo "Installing devenv..."

# NB: eval separately to avoid gobbling errors
eval="$(brew shellenv)"
eval "$eval"
show brew install python@3.11 git

python3.11 -m venv "$devenv_venv"

"$devenv_venv"/bin/pip install "git+$SNTY_DEVENV_REPO@$SNTY_DEVENV_BRANCH"

mkdir -p "$SNTY_DEVENV_HOME/bin"
ln -sf "$devenv_venv/bin/devenv" "$devenv_bin/"
echo "devenv installed at $devenv_bin/devenv"

export="export PATH='\$PATH:$devenv_bin'"
if [[ -e ~/.profile ]] && grep -qFx "$export" ~/.profile; then
  : 'already done!'
elif yesno "Modify PATH in your ~/.profile? If you use a different shell or prefer to modify PATH in your own way, say no"; then
  echo "$export" >> ~/.profile
else
  echo "Okay. Make sure $devenv_bin is in your PATH then."
  break
fi

echo "All done! Run 'devenv bootstrap' to create your development environment."
"$SHELL" -l  # start a new login shell, to get fresh env
