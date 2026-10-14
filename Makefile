test: docker-image
	gh act -W .github/workflows/bootstrap.yml --pull=false

docker-image:
	cd lib/gh-act && make
