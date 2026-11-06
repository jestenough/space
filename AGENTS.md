# AGENTS.md

## Project Rules

This project uses a section-based content architecture. Do not reintroduce unsupported compatibility paths or fallback logic.

The Python build pipeline is the source of truth. TypeScript is a DOM enhancement layer only.

## Versioning

The site is versioned. After meaningful project changes, update the project version instead of leaving it unchanged.

Current version:

- `2.0.0` in `package.json`.
- `1.0.0` was the first complete version of the site.

Release commits follow the existing pattern, for example `chore(release): v2.0.0`.

## Content Structure

`content/` contains only first-level sections. Current sections are:

- `site`
- `profile`
- `projects`
- `notes`
- `articles`
- `tags`

Forbidden old paths:

- `content/site.json`
- `content/assets`
- `content/templates`
- `content/info`

Each section must have a section meta file:

```text
content/<section>/<section>.meta
```

Each item must live in its own directory:

```text
content/<section>/<slug>/<slug>.meta
content/<section>/<slug>/<slug>.<lang>.<ext>
content/<section>/<slug>/assets/...   # optional item media
```

Meta files are JSON without a `.json` extension. Item meta is always named after the item slug, never after the source extension or source filename:

```text
correct: content/profile/bio/bio.meta      # for bio.en.md
wrong:   content/profile/bio/bio.md.meta
wrong:   content/profile/bio/README.meta
```

The optional `assets/` directory inside an item is copied and optimized into `/media/<section>/<slug>/assets/...`.

## Meta And Languages

Content languages are discovered from section meta and item source files. Not every item has to exist in every language.

Language rules:

- If a language is present in localized meta fields, the source file for that language must exist.
- If a source file exists for a language, localized meta fields must include that language.
- If neither meta nor source exists for a language, that is valid.
- Missing-language requests must resolve to prerendered `404` output. Do not reintroduce client-side missing-language fallback rendering.
- Language codes are normalized as `en`, `ru`, or `pt-BR` (lowercase base, uppercase region).

Required localized fields:

- `label`
- `title`
- `description`

Project `status` values, when localized, participate in the same language-consistency checks as `label`, `title`, and `description`.

Required item meta fields:

- `slug`
- `label`
- `title`
- `description`

Required section meta fields:

- `slug`
- `label`
- `title`
- `description`

Common optional item fields:

- `type` — defaults to `page`
- `format` — accepted in content but not used by the build; the source extension selects the renderer
- `date` — `YYYY-MM-DD`
- `tags` — articles
- `download` — boolean, exposes a raw localized source route
- `author`, `coAuthors` — articles
- `stack`, `status`, `projectUrl`, `sourceUrl` — projects

Additional validation rules:

- `date`, when present, must be a real `YYYY-MM-DD` date.
- `download` must be a JSON boolean; only `"download": true` enables the raw route.
- `tags` must be a non-empty list of unique non-empty strings.
- `author` must be an object with a non-empty `name` and an optional absolute `http(s)`, `mailto:`, or root-relative `url`.
- `coAuthors` must be an array of the same author object shape and may be empty. Author and co-author names must be unique.
- Project `stack` must be a non-empty list of unique non-empty strings.
- Project `status` may be a string or a localized object. Supported values are `launched`, `ready`, `development`, `planned`; aliases such as `active`, `live`, `done`, `in development` are normalized during rendering.
- Project `projectUrl` and `sourceUrl`, when present, must be absolute `http(s)` URLs.

UI and renderer translations are currently provided for `en` and `ru`. Adding a new content language also requires adding entries to the relevant translation tables:

- `scripts/rendering/shell.py` — `DEFAULT_UI`, `UI_BY_LANG`, `LOCALE_REGIONS`
- `scripts/rendering/code.py` — `UI`
- `scripts/rendering/files/article.py` — `BYLINE_UI`
- `scripts/rendering/files/project.py` — `STATUS_LABELS`
- `scripts/rendering/folders/notes.py` — `note_ui_by_lang`
- `scripts/citations.py` — `REFERENCE_UI`

Most missing translations raise explicit build errors. Project status/action labels in `scripts/rendering/files/project.py` intentionally fall back to English defaults.

## Item Types

File types are defined by `FileType` in `scripts/config.py`.

`page`:

- Default type when `type` is omitted.
- May use `.md`, `.txt`, or `.tex` sources.
- Raw source download is optional via `download: true`.

`article`:

- Requires `type: "article"`.
- Requires `.tex` sources only.
- Requires a non-empty `tags` list.
- Requires `author`, `coAuthors`, and `date`; feeds, sitemap entries, and article metadata rely on the date.
- Citations use `\citetext{key}[location]{text}` and a per-language `references.<lang>.bib`. A shared `references.bib` is forbidden.
- Citation keys must exist in the matching localized bibliography.

`project`:

- Requires `type: "project"`.
- Must live in a section with `kind: "projects"`.
- Requires `stack` and normally `status`.
- Uses `projectUrl` and `sourceUrl` for external actions.

## Type System

Folder and file types are defined in Python enums, not in TypeScript string unions.

Canonical definitions live in `scripts/config.py`:

- `FolderType`
- `FileType`
- `ContentExtension`

Current folder types:

- `system`
- `files`
- `articles`
- `notes`
- `projects`
- `tags`

Current file types:

- `page`
- `article`
- `project`

Current content extensions:

- `tex`
- `md`
- `txt`
- `meta`

Section `kind` defaults to `files`. A system section must set both:

```json
"kind": "system",
"system": true
```

There must be exactly one system section, and its slug must be `site` (or the `SYSTEM_SECTION` environment override).

If a new folder type or file type is added:

1. add the enum value in `scripts/config.py`
2. add a renderer under `scripts/rendering/folders/` or `scripts/rendering/files/`
3. register the renderer in `scripts/rendering/registry.py`
4. add the matching template file under `templates/folders/<folder-type>.html` or `templates/files/<file-type>.html`
5. implement the renderer hooks that actually differ (`command`, `stage_html`, `process`, `extra_pages`, `index_meta`, `localized_meta`, `render_source`, `render_page`, `validate_item`)
6. add preflight validation if the new type has required metadata

Do not move these type definitions back into TypeScript.

## Routing

Language is always present in localized content URLs.

The root path `/` is special:

- `vite preview` and nginx redirect `/` with `302` to the default language URL (`/en`).
- Prerender writes `dist/index.html` as a noindex redirect fallback, not as a second home page.
- Do not introduce unlocalized content routes.

The `site` section is system-level and is not included in URLs:

```text
content/site/readme/readme.en.md -> /en/readme
```

The `site` section is hidden from user navigation. It provides the default root page at `/<lang>` and root-level files at `/<lang>/<slug>`, but visible navigation contains only non-system sections. When `site` is open, no navigation item is active.

Other sections include their section slug:

```text
content/profile/gpg/gpg.en.asc -> /en/profile/gpg
content/projects/autophany/autophany.en.txt -> /en/projects/autophany
```

Additional route patterns:

```text
section:   /<lang>/<section>
item:      /<lang>/<section>/<slug>
system:    /<lang>/<slug>
tag page:  /<lang>/<section>/<tag>
article PDF: /<lang>/<section>/<slug>.pdf
```

Raw/download files are available only by the full localized path with extension:

```text
/en/profile/gpg.asc
/ru/profile/gpg.asc
```

Raw/download routes are generated only when the item meta explicitly contains:

```json
"download": true
```

Without `"download": true`, generated `downloadPath` must be `null` and the raw source route must not be served.

Do not serve old non-localized download paths like `/profile/gpg.asc`.

Route construction belongs in `scripts/routes.py`. Do not hand-build localized URLs in renderers or TypeScript.

## Generated Structure

Only the section-based generated structure is valid:

```text
generated/sections-index.json
generated/sections/<section>.json
generated/files/<section>/<slug>.<lang>.html
generated/files-meta/<section>/<slug>.<lang>.json
generated/site-meta.json
```

`generated/sections/<section>.json` is an array of localized item index objects. `generated/site-meta.json` contains the `home`, `tag`, and `notFound` page metadata.

Localized file metadata is build-time data and may include fields such as:

- `section`, `slug`, `lang`, `type`, `fileType`
- `label`, `title`, `description`
- `canonicalPath`, `downloadPath`, `downloadPaths`, `pdfPath`
- `sourcePath`, `wordCount`, `charCount`, `byteSize`, `readingTime`

Forbidden generated paths:

```text
generated/articles-index.json
generated/articles/
generated/articles-meta/
generated/<section>-index.json
```

Do not add compatibility code for these paths.

Generated data is build-time only. Do not publish `generated/` into `dist/` or copy `generated/files-meta/` into `dist/`.

## Templates

The project is template-driven at build time.

Template locations:

```text
templates/base.html
templates/head.html
templates/folders/<folder-type>.html
templates/files/<file-type>.html
templates/parts/*.html
templates/system/404.html
```

Current templates:

```text
templates/base.html
templates/head.html
templates/system/404.html
templates/system/root.html
templates/folders/system.html
templates/folders/files.html
templates/folders/articles.html
templates/folders/notes.html
templates/folders/projects.html
templates/folders/tags.html
templates/files/page.html
templates/files/article.html
templates/files/project.html
templates/parts/*.html
```

`index.html` is only the Vite entry point. Production pages are rendered from `templates/base.html`.

`scripts/templating.py` provides Jinja2 with HTML autoescape. Templates must escape data by default; use `|safe` only for HTML produced by a renderer or another template.

Template selection happens in the rendering layer, not in TypeScript:

- folder templates are selected by `FolderRenderer.folder_type` in `scripts/rendering/folders/`
- file templates are selected by `FileShellContext.file_type` in `scripts/rendering/shell.py`

Rules:

- Template files already contain the markup structure.
- Renderers prepare and inject data; they should not duplicate whole page markup in Python string builders.
- Do not reintroduce TypeScript-side content templates.
- Keep template naming aligned with enum values.

## Rendering Architecture

Prerender orchestration lives in `scripts/prerender.py`:

- load generated sections, items, localized metadata, and Vite assets from `dist/.vite/manifest.json`
- create `RouteRender` objects for the root, localized homes, sections, tag pages, and file pages
- render `templates/base.html` and write final pages to `dist/<lang>/.../index.html`

The rendering layer lives in `scripts/rendering/`:

- `registry.py` maps `FolderType` and `FileType` to renderer instances
- `context.py` defines shared render contexts and view models (`RouteRender`, `Stat`, `TocItem`, and the `*Context` dataclasses); shell data is assembled by `shell.py`
- `services.py` is the facade used by renderers
- `shell.py`, `head.py`, `meta.py`, `media.py`, `html_tags.py` handle page context, head data, metadata, media, and attribute patching
- `pages.py` caches fully rendered pages
- `folders/` contains folder renderers (`system`, `files`, `articles`, `notes`, `projects`, `tags`)
- `files/` contains file renderers (`page`, `article`, `project`)

Add new behavior in the relevant renderer instead of branching inside `prerender.py`.

## Static Assets

Favicon and manifest source assets live under `public/icons/`. Font assets live under `public/fonts/`.

Rules:

- Keep favicon-related files grouped in `public/icons/`; do not spread them back into the `public/` root.
- Visible favicon and manifest references should use `/icons/...` paths.
- Do not reintroduce the removed heavyweight SVG favicon unless there is a concrete reason and it is properly optimized.
- `public/**/*.pdf` is generated by the `pdf` step and gitignored. Do not commit generated PDFs.
- `public/boot.js` is the shared pre-paint theme/panel boot script; keep it dependency-free and load it synchronously from the document head.
- Item images under `content/<section>/<slug>/assets/` are converted to WebP with responsive variants by `vite.config.ts` into `dist/media/`; the manifest is written to `.cache/media-manifest.json` and consumed by `scripts/rendering/media.py`.
- Do not keep source copies of `public/robots.txt` or `public/404.html`; these are generated into `dist/` by the `seo` step. Header and cache policy live only in the nginx config.

## Articles

Articles are normal section items with `type: "article"`. Do not hard-code articles as a separate content backend.

Article UI behavior:

- Article actions are `pdf`, `cite`, `edit`, and `zen`.
- `pdf`, `cite`, and `edit` are available only for `type: "article"`.
- `zen` is available for any readable source (`.txt`, `.md`, `.tex`), including non-article pages and projects.
- Non-article `.tex` files render through the TeX pipeline but do not show article-only actions.
- Non-article raw files with `downloadPath` show the `download` action.

Article build behavior:

- sources are rendered through Pandoc to HTML fragments
- article metadata includes byline, tags, previous/next links, PDF path, and JSON-LD
- feeds and sitemap entries are generated from article metadata
- citations and reference lists are generated from localized `references.<lang>.bib` files

## Scripts

Python dependencies are pinned in `requirements.txt`; the content Docker image installs them before running the pipeline. Unit tests live in `tests/` and run with `make test`.

Use the focused modules directly:

- `scripts/cli.py` for command registration and dispatch.
- `scripts/config.py` for paths, enums, and stable build constants.
- `scripts/content.py` for section/item/source scanning.
- `scripts/html.py` for generated HTML fragments, localized metadata, and section indexes.
- `scripts/pdf.py` for article PDF generation and PDF cache fingerprints.
- `scripts/prerender.py` for final page assembly into `dist/` using the rendering layer.
- `scripts/seo.py` for sitemap, robots, feeds, and `404.html`.
- `scripts/verify.py` for post-build output verification.
- `scripts/preflight.py` for source validation.
- `scripts/create.py` for interactive content creation.
- `scripts/dev.mjs` for the local build/prerender/preview shortcut.
- `scripts/check_tools.py` for host and Docker toolchain checks.
- `scripts/cache.py` for bounded cache pruning.
- `scripts/clean.py` for removing generated output and caches.
- `scripts/citations.py` for TeX citation preprocessing, bibliography parsing, and reference HTML.
- `scripts/routes.py` for public/generated route construction.
- `scripts/generated.py` for generated index readers.
- `scripts/jsonio.py` for JSON file IO.
- `scripts/localization.py` for language and localized-text helpers.
- `scripts/templating.py` for the autoescaped Jinja2 template environment.
- `scripts/rendering/` for the prerender rendering layer described above.
- `scripts/rendering/code.py` for code-copy decoration.
- `scripts/rendering/html_tags.py` for tag attribute helpers.
- `scripts/rendering/pages.py` for the rendered-page cache.
- `scripts/rendering/registry.py` is the only place enum values map to renderers.

Scripts must operate on all sections, not only `articles`.

Validation order in `preflight`:

1. route/type invariants
2. project structure
3. content sections and meta/source consistency

External build tools are checked separately:

- `make toolchain` checks `node`, `npm`, `pandoc`, `latexmk`, and `xelatex`.
- `html` requires `pandoc`.
- `pdf` requires `latexmk` and `xelatex`; it skips with a warning unless `STRICT_PDF=1`.
- `verify` warns about missing PDFs unless `STRICT_PDF=1`.

Build errors should be explicit and actionable. Include file path, field name, language, and expected fix where possible.

`verify` also checks the root redirect, `boot.js`, `404.css`, localized download files, media links in every generated fragment, and simple raw asset budgets: 100 KB JavaScript, 200 KB CSS, and 20 KB boot script.

## CLI And Build Pipeline

CLI commands:

```text
python3 -m scripts.cli preflight
python3 -m scripts.cli html
python3 -m scripts.cli pdf
python3 -m scripts.cli prerender
python3 -m scripts.cli seo
python3 -m scripts.cli verify
python3 -m scripts.cli clean
python3 -m scripts.cli create
```

Full production pipeline:

```text
make build
```

which runs:

```text
preflight -> toolchain -> html -> pdf -> typecheck -> frontend -> prerender -> seo -> verify
```

Useful targets:

- `make dev` — `html`, `frontend`, `prerender`, then `npm run preview`
- `make frontend` — `npm run build`
- `make clean` — remove generated output, caches, and generated public PDFs
- `make docker-build-site` — build images, check them, and run the full pipeline
- `make docker-site` — run the full pipeline with already built images
- `make docker-check` — check already built image toolchains
- `make docker-preview` — serve `dist/` with nginx on `:8080`

Build caches:

- `.cache/html/` stores content-addressed Pandoc/render outputs; `FORCE_HTML=1` bypasses it.
- `.cache/media/` stores content-addressed optimized media; `clean` removes all caches.
- `.cache/pages/` stores rendered pages; `FORCE_PAGES=1` bypasses it. Its key includes `SITE_URL`.
- `.cache/pdf/` stores PDF fingerprints.
- Cache entries are pruned to a bounded number of entries; `clean` removes all caches.

PDF environment:

- `FORCE_PDF=1` rebuilds PDFs even when fingerprints are fresh.
- `STRICT_PDF=1` turns missing PDF/tool warnings into errors.

## Frontend

TypeScript is a DOM enhancement layer only. The initial visible UI must already be present in prerendered HTML inside `dist/<lang>/.../index.html`.

Entry point:

- `src/main.ts` -> `src/app/initPage.ts`

Allowed frontend responsibilities:

- pre-paint theme and panel state application so stored hidden state is never flashed
- language switch navigation
- theme switching and system theme tracking
- desktop panel state and mobile panel/overlay behavior
- zen mode
- heading anchors, TOC highlighting, and hash scrolling
- copy behavior inside rendered content (code blocks, line copy, citations, references)
- citation hover/click highlighting and reference scrolling
- zoomable image viewer
- opening already generated action links such as `pdf`, `edit`, and `download`
- client-side list filtering, sorting, and pagination over prerendered DOM, including URL query sync
- keyboard shortcuts such as `/` to focus search and `Escape` to close overlays/zen mode

Forbidden frontend responsibilities:

- content-type definitions
- folder-type definitions
- content HTML rendering
- template selection
- article/info/tag page assembly
- build-time stats computation
- generated JSON driven page rendering

Frontend selectors and behavior must stay generic and data-attribute based:

List behavior:

```text
data-list-root
data-list-items
data-list-item
data-list-search
data-list-sort
data-list-size
data-list-prev
data-list-next
data-list-page-info
data-list-pager
data-list-command-base
data-list-command
```

Per-item data:

```text
data-search
data-sort-title
data-sort-date
data-sort-name
data-sort-count
```

Process/status fields:

```text
data-process-field
```

File actions and content:

```text
data-action-href
data-action-target
data-file-content
```

Copy behavior:

```text
data-copy-text
data-copy-value
data-reference-copy
```

Navigation, citations, and media:

```text
data-heading-id
data-ref
data-zoomable-image
data-full-image
```

Panels and overlays:

```text
data-panel-key
data-mobile-overlay-open
data-mobile-overlay-close
data-mobile-overlay
```

Zen mode:

```text
data-zen-toggle
data-zen-exit
```

Do not reintroduce article-specific TS controllers or section-specific rendering branches.

## Shell UI

Shell-like UI commands should use the shared `guest@cray-1:<cwd>$` prompt style.

Rules:

- The left top command is fixed: `guest@cray-1:~$ tree -d -L 1 .`.
- Other visible prompts are path-aware: use `~` for the root/system `site` section and `~/section` for non-system sections.
- The left MetaInfo command is `sed -n '1,2p' .meta` for the system section and `sed -n '1,2p' <section>.meta` for other sections.
- Visible command text should be relative to the shown cwd when possible; do not reintroduce absolute `~/section/...` command text for `cat`/`stat` if a relative filename is enough.
- For non-article files, visible `cat`/`stat` commands and displayed file names should use the localized `label` display name rather than the raw slug.
- Article `cat`/`stat` commands use the `.tex` item slug.
- Render the prompt host/path and the `$` sign separately: the host/path may be accented, but `$` must stay muted like a normal shell prompt.
- List commands are composed from `data-list-command-base` plus the active search, sort, and page-size `data-list-command` values in `src/features/lists/listController.ts`.

The center column is a single shell surface with a command header and content body.

Rules:

- Keep the command header and the list/file/error body visually connected as one shell block; do not split them back into separate cards.
- Avoid artificial list-panel min-heights that make the shell background extend well past the rendered items.
- Pagination controls should be hidden whenever the total page count is `0` or `1`, including after client-side filtering/search changes.
- In `zen` mode, keep the reading surface clean: no command header, and no center-shell border/background/shadow.

Panel open/closed state is applied before first paint by `public/boot.js` and the boot calls in `templates/head.html` / `templates/base.html`. Keep the `data-panels="pending"` / `data-panels="ready"` handshake and the matching rules in `src/styles/motion.css`; do not move panel state application back into the deferred module bundle. `themeService` and `panelController` must reuse `window.autophanyBoot` instead of reimplementing the state rules.

Motion and hover transitions live in `src/styles/motion.css`. New interactive surfaces should use the shared duration/easing tokens and respect `prefers-reduced-motion`.

## Deploy

The GitHub deploy workflow must remain section-based.

Current workflow: `.github/workflows/deploy.yml`, using the cached `build-images` composite action and then `make docker-site`.

Rules:

- Do not cache only `content/articles`.
- Do not reference `.meta.json`; content meta files use `.meta`.
- PDF cache paths must stay generic: `public/**/*.pdf` and `.cache/pdf/**/*.sha256`.
- Cache `.cache/html`, `.cache/media`, `.cache/pages`, and `.cache/media-manifest.json` as build caches.
- Do not run a pipeline step that removes `public/**/*.pdf` before `pdf`, because that deletes restored PDFs.
- `vite preview` must serve prerendered localized pages from `dist/`; do not depend on TS route rendering in preview.
- Do not publish `generated/` or `generated/files-meta/` into `dist/`; they are build-time data only.
- The production server config lives in `deploy/nginx/autophany.space.conf` and is the only source of header/cache policy, including HSTS and CSP.
- Keep nginx prefix cache locations (`/assets/`, `/media/`, `/fonts/`) marked with `^~`, otherwise the generic extension regex overrides their cache headers.
- Serve directory requests with `try_files $uri $uri/index.html =404;` so internal links without a trailing slash do not trigger an extra `301`.
- Repeat the security headers in any nginx location that declares its own `add_header`; nginx does not inherit `add_header` into such locations.

## Verification

Run when possible:

```text
npm run typecheck
npm run build
python3 -m unittest discover -s tests -v
make nginx-check
python3 -m scripts.cli preflight
python3 -m scripts.cli html
python3 -m scripts.cli pdf
python3 -m scripts.cli prerender
python3 -m scripts.cli seo
python3 -m scripts.cli verify
```

In this environment, `pandoc`, `latexmk`, and `xelatex` may be missing. If so, TeX HTML/PDF generation and full verify may fail after content validation. Do not treat that as a reason to reintroduce fallbacks or unsupported paths.

## Current Content Examples

Examples present in the repository:

```text
content/site/readme/readme.en.md
content/site/changelog/changelog.en.md
content/profile/bio/bio.en.md
content/profile/gpg/gpg.en.asc
content/projects/autophany/autophany.en.txt
content/articles/hello-world/hello-world.en.tex
content/articles/hello-world/references.en.bib
```

The `notes` section currently has a section meta file but no items.
