test: docker-image
	gh act -W .github/workflows/install-devenv.yml --pull=false

venv: requirements-dev.in
	rm -rf venv  # prevent recursion
	python3.11 -m venv --clear --prompt=devenv venv || \
		rm -rf venv  # failure
	./venv/bin/pip install -r requirements-dev.in -e . || \
		rm -rf venv  # failure
	touch venv  # success

docker-image:
	cd lib/gh-act && make
