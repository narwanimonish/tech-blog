# Tech-blog — TaskMaster-style orchestration names (thin wrappers).
# Run from repository root: cd /path/to/tech-blog

.PHONY: test lint generate build-layer build-layer-cython cdk-synth cdk-drop-layer-import cdk-diagnose-api ui-install ui-build ui-deploy postman-install postman-smoke postman-perf help

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
	@echo "  make build-layer   - layer_bundle (pure Python, local dev)"
	@echo "  make build-layer-cython - layer_bundle with Cython .so (needs Docker on macOS)"
	@echo "  make cdk-synth   - CDK synth (backend layer build + synth)"
	@echo "  make cdk-drop-layer-import - deploy Api only; drop SharedLayer cross-stack import"
	@echo "  make cdk-diagnose-api    - check stack status, export lock, API smoke tests"
	@echo "  make postman-smoke       - Newman API smoke (needs postman/environments/local.postman_environment.json)"
	@echo "  make postman-perf        - Newman read-only performance loop (see postman/README.md)"
	@echo "  make postman-pipeline    - smoke + perf like CI (needs POSTMAN_USERNAME/PASSWORD env vars)"

test:
	$(PYTEST) -v

lint:
	$(RUFF) check backend/
	$(RUFF) format --check backend/

generate:
	@echo "Not wired yet. Add openapi-generator or datamodel-codegen against backend/api-spec.yaml, then:"
	@echo "  e.g. openapi-python-client generate --path backend/api-spec.yaml ..."
	@exit 0

build-layer:
	$(PYTHON) backend/build.py

build-layer-cython:
	CYTHONIZE=1 $(PYTHON) backend/build.py

cdk-synth:
	CYTHONIZE=1 $(PYTHON) backend/build.py
	cd infrastructure && APP_ENV=dev CDK_DEFAULT_ACCOUNT=111111111111 CDK_DEFAULT_REGION=us-east-1 \
		npx --yes aws-cdk@2.114.1 synth

cdk-drop-layer-import:
	bash scripts/drop-shared-layer-import.sh

cdk-diagnose-api:
	bash scripts/diagnose-api.sh

ui-install:
	cd ui && npm install

ui-build:
	cd ui && npm ci && npm run build

ui-deploy: ui-build
	bash scripts/deploy-frontend.sh

postman-install:
	cd postman && npm install

postman-smoke: postman-install
	bash scripts/postman-run.sh smoke

postman-perf: postman-install
	bash scripts/postman-run.sh perf

postman-pipeline: postman-install
	bash scripts/postman-ci.sh pipeline
