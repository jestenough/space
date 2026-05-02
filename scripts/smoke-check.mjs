import { access, readFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(process.cwd());
const strictPdf = process.env.STRICT_PDF === "1";
const index = JSON.parse(await readFile(resolve(root, "generated", "articles-index.json"), "utf8"));
const sitemap = await readFile(resolve(root, "generated", "sitemap.xml"), "utf8");
const robots = await readFile(resolve(root, "public", "robots.txt"), "utf8");
const headers = await readTextIfExists(resolve(root, "public", "_headers"));
const vercel = await readTextIfExists(resolve(root, "vercel.json"));

const errors = [], warnings = [], slugs = new Set(), titles = new Map(), descriptions = new Map();
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
    const pdfPath = resolve(root, "public", lang, "articles", `${article.slug}.pdf`);
    const canonicalPath = `/${lang}/articles/${encodeURIComponent(article.slug)}`;
    const shortLegacyPath = `/${lang}/${encodeURIComponent(article.slug)}`;
    const pdfRoute = `${canonicalPath}.pdf`;
    const html = await readTextIfExists(htmlPath, `Missing generated HTML: ${htmlPath}`);

    if (!article.slug?.trim()) errors.push(`Missing slug: ${article.slug}.${lang}`);
    if (!title?.trim()) errors.push(`Missing title: ${article.slug}.${lang}`);
    if (!description?.trim()) errors.push(`Missing description: ${article.slug}.${lang}`);
    if (title) pushUnique(titles, title, `${article.slug}.${lang}`, "Duplicate title");
    if (description) pushUnique(descriptions, description, `${article.slug}.${lang}`, "Duplicate description");
    if (html && !/<h1\b/i.test(html)) errors.push(`Generated article has no h1: ${article.slug}.${lang}`);
    if (!sitemap.includes(canonicalPath)) errors.push(`Sitemap is missing canonical route: ${canonicalPath}`);
    if (sitemap.includes(shortLegacyPath)) errors.push(`Sitemap contains legacy short article route: ${shortLegacyPath}`);
    if (sitemap.includes(pdfRoute)) errors.push(`Sitemap must not include duplicate PDF route: ${pdfRoute}`);
    if (!headers.includes(pdfRoute) && !vercel.includes(pdfRoute)) errors.push(`PDF canonical headers missing for ${pdfRoute}`);
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

async function readTextIfExists(path, message) {
  try { return await readFile(path, "utf8"); }
  catch { if (message) errors.push(message); return ""; }
}
function pushUnique(map, value, location, message) {
  const key = value.trim().toLowerCase();
  const previous = map.get(key);
  if (previous) errors.push(`${message}: ${value} (${previous}, ${location})`);
  else map.set(key, location);
}
