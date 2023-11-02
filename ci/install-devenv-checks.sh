#!/bin/bash
exec </dev/null  # no interactive input
exec >&2  # helps keeps stdout/stderr outputs in order with each other
set -ex

devenv doctor --check-only || touch foo
devenv doctor --check-only
rm foo
echo 'y' | devenv doctor
echo '' | devenv doctor
