import { mkdir, readdir, readFile, rm, writeFile } from "node:fs/promises";
import { resolve, basename } from "node:path";

const root = resolve(process.cwd());
const metadataPath = resolve(root, "content", "articles-index.json");
const sourceDir = resolve(root, "content", "articles");
const generatedDir = resolve(root, "generated");
const outputDir = resolve(generatedDir, "articles");
const feedsDir = resolve(generatedDir, "feeds");
const supportedLangs = ["en", "ru"];
const DEFAULT_SITE_URL = "https://autophany.space";
const DEFAULT_LASTMOD = "2026-05-01";
const XML_HEADER = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>";
const SITEMAP_ROOT = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">';
const sectionLevels = new Map([["part", 1], ["chapter", 1], ["section", 1], ["subsection", 2], ["subsubsection", 3], ["paragraph", 4], ["subparagraph", 5]]);

const main = async () => {
  const rawIndex = await readFile(metadataPath, "utf8");
  const articleIndex = normalizeArticleIndex(JSON.parse(rawIndex));
  const sourceFiles = await readSourceFiles(sourceDir);
  validateSourcesAgainstIndex(sourceFiles, articleIndex);

  await rm(generatedDir, { recursive: true, force: true });
  await mkdir(outputDir, { recursive: true });
  await mkdir(feedsDir, { recursive: true });

  for (const article of articleIndex) {
    for (const lang of article.languages) {
      const sourcePath = resolve(sourceDir, `${article.slug}.${lang}.tex`);
      const targetPath = resolve(outputDir, `${article.slug}.${lang}.html`);
      const source = await readFile(sourcePath, "utf8");
      await writeFile(targetPath, convertLatexToHtml(source), "utf8");
    }
  }

  const siteUrl = normalizeSiteUrl(process.env.SITE_URL || DEFAULT_SITE_URL);
  const tagsByLang = collectTagsByLang(articleIndex);
  await writeFile(resolve(generatedDir, "articles-index.json"), JSON.stringify(articleIndex, null, 2) + "\n", "utf8");
  await writeFile(resolve(generatedDir, "sitemap.xml"), renderSitemap(buildSitemapEntries(articleIndex, tagsByLang), siteUrl), "utf8");
  await writeFile(resolve(root, "public", "robots.txt"), renderRobots(siteUrl), "utf8");
  await writeFile(resolve(root, "public", "404.html"), render404(), "utf8");
  await writeFile(resolve(root, "public", "_headers"), renderHeaders(articleIndex, siteUrl), "utf8");
  await writeFile(resolve(root, "vercel.json"), JSON.stringify(renderVercelConfig(articleIndex, siteUrl), null, 2) + "\n", "utf8");
  for (const lang of supportedLangs) {
    await writeFile(resolve(feedsDir, `${lang}.xml`), renderRssFeed(lang, articleIndex, siteUrl), "utf8");
  }
  console.log(`content_ok: ${articleIndex.length} articles, ${sourceFiles.size} source files, generated/ updated`);
};

const parseArticleFilename = (fileName) => {
  const match = fileName.match(/^(.+)\.([a-z]{2})\.tex$/i);
  if (!match) return null;
  const [, slug, rawLang] = match;
  const lang = rawLang.toLowerCase();
  if (!supportedLangs.includes(lang)) return null;
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) throw new Error(`Invalid article slug in filename: ${fileName}`);
  return { slug, lang, key: `${slug}.${lang}` };
};

const readSourceFiles = async (dir) => {
  const entries = await readdir(dir, { withFileTypes: true });
  const files = new Map();
  for (const entry of entries) {
    if (entry.isDirectory()) throw new Error(`Language subdirectories are not allowed in content/articles/: ${entry.name}`);
    if (!entry.isFile()) continue;
    if (!entry.name.endsWith(".tex")) continue;
    const parsed = parseArticleFilename(entry.name);
    if (!parsed) throw new Error(`Article source filename must be <slug>.<lang>.tex: ${entry.name}`);
    if (files.has(parsed.key)) throw new Error(`Duplicate article source: ${entry.name}`);
    files.set(parsed.key, entry.name);
  }
  return files;
};

const validateSourcesAgainstIndex = (files, articles) => {
  const expected = new Set();
  const seenSlugs = new Set();
  for (const article of articles) {
    if (seenSlugs.has(article.slug)) throw new Error(`Duplicate article slug in metadata: ${article.slug}`);
    seenSlugs.add(article.slug);
    for (const lang of article.languages) {
      const key = `${article.slug}.${lang}`;
      expected.add(key);
      if (!files.has(key)) throw new Error(`Missing source file: content/articles/${key}.tex`);
    }
  }
  for (const key of files.keys()) if (!expected.has(key)) throw new Error(`Source file is not listed in content/articles-index.json: content/articles/${key}.tex`);
};

const escapeHtml = (value) => {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
};

const slugify = (value) => {
  return value.toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "").replace(/[^\p{Letter}\p{Number}]+/gu, "-").replace(/^-+|-+$/g, "") || "section";
};

const inlineLatexToHtml = (value) => {
  return escapeHtml(value)
    .replace(/\\texttt\{([^{}]*)\}/g, "<code>$1</code>")
    .replace(/\\emph\{([^{}]*)\}/g, "<em>$1</em>")
    .replace(/\\textbf\{([^{}]*)\}/g, "<strong>$1</strong>")
    .replace(/\\\\/g, "<br>");
};

const flushParagraph = (buffer, out) => {
  const text = buffer.join(" ").trim();
  buffer.length = 0;
  if (text) out.push(`<p>${inlineLatexToHtml(text)}</p>`);
};

const flushListItem = (buffer, out) => {
  const text = buffer.join(" ").trim();
  buffer.length = 0;
  if (text) out.push(`<li>${inlineLatexToHtml(text)}</li>`);
};

const stripLatexComment = (line) => {
  let escaped = false;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (char === "\\") { escaped = !escaped; continue; }
    if (char === "%" && !escaped) return line.slice(0, index);
    escaped = false;
  }
  return line;
};

const parseSectionCommand = (line) => {
  const commandMatch = line.match(/^\\([a-z]+)\*?(?:\[[^\]]*\])?\s*/i);
  if (!commandMatch || !sectionLevels.has(commandMatch[1])) return null;
  const rest = line.slice(commandMatch[0].length).trim();
  if (!rest.startsWith("{")) return null;
  let depth = 0, title = "";
  for (let index = 0; index < rest.length; index += 1) {
    const char = rest[index];
    if (char === "{" && rest[index - 1] !== "\\") { depth += 1; if (depth > 1) title += char; continue; }
    if (char === "}" && rest[index - 1] !== "\\") {
      depth -= 1;
      if (depth === 0) return rest.slice(index + 1).trim() ? null : { command: commandMatch[1], title: title.trim() };
      title += char;
      continue;
    }
    if (depth > 0) title += char;
  }
  return null;
};

const convertLatexToHtml = (source) => {
  const normalized = source.replace(/\r\n?/g, "\n");
  const lines = normalized.split("\n");
  const out = [], paragraph = [], listItem = [], counters = new Map();
  let mode = "normal", listTag = "", envLines = [], quoteLines = [];

  const startList = (tag) => { flushParagraph(paragraph, out); out.push(`<${tag}>`); mode = tag === "ul" ? "itemize" : "enumerate"; listTag = tag; };
  const closeList = (expectedTag) => { if (listTag !== expectedTag) throw new Error(`Unexpected list close while in ${mode}`); flushListItem(listItem, out); out.push(`</${expectedTag}>`); listTag = ""; mode = "normal"; };

  for (const rawLine of lines) {
    const lineWithoutComment = mode === "verbatim" ? rawLine : stripLatexComment(rawLine);
    const line = lineWithoutComment.trim();

    if (mode === "verbatim") {
      if (line === "\\end{verbatim}") { out.push(`<pre><code>${escapeHtml(envLines.join("\n"))}</code></pre>`); envLines = []; mode = "normal"; }
      else envLines.push(rawLine);
      continue;
    }
    if (mode === "quote") {
      if (line === "\\end{quote}") { out.push(`<blockquote>${quoteLines.map(inlineLatexToHtml).join("<br>")}</blockquote>`); quoteLines = []; mode = "normal"; }
      else if (line) quoteLines.push(line);
      continue;
    }
    if (mode === "itemize" || mode === "enumerate") {
      if (line === "") { flushListItem(listItem, out); continue; }
      if (line === "\\end{itemize}") { closeList("ul"); continue; }
      if (line === "\\end{enumerate}") { closeList("ol"); continue; }
      const item = line.match(/^\\item(?:\s+(.*))?$/);
      if (item) { flushListItem(listItem, out); if (item[1]) listItem.push(item[1]); }
      else if (listItem.length > 0) listItem.push(line);
      else throw new Error(`List content must start with \\item: ${line}`);
      continue;
    }

    if (line === "") { flushParagraph(paragraph, out); continue; }
    if (line === "\\begin{verbatim}") { flushParagraph(paragraph, out); mode = "verbatim"; continue; }
    if (line === "\\begin{quote}") { flushParagraph(paragraph, out); mode = "quote"; continue; }
    if (line === "\\begin{itemize}") { startList("ul"); continue; }
    if (line === "\\begin{enumerate}") { startList("ol"); continue; }

    const section = parseSectionCommand(line);
    if (section) {
      flushParagraph(paragraph, out);
      const level = sectionLevels.get(section.command);
      const baseId = slugify(section.title);
      const count = counters.get(baseId) ?? 0;
      counters.set(baseId, count + 1);
      const id = count === 0 ? baseId : `${baseId}-${count + 1}`;
      out.push(`<h${level} id="${id}">${inlineLatexToHtml(section.title)}</h${level}>`);
      continue;
    }
    paragraph.push(line);
  }
  if (mode !== "normal") throw new Error(`Unclosed LaTeX environment: ${mode}`);
  flushParagraph(paragraph, out);
  return out.join("\n");
};

const normalizeArticleIndex = (value) => {
  if (!Array.isArray(value)) throw new Error("Invalid article index: expected an array");
  return value.map((item, index) => normalizeArticleMeta(item, index));
};
const normalizeArticleMeta = (value, index) => {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`Invalid article index item at ${index}: expected object`);
  const slug = requiredString(value.slug, `item ${index}.slug`);
  const date = requiredString(value.date, `item ${index}.date`);
  const tags = requiredStringArray(value.tags, `item ${index}.tags`);
  const title = requiredLangRecord(value.title, `item ${index}.title`);
  const description = requiredLangRecord(value.description, `item ${index}.description`);
  const languages = requiredLangArray(value.languages, `item ${index}.languages`);
  return { slug, date, tags, title, description, languages };
};
const requiredString = (value, path) => { if (typeof value !== "string" || value.trim() === "") throw new Error(`Invalid article index: ${path} must be a non-empty string`); return value; };
const requiredStringArray = (value, path) => { if (!Array.isArray(value) || value.some((item) => typeof item !== "string" || item.trim() === "")) throw new Error(`Invalid article index: ${path} must be a string array`); return value; };
const requiredLangRecord = (value, path) => { if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`Invalid article index: ${path} must be an object`); return { ru: requiredString(value.ru, `${path}.ru`), en: requiredString(value.en, `${path}.en`) }; };
const requiredLangArray = (value, path) => { const languages = requiredStringArray(value, path); if (languages.some((lang) => !supportedLangs.includes(lang))) throw new Error(`Invalid article index: ${path} must contain only ${supportedLangs.join("/")}`); return [...new Set(languages)]; };

const normalizeSiteUrl = (value) => value.replace(/\/+$/g, "");
const articlePath = (lang, slug) => `/${lang}/articles/${encodeURIComponent(slug)}`;
const articlePdfPath = (lang, slug) => `${articlePath(lang, slug)}.pdf`;
const tagPath = (lang, tag) => `/${lang}/tags/${encodeURIComponent(tag)}`;
const collectTagsByLang = (articles) => {
  const result = { en: new Set(), ru: new Set() };
  for (const article of articles) for (const lang of article.languages) for (const tag of article.tags) result[lang].add(tag);
  return result;
};
const buildSitemapEntries = (articles, tagsByLang) => {
  const entries = [localizedEntry("/en", "/ru", DEFAULT_LASTMOD), localizedEntry("/en/articles", "/ru/articles", latestDate(articles)), localizedEntry("/en/tags", "/ru/tags", latestDate(articles))];
  for (const lang of supportedLangs) for (const tag of tagsByLang[lang]) entries.push({ path: tagPath(lang, tag), lastmod: latestDate(articlesWithTag(articles, lang, tag)), alternates: tagAlternates(tag, tagsByLang) });
  for (const article of articles) for (const lang of article.languages) entries.push({ path: articlePath(lang, article.slug), lastmod: article.date, alternates: articleAlternates(article) });
  return entries;
};
const localizedEntry = (enPath, ruPath, lastmod) => ({ path: enPath, lastmod, alternates: { en: enPath, ru: ruPath, "x-default": enPath } });
const articleAlternates = (article) => { const alternates = {}; for (const lang of article.languages) alternates[lang] = articlePath(lang, article.slug); alternates["x-default"] = alternates.en ?? alternates.ru; return alternates; };
const tagAlternates = (tag, tagsByLang) => { const alternates = {}; for (const lang of supportedLangs) if (tagsByLang[lang].has(tag)) alternates[lang] = tagPath(lang, tag); alternates["x-default"] = alternates.en ?? alternates.ru; return alternates; };
const articlesWithTag = (articles, lang, tag) => articles.filter((article) => article.languages.includes(lang) && article.tags.includes(tag));
const latestDate = (articles) => articles.reduce((latest, article) => article.date > latest ? article.date : latest, DEFAULT_LASTMOD);
const renderSitemap = (entries, siteUrl) => [XML_HEADER, SITEMAP_ROOT, ...entries.map((entry) => renderSitemapEntry(entry, siteUrl)), "</urlset>"].join("\n");
const renderSitemapEntry = (entry, siteUrl) => { const lines = ["  <url>", `    <loc>${xmlEscape(siteUrl + entry.path)}</loc>`, `    <lastmod>${xmlEscape(entry.lastmod)}</lastmod>`]; for (const [hreflang, path] of Object.entries(entry.alternates ?? {})) if (path) lines.push(`    <xhtml:link rel="alternate" hreflang="${xmlEscape(hreflang)}" href="${xmlEscape(siteUrl + path)}" />`); lines.push("  </url>"); return lines.join("\n"); };
const renderRobots = (siteUrl) => ["User-agent: *", "Allow: /", "Disallow: /generated/", `Sitemap: ${siteUrl}/sitemap.xml`, ""].join("\n");
const renderHeaders = (articles, siteUrl) => {
  const lines = ["/*", "  X-Content-Type-Options: nosniff", "  Referrer-Policy: strict-origin-when-cross-origin", "", "/404.html", "  X-Robots-Tag: noindex, nofollow", "", "/generated/*", "  X-Robots-Tag: noindex, nofollow", ""];
  for (const article of articles) for (const lang of article.languages) { lines.push(articlePdfPath(lang, article.slug)); lines.push(`  Link: <${siteUrl}${articlePath(lang, article.slug)}>; rel=\"canonical\"`); lines.push("  X-Robots-Tag: index, follow", ""); }
  return lines.join("\n");
};
const renderVercelConfig = (articles, siteUrl) => ({ cleanUrls: true, trailingSlash: false, headers: [{ source: "/404.html", headers: [{ key: "X-Robots-Tag", value: "noindex, nofollow" }] }, ...articles.flatMap((article) => article.languages.map((lang) => ({ source: articlePdfPath(lang, article.slug), headers: [{ key: "Link", value: `<${siteUrl}${articlePath(lang, article.slug)}>; rel=\"canonical\"` }, { key: "X-Robots-Tag", value: "index, follow" }] })))] });
const renderRssFeed = (lang, articles, siteUrl) => {
  const langArticles = articles.filter((article) => article.languages.includes(lang)).sort((a, b) => b.date.localeCompare(a.date)).slice(0, 20);
  return [XML_HEADER, '<rss version="2.0">', '  <channel>', `    <title>${xmlEscape(lang === "ru" ? "autophany.space — статьи" : "autophany.space — articles")}</title>`, `    <link>${xmlEscape(siteUrl + `/${lang}/articles`)}</link>`, `    <description>${xmlEscape(lang === "ru" ? "Новые LaTeX-статьи autophany.space" : "New LaTeX articles from autophany.space")}</description>`, `    <language>${lang}</language>`, ...langArticles.map((article) => ["    <item>", `      <title>${xmlEscape(article.title[lang])}</title>`, `      <link>${xmlEscape(siteUrl + articlePath(lang, article.slug))}</link>`, `      <guid>${xmlEscape(siteUrl + articlePath(lang, article.slug))}</guid>`, `      <pubDate>${new Date(article.date + "T00:00:00Z").toUTCString()}</pubDate>`, `      <description>${xmlEscape(article.description[lang])}</description>`, "    </item>"].join("\n")), '  </channel>', '</rss>'].join("\n");
};
const render404 = () => `<!doctype html>
<html lang="en" data-theme="dark">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="robots" content="noindex,nofollow" />
    <title>signal lost :: autophany.space</title>
    <style>
      :root{color-scheme:dark;--bg:#080a0f;--surface:#0f151d;--text:#d7dde7;--muted:#8d99aa;--accent:#8ab4f8;--accent2:#66e3c4;--border:rgba(141,153,170,.22)}
      *{box-sizing:border-box}body{min-height:100vh;margin:0;display:grid;place-items:center;background:radial-gradient(circle at 50% 15%,rgba(138,180,248,.1),transparent 28rem),linear-gradient(180deg,#080a0f,#0c1118);color:var(--text);font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace}main{width:min(92vw,40rem);padding:2rem;border:1px dashed var(--border);background:linear-gradient(180deg,rgba(15,21,29,.94),rgba(8,10,15,.98));text-align:center}h1{margin:0 0 1rem;color:var(--accent);font-size:clamp(2rem,9vw,5rem);font-weight:700;letter-spacing:.02em;text-transform:lowercase}a{color:var(--text);text-decoration:none;border-bottom:1px dashed var(--accent2);font-size:clamp(1rem,3vw,1.25rem)}a:hover,a:focus-visible{color:var(--accent2);outline:none}
    </style>
  </head>
  <body>
    <main aria-label="404"><h1>signal lost</h1><a href="/">cd /</a></main>
  </body>
</html>`;
const xmlEscape = (value) => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&apos;");

await main();
