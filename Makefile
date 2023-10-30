test: docker-image
	gh act -W .github/workflows/install-devenv.yml --pull=false

venv:
	python3.11 -m venv --clear --prompt=devenv venv || rm -rf venv
	./venv/bin/pip install -r requirements-dev.in -e .


docker-image:
	cd lib/gh-act && make
