#!/bin/bash
set -ex
devenv doctor --check-only || touch foo
devenv doctor --check-only
rm foo
echo '' | devenv doctor
devenv doctor
