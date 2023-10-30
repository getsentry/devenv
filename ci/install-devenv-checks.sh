#!/bin/bash
exec </dev/null  # no interactive input
set -ex


devenv doctor --check-only || touch foo
devenv doctor --check-only
rm foo
echo 'y' | devenv doctor
echo '' | devenv doctor
