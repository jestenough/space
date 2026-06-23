SHELL := /bin/bash
FRONTEND_IMAGE ?= frontend
CONTENT_IMAGE ?= content
PDF_IMAGE ?= pdf
HOST_UID := $(shell id -u)
HOST_GID := $(shell id -g)

DOCKER_ENV = -e SITE_URL="$${SITE_URL:-https://autophany.space}" -e STRICT_PDF=1
DOCKER_VOLUMES = -v "$$PWD/public:/app/public" -v "$$PWD/dist:/app/dist" -v "$$PWD/generated:/app/generated" -v "$$PWD/.cache:/app/.cache"
DOCKER_RUN = docker run --rm $(DOCKER_ENV) $(DOCKER_VOLUMES)

.PHONY: help install dev dev-host preview typecheck preflight toolchain create html pdf frontend prerender seo verify build clean docker-build docker-toolchain docker-build-site docker-shell

help:
	@echo "autophany.space build commands"
	@echo "  make install           install npm dependencies"
	@echo "  make dev               build prerendered pages and preview locally"
	@echo "  make dev-host          build prerendered pages and preview on 0.0.0.0:4173"
	@echo "  make preview           preview current production build"
	@echo "  make typecheck         run TypeScript checks"
	@echo "  make preflight         validate source content"
	@echo "  make toolchain         validate required external tools"
	@echo "  make create            create content sections and items"
	@echo "  make html              generate content HTML fragments and metadata"
	@echo "  make pdf               generate PDF files"
	@echo "  make frontend          build Vite frontend"
	@echo "  make prerender         prerender static HTML routes"
	@echo "  make seo               generate sitemap, robots, headers, feeds and 404"
	@echo "  make verify            verify generated production output"
	@echo "  make build             run full production pipeline"
	@echo "  make clean             remove generated output and caches"
	@echo "  make docker-build      build frontend/content/pdf images"
	@echo "  make docker-toolchain  validate Docker image tools"
	@echo "  make docker-build-site run full build in Docker containers"
	@echo "  make docker-shell      open a container shell"

install:
	npm ci

dev: html frontend prerender
	npm run preview

dev-host: html frontend prerender
	npm run preview -- --host 0.0.0.0 --port 4173

preview:
	npm run preview

typecheck:
	npm run typecheck

preflight:
	python3 -m scripts.cli preflight

toolchain:
	@for binary in node npm pandoc latexmk xelatex; do \
		command -v "$$binary" >/dev/null || { echo "Missing required build tool: $$binary"; exit 1; }; \
	done

create:
	python3 -m scripts.cli create $(ARGS)

html:
	python3 -m scripts.cli html

pdf:
	python3 -m scripts.cli pdf

frontend:
	npm run build

prerender:
	python3 -m scripts.cli prerender

seo:
	python3 -m scripts.cli seo

verify:
	python3 -m scripts.cli verify

build: preflight toolchain html pdf typecheck frontend prerender seo verify

clean:
	python3 -m scripts.cli clean

docker-build:
	docker build -f docker/frontend.Dockerfile -t $(FRONTEND_IMAGE) .
	docker build -f docker/content.Dockerfile -t $(CONTENT_IMAGE) .
	docker build -f docker/pdf.Dockerfile -t $(PDF_IMAGE) .

docker-toolchain: docker-build
	docker run --rm $(CONTENT_IMAGE) sh -lc 'for binary in python3 pandoc; do command -v "$$binary" >/dev/null || { echo "content image missing: $$binary"; exit 1; }; done'
	docker run --rm $(PDF_IMAGE) sh -lc 'for binary in python3 latexmk xelatex; do command -v "$$binary" >/dev/null || { echo "pdf image missing: $$binary"; exit 1; }; done'
	docker run --rm $(FRONTEND_IMAGE) sh -lc 'for binary in node npm; do command -v "$$binary" >/dev/null || { echo "frontend image missing: $$binary"; exit 1; }; done'

docker-build-site: docker-toolchain
	mkdir -p dist public generated .cache
	$(DOCKER_RUN) $(CONTENT_IMAGE) sh -lc 'rm -rf /app/dist/* /app/generated/* && mkdir -p /app/dist /app/generated /app/public /app/.cache'
	$(DOCKER_RUN) $(CONTENT_IMAGE) python3 -m scripts.cli preflight
	$(DOCKER_RUN) $(CONTENT_IMAGE) python3 -m scripts.cli html
	$(DOCKER_RUN) $(PDF_IMAGE) python3 -m scripts.cli pdf
	$(DOCKER_RUN) $(FRONTEND_IMAGE) npm run typecheck
	$(DOCKER_RUN) $(FRONTEND_IMAGE) npm run build
	$(DOCKER_RUN) $(CONTENT_IMAGE) python3 -m scripts.cli prerender
	$(DOCKER_RUN) $(CONTENT_IMAGE) python3 -m scripts.cli seo
	$(DOCKER_RUN) $(CONTENT_IMAGE) python3 -m scripts.cli verify
	$(DOCKER_RUN) $(CONTENT_IMAGE) chown -R "$(HOST_UID):$(HOST_GID)" /app/public /app/dist /app/generated /app/.cache

docker-shell:
	docker build -f docker/content.Dockerfile -t $(CONTENT_IMAGE) .
	mkdir -p dist public generated .cache
	docker run --rm -it $(DOCKER_ENV) $(DOCKER_VOLUMES) $(CONTENT_IMAGE) sh
