# Tech-blog — TaskMaster-style orchestration names (thin wrappers).
# Run from repository root: cd /path/to/tech-blog

.PHONY: test lint generate cdk-synth help

PYTHON ?= python3
PYTEST = PYTHONPATH=backend $(PYTHON) -m pytest backend/tests
RUFF = $(PYTHON) -m ruff

help:
	@echo "Targets:"
	@echo "  make test        - pytest backend/tests (needs: pip install -r infrastructure/requirements-dev.txt)"
	@echo "  make lint        - ruff check + format --check on backend/"
	@echo "  make generate    - placeholder: OpenAPI -> Python/TS codegen (not wired yet)"
	@echo "  make cdk-synth   - CDK synth (needs: cd infrastructure && deps + AWS account/region)"

test:
	$(PYTEST) -v

lint:
	$(RUFF) check backend/
	$(RUFF) format --check backend/

generate:
	@echo "Not wired yet. Add openapi-generator or datamodel-codegen against backend/api-spec.yaml, then:"
	@echo "  e.g. openapi-python-client generate --path backend/api-spec.yaml ..."
	@exit 0

cdk-synth:
	@command -v cdk >/dev/null 2>&1 || (echo "Install CDK CLI: npm install -g aws-cdk"; exit 1)
	cd infrastructure && cdk synth
