## v2.1.0

Date: **2026.11.08**
- Added default Open Graph and Twitter preview images, including a generated site card
- Added WebSite, Person, and BlogPosting JSON-LD
- Added localized RSS feeds and linked them from page heads and the footer
- Kept image entries inside sitemap `<url>` records and added sitemap image validation
- Excluded empty sections and thin tag pages from the sitemap and marked them noindex
- Removed the always-present client error block and its unused styles
- Added rel next/prev updates to client-side pagination
- Added an SVG favicon
- Hardened 404 output checks

## v2.0.0

Date: **2026.11.06**
- Rebuilt the HTML layer on Jinja2 with autoescaping and full-page templates
- Removed regex-based shell patching and the custom HTML patch layer
- Stopped publishing `generated/` and `_headers`; nginx is now the only header and cache policy source
- Added content-addressed HTML, media, and rendered-page caches with bounded pruning
- Switched precompressed assets to gzip with `gzip_static`
- Added Docker image layer caching in the deploy workflow
- Preloaded critical font subsets and added reduced-motion-aware transitions
- Consolidated pre-paint theme/panel boot logic; removed page-load layout animations and font-swap jitter
- Compacted the System Note layout
- Redirected `/` to `/en` and removed extra directory `301` redirects
- Added CSP, HSTS, and nginx config validation
- Added unit tests for routes, templates, caching, and nginx invariants
- Fixed localized raw downloads for every available language
- Articles now require an explicit `date`

## v1.5.0

Date: **2026.08.21**
- Added the pcd project with localized descriptions
- Made shell commands update automatically with search, sorting, page size, and pagination across all filtered lists
- Standardized project display names across cards and project pages
- Fixed pagination for project grid cards
- Fixed the image viewer briefly showing the previously opened image

## v1.4.0

Date: **2026.07.22**
- Added numbered interactive citations with explicit `\citetext{key}[location]{text}` ranges, hover highlighting, source navigation, link opening, and one-click reference copying
- Added strict per-language bibliographies through `references.<lang>.bib`, localized reference formatting, and preflight validation for missing files, malformed commands, and unknown citation keys
- Added article author and co-author metadata with optional links, visible bylines, JSON-LD authors, and BibTeX export support
- Brought PDF output to parity with HTML: localized authors, citations, bibliography, stable citation order, improved compiler diagnostics, and content-fingerprint caching
- Added local JetBrains Mono Latin/Cyrillic webfonts for the terminal UI while keeping Inter for readable article content
- Refactored the frontend into focused actions, citations, clipboard, and panels modules; replaced the stateful PageController with an explicit `initPage()` composition
- Fixed mobile/desktop panel relocation across viewport changes and reduced unnecessary listeners, DOM work, paint effects, and repeated build-time HTML scans
- Improved responsive image variants, explicit image sizing, media/font cache headers, Docker source mounts, and repeatable prerender/PDF builds

## v1.3.0

Date: **2026.06.28**
- Added a dedicated notes section renderer for short thoughts, snippets, and gist-like entries
- Added language labels and one-click copy for whole code blocks and individual hovered/focused code lines
- Added build-time syntax highlighting styles for Pandoc-generated code tokens

## v1.2.6

Date: **2026.06.26**
- Reduced mobile CLS by prerendering overlay visibility, TOC control visibility, and initial list pagination state
- Smoothed heading/TOC switching by avoiding duplicate scroll handling and animating the active indicator

## v1.2.5

Date: **2026.06.26**
- Added local Inter webfont assets and switched readable file content to Inter
- Added a public licenses page for source, content, and local font licenses
- Added a public privacy notice covering cookies, analytics, tracking, profiling, and interface-only localStorage
- Switched file listing/stat ownership from `root` to `guest`
- Refined the desktop logo font for steadier rendering
- Stabilized the sticky header during content scrolling
- Adjusted the desktop ASCII logo font spacing and weight
- Changed the desktop header from sticky to fixed to prevent scroll jitter
- Increased desktop content offset below the fixed header

## v1.2.4

Date: **2026.06.25**
- Fixed `label`/`title` usage so section lists consistently display `label`
- Moved Dockerfiles into per-service Docker directories

## v1.2.3

Date: **2026.06.24**
- Converted changelog sources to Markdown
- Added article-style heading navigation for Markdown files
- Removed `articles` and `downloads` rows from section stats

## v1.2.2

Date: **2026.06.24**
- Renamed the personal section from `about/` to `profile/`
- Updated profile navigation text, section metadata, and route validation examples
- Added `BIO.md`, `CONTACTS`, public GPG key


## v1.2.1

Date: **2026.06.24**
- Added scripts.cli create for creating content sections and items;
- Delete deprecated ContentFormat enum


## v1.2

Date: **2026.06.23**
- Refined the desktop terminal workstation layout; 
- Switched the navigation command to `tree -d -L 1 .`; 
- Localized window titles and the `!ls` back tooltip; 
- Preserved desktop panel state in localStorage only on desktop; 
- Redesigned the mobile experience around the reader-first content flow, compact file actions, and overlay panels; 
- Improved mobile overlay spacing; 
- Enabled zen mode for readable files only; 
- Added Escape and empty-area exit behavior for zen mode; 
- Made the zen exit control square and more visible; 
- Kept raw/non-readable files from showing zen actions;


## v1

Date: **2026.06.05**
- Init v1 of site.
