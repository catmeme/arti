#
# Project:   catmeme
# Copyright: (c) 2024 catmeme - all rights reserved
#
# A GNU Makefile for the project.
#
SHELL := bash
.SHELLFLAGS := -euo pipefail -c

.DEFAULT_GOAL := help
.DELETE_ON_ERROR :
.MAKEFLAGS += --warn-undefined-variables --no-builtin-rules

export AWS_REGION ?= us-east-1
export DEPLOY_ENVIRONMENT ?= sandbox

ifndef AWS_ACCESS_KEY_ID
USE_AWS_PROFILE ?= "--profile=$(DEPLOY_ENVIRONMENT)-deployment"
endif

AWS_CALLER_ID = $(eval AWS_CALLER_ID := $$(shell aws $(USE_AWS_PROFILE) sts get-caller-identity))$(AWS_CALLER_ID)
AWS_CALLER_ARN = $(shell echo '$(AWS_CALLER_ID)' | jq -r .Arn)
AWS_ACCOUNT_ID = $(shell echo '$(AWS_CALLER_ID)' | jq -r .Account)

STACK_PREFIX ?= $(DEPLOY_ENVIRONMENT)
export PULUMI_CONFIG_PASSPHRASE ?=
PULUMI_ORGANIZATION_NAME := catmeme
PULUMI_POLICY_PACKS_DIR ?= pulumi-policy-packs
PULUMI_PROJECT_NAME := $$(grep -E "^name:" Pulumi.yaml | awk '{ print $$2 }')
PULUMI_STACK_BASE_NAME := $(PULUMI_ORGANIZATION_NAME).$(PULUMI_PROJECT_NAME).$(STACK_PREFIX)
PULUMI_STACK_NAME := $(PULUMI_STACK_BASE_NAME).$(AWS_REGION)

PULUMI_BACKEND_URL ?= file://.pulumi
PULUMI_CMD = export PULUMI_BACKEND_URL=$(PULUMI_BACKEND_URL); pulumi

DIST_DIR = dist

VENV = venv
ACTIVATE = . "$(VENV)/bin/activate"

BANDIT = $(ACTIVATE); bandit
BLACK = $(ACTIVATE); black
FLAKE8 = $(ACTIVATE); flake8
MYPY = $(ACTIVATE); mypy
PIP = $(ACTIVATE); pip3
PYLINT = $(ACTIVATE); pylint
PYTEST = $(ACTIVATE); pytest

.env: sample.env
	@if [ ! -e $(@) ]; then exit; fi; \
	get-env-var-keys() { grep -v ^'#' $${1} | awk -F "=" '{print $$1}' | sort; }; \
	DIFF_OUTPUT=$$(diff <(echo -e "$$(get-env-var-keys $(<))") <(echo -e "$$(get-env-var-keys $(@))")); \
	if [ -n "$${DIFF_OUTPUT}" ]; then \
		echo "Warning: differences between variables defined in $(<) (<) and $(@) (>):" >&2; \
		echo "$${DIFF_OUTPUT}" | grep ^"[\<\>]" | sort >&2; \
		echo >&2; \
		exit 1; \
	fi

# Build the application for distribution
build:
	@mkdir -p $(DIST_DIR)/app && cp -r src/* $(DIST_DIR)/app
.PHONY: build

# Remove all generated files
clean: clean-output
	@rm -fr $(DIST_DIR)
	@find . -name '__pycache__' -exec rm -rf {} +
	@find . -name '*.py[co]' -exec rm -f {} +
	@find src -type d -name "*.egg-info" -exec rm -rf {} +
	@rm -fr coverage/ .coverage .pytest_cache/ test-report.xml
.PHONY: clean

# Remove all generated video outputs
clean-output:
	@rm -fr output/
.PHONY: clean-output

# Deploy application to target environment
deploy: _pulumi-stack-init _pinecone-api-key
	@$(PULUMI_CMD) -s $(PULUMI_STACK_NAME) up --skip-preview -y
.PHONY: deploy

# Preview changes before deployment
deploy-preview: _pulumi-stack-init _pinecone-api-key
	@POLICY_PACKS_FLAGS=; \
	if [ -d $(PULUMI_POLICY_PACKS_DIR) ]; \
		then POLICY_PACKS_FLAGS=$$(find $(PULUMI_POLICY_PACKS_DIR) -name policy-config.json | awk -F "/" '{ print " --policy-pack "$$1"/"$$2" --policy-pack-config "$$1"/"$$2"/"$$3 }'); \
	fi; \
	$(PULUMI_CMD) -s $(PULUMI_STACK_NAME) preview $${POLICY_PACKS_FLAGS}
.PHONY: deploy-preview

# Install the python packages, dev dependencies, and setup in develop mode
develop: install
	@$(PIP) --require-virtualenv install -r requirements-dev.txt
.PHONY: develop

# Fix application code formatting
format:
	@$(BLACK) .
.PHONY: format

# Check application code formatting
format-check:
	@$(BLACK) --check .
.PHONY: format-check

# Install the python packages
install: venv
	@$(PIP) --require-virtualenv install -r requirements.txt -e .
.PHONY: install

# Run lint checks
lint:
	@EXIT_CODE=0; \
	$(FLAKE8) || EXIT_CODE=$$?; \
	$(MYPY) . || EXIT_CODE=$$?; \
	$(PYLINT) . || EXIT_CODE=$$?; \
	exit $${EXIT_CODE}
.PHONY: lint

# Refresh Pulumi's state against the target environment
pulumi-refresh:
	@$(PULUMI_CMD) -s $(PULUMI_STACK_NAME) refresh -y
.PHONY: pulumi-refresh

# Run application security tests
security-ast:
	@$(BANDIT) -c pyproject.toml -r .
.PHONY: security-ast

# Run package CVE scans
security-cve:
	@$(PIP) --require-virtualenv freeze | pip-audit
.PHONY: security-cve

# Run automated tests
test:
	@$(PYTEST)
.PHONY: test

# Run automated tests with coverage
test-coverage:
	@$(PYTEST) --cov \
		--cov-report=lcov:coverage/lcov.info \
		--cov-report=term-missing \
		--cov-report=xml:coverage/coverage.xml \
		--junitxml=test-report.xml \
		tests
.PHONY: test-coverage

# Rebuild the venv folder
venv: requirements.txt
	@python3 -m venv --upgrade-deps $(VENV)
	@grep -q $(VENV) .gitignore || echo "/$(VENV)/" >> .gitignore
.PHONY: venv

# Remove application from target environment
undeploy:
	@$(PULUMI_CMD) -s $(PULUMI_STACK_NAME) destroy
.PHONY: undeploy

# Require an environment variable to be set
_check-env-phony:
_check-env-%: _check-env-phony
	@if [ -z "$($(*))" ]; then echo "Required environment variable '$*' is not set"; exit 1; fi
.PHONY: _check-env-phony

# Ensure Pinecone API key is in environment
_pinecone-api-key:
PINECONE_API_KEY := $$(grep -o 'PINECONE_API_KEY=.*' .env | cut -d'=' -f2)
export PINECONE_API_KEY
.PHONY: _pinecone-api-key

# Create Pulumi stack if it doesn't exist
_pulumi-stack-init: _check-env-AWS_ACCOUNT_ID _check-env-PULUMI_BACKEND_URL
	@export PULUMI_BACKEND_URL=$(PULUMI_BACKEND_URL); \
	mkdir -p $(PWD)/.pulumi; \
	if [ ! -f "deploy/pulumi/Pulumi.$(PULUMI_STACK_NAME).yaml" ]; then \
		DEV_STACK_BASE_NAME=$(PULUMI_ORGANIZATION_NAME).$(PULUMI_PROJECT_NAME).sandbox; \
		DEV_STACK_NAME=$${DEV_STACK_BASE_NAME}.$(AWS_REGION); \
		printf "Stack config: $(PULUMI_STACK_NAME) doesn't exist, create from sandbox config (y/n)? "; \
		read ANSWER; \
		if [[ "$${ANSWER}" == "y" ]]; then \
			pulumi stack init $(PULUMI_STACK_NAME) --copy-config-from $${DEV_STACK_NAME} \
			&& $(PULUMI_CMD) -s $(PULUMI_STACK_NAME) config refresh 2> /dev/null; \
			PULUMI_APP_NAME=$$($(PULUMI_CMD) -s $(PULUMI_STACK_NAME) config get appName) \
			&& $(PULUMI_CMD) -s $(PULUMI_STACK_NAME) config set appName $(DEPLOY_ENVIRONMENT)-$${PULUMI_APP_NAME}; \
		fi; \
	else \
		$(PULUMI_CMD) stack init $(PULUMI_STACK_NAME) 2> /dev/null || true; \
	fi
	@if [ -n "$(CI)" ]; then sed -i.bak '\/aws:profile:/d' deploy/pulumi/Pulumi.$(PULUMI_STACK_NAME).yaml; fi
.PHONY: _pulumi-stack-init
