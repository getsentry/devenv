# Steps are split smaller than strictly necessary to allow later,
# faster-changing steps to not affect caching of earlier, more stable steps.

#FROM catthehacker/ubuntu:act-latest AS builder
FROM debian:bullseye-slim AS builder

ARG GITHUB_ARCH
ARG PYTHON_VERSION

# make local scripts available
ADD ./apt-install ./apt-install

# minimum prerequisites to fetch source
RUN ./apt-install git wget ca-certificates

# pyenv
RUN git clone https://github.com/pyenv/pyenv /opt/pyenv
ENV PATH="$PATH:/opt/pyenv/bin"

# pyenv cache
ENV PYTHON_BUILD_CACHE_PATH /opt/pyenv-cache
run mkdir -p "$PYTHON_BUILD_CACHE_PATH"
# fail but populate cache
RUN set -ex; pyenv install --verbose "$PYTHON_VERSION" \
  || : "expected failure while populating cache"

# build prereqs: https://devguide.python.org/getting-started/setup-building/#install-dependencies
RUN ./apt-install build-essential pkg-config 
RUN ./apt-install gdb lcov \
      libbz2-dev libffi-dev libgdbm-dev libgdbm-compat-dev liblzma-dev \
      libncurses5-dev libreadline6-dev libsqlite3-dev libssl-dev \
      lzma lzma-dev tk-dev uuid-dev zlib1g-dev


# pyenv install
RUN set -ex; pyenv install --verbose "$PYTHON_VERSION"

# put python into the expected spot, for GHA
ADD ./hostedtoolcache-python.sh ./hostedtoolcache-python.sh
RUN set -ex; ./hostedtoolcache-python.sh "$GITHUB_ARCH" "$PYTHON_VERSION"

#FROM catthehacker/ubuntu:act-latest
FROM debian:bullseye-slim

COPY --from=builder /opt/hostedtoolcache/Python /opt/hostedtoolcache/Python
COPY --from=builder /root/.pyenv/versions /root/.pyenv/versions
ADD ./apt-install ./apt-install

# minimum prerequisites to fetch source
RUN ./apt-install git wget ca-certificates
# used in CI:
RUN ./apt-install sudo
# used by homebrew:
RUN ./apt-install procps
RUN ls -l /bin/ps
