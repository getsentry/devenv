all: .all.done
.all.done: Dockerfile ./docker-build.sh ~/.docker/cli-plugins/docker-buildx
	./docker-build.sh && touch $@

~/.docker/cli-plugins/docker-buildx:
	# https://github.com/Homebrew/homebrew-core/blob/668e9f15f/Formula/d/docker-buildx.rb#L40-L42
	mkdir -p ~/.docker/cli-plugins
	ln -sfn $$(which docker-buildx) ~/.docker/cli-plugins/
