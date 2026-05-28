# Tech-blog — TaskMaster-style orchestration names (thin wrappers).
# Run from repository root: cd /path/to/tech-blog

.PHONY: test lint generate cdk-synth cdk-drop-layer-import ui-install ui-build ui-deploy help

PYTHON ?= python3
PYTEST = PYTHONPATH=backend $(PYTHON) -m pytest backend/tests
RUFF = $(PYTHON) -m ruff

help:
	@echo "Targets:"
	@echo "  make test        - pytest backend/tests (needs: pip install -r infrastructure/requirements-dev.txt)"
	@echo "  make lint        - ruff check + format --check on backend/"
	@echo "  make generate    - placeholder: OpenAPI -> Python/TS codegen (not wired yet)"
	@echo "  make ui-deploy   - sync ui/dist to S3 + invalidate CloudFront (after cdk deploy)"
	@echo "  make ui-build    - npm run build in ui/"
	@echo "  make cdk-synth   - CDK synth (backend layer build + synth)"
	@echo "  make cdk-drop-layer-import - deploy Api only; drop SharedLayer cross-stack import"

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
	python backend/build.py
	cd infrastructure && APP_ENV=dev CDK_DEFAULT_ACCOUNT=111111111111 CDK_DEFAULT_REGION=us-east-1 \
		npx --yes aws-cdk@2.114.1 synth

cdk-drop-layer-import:
	bash scripts/drop-shared-layer-import.sh

ui-install:
	cd ui && npm install

ui-build:
	cd ui && npm ci && npm run build

ui-deploy: ui-build
	bash scripts/deploy-frontend.sh
