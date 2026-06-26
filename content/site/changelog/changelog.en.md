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
