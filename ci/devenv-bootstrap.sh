# shellcheck disable=all

# we don't have permissions to clone getsentry which is a good thing
# eventually we should move this bootstrap testing over to getsentry repo
# in the meantime, mock it so that pip install -e has something to chew on
mkdir -p "${HOME}/dev/getsentry"
cat <<EOF > "${HOME}/dev/getsentry/pyproject.toml"
[project]
name = "getsentry-mock"
version = "0.0.0"
EOF

# note: colima will be used and is necessary for a docker runtime on
#       macos GitHub runners
yes '' | devenv bootstrap

cd $HOME/dev/sentry
direnv allow
