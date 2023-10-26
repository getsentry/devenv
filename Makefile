test: docker-image
	gh act -W .github/workflows/install-devenv.yml --pull=false


docker-image:
	cd lib/gh-act && make
