SHELL := /bin/bash
IMAGE ?= autophany-space

.PHONY: help install clean prepare-content prepare-pdf prepare typecheck check-content build preview lighthouse docker-build docker-prepare docker-build-site docker-shell

help:
	@echo "autophany.space build commands"
	@echo "  make install          npm ci"
	@echo "  make prepare-content  LaTeX fragments -> generated HTML/index/sitemap"
	@echo "  make prepare-pdf      LaTeX fragments -> public/<lang>/articles/<slug>.pdf"
	@echo "  make prepare          prepare content, generate PDFs, run content checks"
	@echo "  make typecheck        TypeScript check"
	@echo "  make build            full production build"
	@echo "  make clean            remove generated output"
	@echo "  make docker-build     build Docker image"
	@echo "  make docker-build-site run full build inside Docker"

install:
	npm ci

clean:
	npm run clean

prepare-content:
	npm run prepare:content

prepare-pdf:
	npm run prepare:pdf

prepare: prepare-content prepare-pdf check-content

typecheck:
	npm run check:types

check-content:
	npm run check:content

build:
	npm run build

preview:
	npm run preview

lighthouse:
	npm run check:lighthouse

docker-build:
	docker build -t $(IMAGE) .

docker-prepare: docker-build
	@cid=$$(docker create $(IMAGE) make prepare); \
	docker start -a $$cid; \
	rm -rf generated; \
	mkdir -p public; \
	docker cp $$cid:/app/generated ./generated; \
	docker cp $$cid:/app/public/. ./public; \
	docker rm $$cid

docker-build-site: docker-build
	@cid=$$(docker create $(IMAGE) make build); \
	docker start -a $$cid; \
	rm -rf dist; \
	docker cp $$cid:/app/dist ./dist; \
	docker rm $$cid

docker-shell: docker-build
	docker run --rm -it $(IMAGE) bash
