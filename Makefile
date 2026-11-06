FRONTEND_IMAGE ?= frontend
CONTENT_IMAGE ?= content
PDF_IMAGE ?= pdf

ifeq ($(OS),Windows_NT)
PYTHON ?= python
HOST_UID ?= 1000
HOST_GID ?= 1000
else
PYTHON ?= python3
HOST_UID ?= $(shell id -u)
HOST_GID ?= $(shell id -g)
endif

SITE_URL ?= https://autophany.space
CLI = $(PYTHON) -m scripts.cli

DOCKER_ENV = -e SITE_URL="$(SITE_URL)" -e STRICT_PDF=1
DOCKER_VOLUMES = \
	-v "$(CURDIR)/content:/app/content:ro" \
	-v "$(CURDIR)/scripts:/app/scripts:ro" \
	-v "$(CURDIR)/templates:/app/templates:ro" \
	-v "$(CURDIR)/public:/app/public" \
	-v "$(CURDIR)/dist:/app/dist" \
	-v "$(CURDIR)/generated:/app/generated" \
	-v "$(CURDIR)/.cache:/app/.cache"
DOCKER_RUN = docker run --rm $(DOCKER_ENV) $(DOCKER_VOLUMES)
DOCKER_CLI = $(DOCKER_RUN) $(CONTENT_IMAGE) python3 -m scripts.cli
DOCKER_FRONTEND = $(DOCKER_RUN) $(FRONTEND_IMAGE)
DOCKER_PDF = $(DOCKER_RUN) $(PDF_IMAGE) python3 -m scripts.cli

.PHONY: help install dev dev-host preview typecheck test nginx-check preflight toolchain create html pdf frontend prerender seo verify build clean docker-build docker-check docker-toolchain docker-site docker-build-site docker-preview docker-shell

help:
	@echo "autophany.space build commands"
	@echo "  make install           install npm and Python dependencies"
	@echo "  make dev               build pages and preview locally"
	@echo "  make build             full production build"
	@echo "  make test              run Python tests"
	@echo "  make nginx-check       validate nginx config"
	@echo "  make clean             remove build output and caches"
	@echo "  make docker-build-site build images and run full Docker build"
	@echo "  make docker-site       run full build in existing images"
	@echo "  make docker-preview    serve dist with nginx on :8080"

install:
	npm ci
	$(PYTHON) -m pip install -r requirements.txt

dev: html frontend prerender
	npm run preview

dev-host: html frontend prerender
	npm run preview -- --host 0.0.0.0 --port 4173

preview:
	npm run preview

typecheck:
	npm run typecheck

test:
	$(PYTHON) -m unittest discover -s tests -v

nginx-check:
	sh deploy/nginx/check.sh

preflight:
	$(CLI) preflight

toolchain:
	$(PYTHON) scripts/check_tools.py host

create:
	$(CLI) create $(ARGS)

html:
	$(CLI) html

pdf:
	$(CLI) pdf

frontend:
	npm run build

prerender:
	$(CLI) prerender

seo:
	$(CLI) seo

verify:
	$(CLI) verify

build: preflight toolchain test html pdf typecheck frontend prerender seo verify

clean:
	$(CLI) clean

docker-build:
	docker build -f docker/frontend/Dockerfile -t $(FRONTEND_IMAGE) .
	docker build -f docker/content/Dockerfile -t $(CONTENT_IMAGE) .
	docker build -f docker/pdf/Dockerfile -t $(PDF_IMAGE) .

docker-check:
	docker run --rm $(CONTENT_IMAGE) python3 scripts/check_tools.py content
	docker run --rm $(PDF_IMAGE) python3 scripts/check_tools.py pdf
	docker run --rm $(FRONTEND_IMAGE) node --version
	docker run --rm $(FRONTEND_IMAGE) npm --version

docker-toolchain: docker-build docker-check

docker-site:
	$(PYTHON) -c "import pathlib; [pathlib.Path(p).mkdir(parents=True, exist_ok=True) for p in ('dist','public','generated','.cache')]"
	$(DOCKER_RUN) $(CONTENT_IMAGE) sh -lc "rm -rf /app/dist/* /app/generated/* && mkdir -p /app/dist /app/generated /app/public /app/.cache"
	$(DOCKER_CLI) preflight
	$(DOCKER_RUN) $(CONTENT_IMAGE) python3 -m unittest discover -s tests -v
	$(DOCKER_CLI) html
	$(DOCKER_PDF) pdf
	$(DOCKER_FRONTEND) npm run typecheck
	$(DOCKER_FRONTEND) npm run build
	$(DOCKER_CLI) prerender
	$(DOCKER_CLI) seo
	$(DOCKER_CLI) verify
	$(DOCKER_RUN) $(CONTENT_IMAGE) chown -R "$(HOST_UID):$(HOST_GID)" /app/public /app/dist /app/generated /app/.cache

docker-build-site: docker-toolchain
	$(MAKE) docker-site

docker-preview:
	docker run --rm -p 8080:80 \
		-v "$(CURDIR)/dist:/usr/share/nginx/html:ro" \
		-v "$(CURDIR)/deploy/nginx/preview.conf:/etc/nginx/conf.d/default.conf:ro" \
		nginx:alpine

docker-shell:
	docker build -f docker/content/Dockerfile -t $(CONTENT_IMAGE) .
	$(PYTHON) -c "import pathlib; [pathlib.Path(p).mkdir(parents=True, exist_ok=True) for p in ('dist','public','generated','.cache')]"
	docker run --rm -it $(DOCKER_ENV) $(DOCKER_VOLUMES) $(CONTENT_IMAGE) sh
