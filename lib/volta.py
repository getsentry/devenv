# we should download this stuff to ~/.local/share/sentry-devenv/bin
# since it's already on the path
# https://github.com/volta-cli/volta/releases/download/v1.1.1/volta-1.1.1-macos-aarch64.tar.gz
# https://github.com/volta-cli/volta/releases/download/v1.1.1/volta-1.1.1-macos.tar.gz
# export VOLTA_HOME=~/.local/share/sentry-devenv/volta
# we also need VOLTA_HOME/bin on PATH, use idempotent_add
# executing volta -v will populate the VOLTA_HOME directory,
# we should check to see if VOLTA_HOME/bin/node is present
from __future__ import annotations
