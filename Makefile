VERSION_TO_BUILD ?= 2.0.6-alpine

PROJECTPATH=$(dir $(realpath $(lastword $(MAKEFILE_LIST))))
CHARM_BUILD_DIR ?= ${PROJECTPATH:%/=%}
METADATA_FILE="metadata.yaml"
CHARM_NAME=$(shell cat ${PROJECTPATH}/${METADATA_FILE} | awk '/^name:/ {print $$2".charm"}')

blacken:
	@echo "Normalising python layout with black."
	@tox -e black


lint: blacken
	@echo "Running flake8"
	@tox -e lint

# We actually use the build directory created by charmcraft,
# but the .charm file makes a much more convenient sentinel.
unittests: build
	@tox -e unit

build:
	@echo "Building charm to ${CHARM_BUILD_DIR}/${CHARM_NAME}"
	@-git rev-parse HEAD > ./repo-info
	@cd ${CHARM_BUILD_DIR} && TERM=linux charmcraft build -f ${PROJECTPATH}

# TODO: fix functional tests, broken with juju 2.9.0 + zaza 94abaf1 + microk8s v1.20.6
test: lint unittests #functional
	@echo "Tests completed for charm ${CHARM_NAME}."

functional: build
	@echo "Executing functional tests in ${CHARM_BUILD_DIR}"
	@CHARM_BUILD_DIR=${CHARM_BUILD_DIR} tox -e functional

clean:
	@echo "Cleaning files"
	@git clean -fXd -e '!.idea'
	@echo "Cleaning existing build"
	@rm -rf ${CHARM_BUILD_DIR}/${CHARM_NAME}

image-build:
	@echo "Building the image."
	@docker build \
		--build-arg VERSION_TO_BUILD=$(VERSION_TO_BUILD) \
		-t influxdb:$(VERSION_TO_BUILD) \
		.

.PHONY: blacken lint unittests test clean image-build build
