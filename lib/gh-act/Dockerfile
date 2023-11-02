# Steps are split smaller than strictly necessary to allow later, faster
# changing steps to not invalidate the cache of earlier, more stable steps.

ARG GITHUB_ARCH
ARG PYTHON_VERSION
# required for homebrew:
# https://github.com/Homebrew/brew/blob/master/Library/Homebrew/utils/ruby.sh#L3
ARG RUBY_VERSION=2.6.10

#############################
## base image: reused everywhere
FROM debian:bullseye-slim AS base

# minimum prerequisites to fetch source
ADD ./apt-install /usr/local/bin/apt-install
RUN apt-install git wget ca-certificates

# grant sudo access (passwordless) to a "wheel" group (the usual name)
RUN apt-install sudo
RUN groupadd wheel
RUN echo '%wheel ALL=(ALL:ALL) NOPASSWD: ALL' >  /etc/sudoers.d/wheel

# create a "runner" and a "builder" users (with sudo access)
RUN useradd -G wheel --create-home runner
RUN useradd -G wheel --create-home builder


#############################
## base builder image: reused between pyenv and rbenv
FROM base AS base-builder
# bare essentials to build anything
RUN apt-install build-essential pkg-config

# builder tools and outputs go here:
RUN chown builder /opt
ENV PATH="$PATH:/opt/builder/bin"
RUN ls -la /opt

# enable debug logging
ENV VERBOSE=1 DEBUG=1 KEEP=1
# make faster, please
ENV MAKEFLAGS="-j 30"

# run commands as "builder" by default
USER builder
WORKDIR /home/builder

# local script, used later


#############################
## builder image: python
FROM base-builder as pyenv
ARG GITHUB_ARCH
ARG PYTHON_VERSION

# pyenv
RUN git clone https://github.com/pyenv/pyenv /opt/builder

# pyenv prereqs: https://devguide.python.org/getting-started/setup-building/#install-dependencies
RUN apt-install gdb lcov \
      libbz2-dev libffi-dev libgdbm-dev libgdbm-compat-dev liblzma-dev \
      libncurses5-dev libreadline6-dev libsqlite3-dev libssl-dev \
      lzma lzma-dev tk-dev uuid-dev zlib1g-dev

# pyenv install
RUN set -eux; pyenv install --verbose "$PYTHON_VERSION"

# put python into the expected spot, for GHA
ADD hostedtoolcache.sh hostedtoolcache.sh
ADD hostedtoolcache-python.sh hostedtoolcache-python.sh
RUN set -eux; ./hostedtoolcache-python.sh "$PYTHON_VERSION" "$GITHUB_ARCH"


#############################
## builder image: ruby
FROM base-builder as rbenv
ARG GITHUB_ARCH
ARG RUBY_VERSION

# they want us to clone two repos for this; so weird
RUN git clone https://github.com/rbenv/rbenv /opt/builder
RUN git clone https://github.com/rbenv/ruby-build "$(rbenv root)"/plugins/ruby-build

# rbenv prereqs: https://github.com/rbenv/ruby-build/wiki#ubuntudebianmint
RUN apt-install \
    autoconf patch build-essential rustc libssl-dev libyaml-dev \
    libreadline6-dev zlib1g-dev libgmp-dev libncurses5-dev libffi-dev libgdbm6 \
    libgdbm-dev libdb-dev uuid-dev \
;

# rbenv install
RUN set -eux; rbenv install --verbose "$RUBY_VERSION"

# put ruby into the expected spot, for GHA
ADD hostedtoolcache.sh hostedtoolcache.sh
ADD hostedtoolcache-ruby.sh hostedtoolcache-ruby.sh
RUN set -eux; ./hostedtoolcache-ruby.sh "$RUBY_VERSION" "$GITHUB_ARCH"


#############################
## main image: used to emulate a GHA worker
FROM base as runner
# run commands as "runner" by default
USER runner
WORKDIR /home/runner

# used in CI:
RUN apt-install sudo zsh
# used by homebrew:
RUN apt-install build-essential procps curl file git

# emulate macos, a little:
RUN sudo chsh -s /bin/zsh runner

# avoid zsh's "new user" configuration script
RUN cp /etc/zsh/newuser.zshrc.recommended ~/.zshrc

# these operations are cheap:
COPY --from=pyenv /opt/hostedtoolcache/Python /opt/hostedtoolcache/Python
COPY --from=pyenv /home/builder/.pyenv/versions /home/builder/.pyenv/versions
COPY --from=rbenv /opt/hostedtoolcache/Ruby /opt/hostedtoolcache/Ruby
COPY --from=rbenv /home/builder/.rbenv/versions /home/builder/.rbenv/versions

ARG GITHUB_ARCH
RUN sudo ln -v -svn /opt/hostedtoolcache/*/*/$GITHUB_ARCH/bin/* /usr/local/bin
