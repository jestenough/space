import { access, readdir, readFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(process.cwd());
const strictPdf = process.env.STRICT_PDF === "1";
const index = JSON.parse(await readFile(resolve(root, "generated", "articles-index.json"), "utf8"));
const sitemap = await readFile(resolve(root, "generated", "sitemap.xml"), "utf8");
const robots = await readFile(resolve(root, "public", "robots.txt"), "utf8");
const headers = await readTextIfExists(resolve(root, "public", "_headers"));

const errors = [], warnings = [], slugs = new Set(), titles = new Map(), descriptions = new Map();
await validateArticleSourceLayout();
if (!robots.includes("Sitemap:")) errors.push("robots.txt must reference sitemap.xml");
if (!robots.includes("Disallow: /generated/")) errors.push("robots.txt should keep generated fragments out of the index");
if (sitemap.includes("/404") || sitemap.includes("404.html")) errors.push("sitemap.xml must not contain 404 pages");
const fourOhFour = await readTextIfExists(resolve(root, "public", "404.html"), "Missing public/404.html");
if (fourOhFour && !/noindex/i.test(fourOhFour)) errors.push("404.html must include noindex");

for (const article of index) {
  if (slugs.has(article.slug)) errors.push(`Duplicate slug: ${article.slug}`);
  slugs.add(article.slug);
  for (const lang of article.languages ?? []) {
    const title = article.title?.[lang], description = article.description?.[lang];
    const htmlPath = resolve(root, "generated", "articles", `${article.slug}.${lang}.html`);
    const metaPath = resolve(root, "generated", "articles-meta", `${article.slug}.${lang}.json`);
    const pdfPath = resolve(root, "public", lang, "articles", `${article.slug}.pdf`);
    const canonicalPath = `/${lang}/articles/${encodeURIComponent(article.slug)}`;
    const shortLegacyPath = `/${lang}/${encodeURIComponent(article.slug)}`;
    const pdfRoute = `${canonicalPath}.pdf`;
    const html = await readTextIfExists(htmlPath, `Missing generated HTML: ${htmlPath}`);
    const metaText = await readTextIfExists(metaPath, `Missing generated article metadata: ${metaPath}`);

    if (!article.slug?.trim()) errors.push(`Missing slug: ${article.slug}.${lang}`);
    if (!title?.trim()) errors.push(`Missing title: ${article.slug}.${lang}`);
    if (!description?.trim()) errors.push(`Missing description: ${article.slug}.${lang}`);
    if (title) pushUnique(titles, title, `${article.slug}.${lang}`, "Duplicate title");
    if (description) pushUnique(descriptions, description, `${article.slug}.${lang}`, "Duplicate description");
    if (html && !/<h1\b/i.test(html)) errors.push(`Generated article has no h1: ${article.slug}.${lang}`);
    if (metaText) validateArticleMeta(metaText, article, lang, metaPath);
    if (!sitemap.includes(canonicalPath)) errors.push(`Sitemap is missing canonical route: ${canonicalPath}`);
    if (sitemap.includes(shortLegacyPath)) errors.push(`Sitemap contains legacy short article route: ${shortLegacyPath}`);
    if (sitemap.includes(pdfRoute)) errors.push(`Sitemap must not include duplicate PDF route: ${pdfRoute}`);
    if (!headers.includes(pdfRoute)) errors.push(`PDF canonical headers missing for ${pdfRoute}`);
    try {
      await access(pdfPath);
    } catch {
      const message = `Missing PDF for always-visible PDF action: ${pdfPath}`;
      if (strictPdf) errors.push(message); else warnings.push(message);
    }
  }
}

if (!sitemap.includes("xmlns:xhtml=")) errors.push("Sitemap must declare xhtml hreflang namespace");
if (sitemap.includes("#/")) errors.push("Sitemap must not contain hash routes");
if (sitemap.includes("404")) errors.push("Sitemap must not contain 404 routes");
if (/\/generated\//.test(sitemap)) errors.push("Sitemap must not contain generated fragment routes");

for (const warning of warnings) console.warn(`WARN ${warning}`);
if (errors.length) {
  for (const error of errors) console.error(`ERROR ${error}`);
  process.exit(1);
}
console.log(`seo_smoke_ok: ${index.length} articles checked${warnings.length ? `, ${warnings.length} PDF warnings` : ""}`);

async function validateArticleSourceLayout() {
  const legacyIndexPath = resolve(root, "content", "articles-index.json");
  try { await access(legacyIndexPath); errors.push("content/articles-index.json must not be used"); } catch { /* legacy index is absent as expected. */ }
  const articlesDir = resolve(root, "content", "articles");
  const entries = await readdir(articlesDir, { withFileTypes: true });
  if (entries.some((entry) => entry.isFile() && entry.name.endsWith(".tex"))) errors.push("Article .tex files must live in content/articles/<slug>/ folders");
  if (entries.some((entry) => entry.isFile() && entry.name === "articles-index.json")) errors.push("content/articles/articles-index.json must not be used");
  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const slug = entry.name;
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) errors.push(`Invalid article folder slug: ${slug}`);
    const articleDir = resolve(articlesDir, slug);
    const articleEntries = await readdir(articleDir, { withFileTypes: true });
    const metaName = `${slug}.meta.json`;
    if (!articleEntries.some((item) => item.isFile() && item.name === metaName)) errors.push(`Missing article meta: content/articles/${slug}/${metaName}`);
    const texFiles = articleEntries.filter((item) => item.isFile() && item.name.endsWith(".tex"));
    if (texFiles.length === 0) errors.push(`Missing article tex source: content/articles/${slug}/`);
    for (const item of texFiles) {
      if (!new RegExp(`^${escapeRegExp(slug)}\\.[a-z]{2,3}(?:-[A-Za-z]{2})?\\.tex$`).test(item.name)) errors.push(`Invalid article tex filename: content/articles/${slug}/${item.name}`);
    }
  }
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

async function readTextIfExists(path, message) {
  try { return await readFile(path, "utf8"); }
  catch { if (message) errors.push(message); return ""; }
}

function validateArticleMeta(metaText, article, lang, path) {
  let meta;
  try { meta = JSON.parse(metaText); } catch { errors.push(`Invalid JSON metadata: ${path}`); return; }
  if (meta.slug !== article.slug) errors.push(`Metadata slug mismatch: ${path}`);
  if (meta.lang && meta.lang !== lang) errors.push(`Metadata lang mismatch: ${path}`);
  if (typeof meta.canonicalPath !== "string" || !meta.canonicalPath.endsWith(`/articles/${encodeURIComponent(article.slug)}`)) errors.push(`Invalid canonicalPath in ${path}`);
  if (typeof meta.pdfPath !== "string" || !meta.pdfPath.endsWith(`/${encodeURIComponent(article.slug)}.pdf`)) errors.push(`Invalid pdfPath in ${path}`);
  if (/<(p|h1|article|section)\b/i.test(metaText)) errors.push(`Article metadata must not contain HTML content: ${path}`);
}

function pushUnique(map, value, location, message) {
  const key = value.trim().toLowerCase();
  const previous = map.get(key);
  if (previous) errors.push(`${message}: ${value} (${previous}, ${location})`);
  else map.set(key, location);
}
