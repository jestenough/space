SHELL := /bin/bash
IMAGE ?= autophany-toolchain
HOST_UID := $(shell id -u)
HOST_GID := $(shell id -g)

.PHONY: help install dev dev-host preview typecheck preflight html pdf frontend prerender seo verify build clean docker-build docker-build-site docker-shell

help:
	@echo "autophany.space build commands"
	@echo "  make install           install npm dependencies"
	@echo "  make dev               prepare content and start Vite dev server"
	@echo "  make dev-host          prepare content and start Vite on 0.0.0.0:4173"
	@echo "  make preview           preview production build"
	@echo "  make typecheck         run TypeScript checks"
	@echo "  make preflight         validate source content and required tools"
	@echo "  make html              generate HTML fragments and article metadata"
	@echo "  make pdf               generate PDF files"
	@echo "  make frontend          build Vite frontend"
	@echo "  make prerender         prerender static HTML routes"
	@echo "  make seo               generate sitemap, robots, headers, feeds and 404"
	@echo "  make verify            verify generated production output"
	@echo "  make build             run full production pipeline"
	@echo "  make clean             remove generated output and caches"
	@echo "  make docker-build      build Docker toolchain image"
	@echo "  make docker-build-site run full build inside Docker"

install:
	npm ci

dev: html
	npm run dev

dev-host: html
	npm run dev -- --host 0.0.0.0 --port 4173

preview:
	npm run preview

typecheck:
	npm run typecheck

preflight:
	python3 -m scripts.cli preflight

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

build: clean preflight html pdf typecheck frontend prerender seo verify

clean:
	python3 -m scripts.cli clean

docker-build:
	docker build -t $(IMAGE) .

docker-build-site: docker-build
	rm -rf dist generated
	mkdir -p dist public generated .cache
	docker run --rm \
		-e SITE_URL="$${SITE_URL:-https://autophany.space}" \
		-e STRICT_PDF=1 \
		-e HOST_UID="$(HOST_UID)" \
		-e HOST_GID="$(HOST_GID)" \
		-v "$$PWD/public:/app/public" \
		-v "$$PWD/dist:/app/dist" \
		-v "$$PWD/generated:/app/generated" \
		-v "$$PWD/.cache:/app/.cache" \
		$(IMAGE) \
		sh -lc 'make build && chown -R "$$HOST_UID:$$HOST_GID" /app/public /app/dist /app/generated /app/.cache'

docker-shell: docker-build
	mkdir -p dist public generated .cache
	docker run --rm -it \
		-e SITE_URL="$${SITE_URL:-https://autophany.space}" \
		-v "$$PWD/public:/app/public" \
		-v "$$PWD/dist:/app/dist" \
		-v "$$PWD/generated:/app/generated" \
		-v "$$PWD/.cache:/app/.cache" \
		$(IMAGE) \
		bash
