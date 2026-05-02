import { mkdir, readdir, readFile, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(process.cwd());
const metadataPath = resolve(root, "content", "articles-index.json");
const sourceDir = resolve(root, "content", "articles");
const generatedDir = resolve(root, "generated");
const outputDir = resolve(generatedDir, "articles");
const metaDir = resolve(generatedDir, "articles-meta");
const feedsDir = resolve(generatedDir, "feeds");
const DEFAULT_SITE_URL = "https://autophany.space";
const DEFAULT_LASTMOD = "2026-05-01";
const XML_HEADER = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>";
const SITEMAP_ROOT = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">';
const sectionLevels = new Map([["part", 1], ["chapter", 1], ["section", 1], ["subsection", 2], ["subsubsection", 3], ["paragraph", 4], ["subparagraph", 5]]);

const normalizeLang = (value) => {
  const match = String(value).match(/^([a-z]{2,3})(?:-([A-Za-z]{2}))?$/);
  if (!match) throw new Error(`Invalid language code: ${value}`);
  return match[2] ? `${match[1].toLowerCase()}-${match[2].toUpperCase()}` : match[1].toLowerCase();
};

const parseArticleFilename = (fileName) => {
  const match = fileName.match(/^(.+)\.([a-z]{2,3}(?:-[A-Za-z]{2})?)\.tex$/);
  if (!match) return null;
  const [, slug, rawLang] = match;
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) throw new Error(`Invalid article slug in filename: ${fileName}`);
  const lang = normalizeLang(rawLang);
  return { slug, lang, key: `${slug}.${lang}` };
};

const readSourceFiles = async (dir) => {
  const entries = await readdir(dir, { withFileTypes: true });
  const files = new Map();
  for (const entry of entries) {
    if (entry.isDirectory()) throw new Error(`Language subdirectories are not allowed in content/articles/: ${entry.name}`);
    if (!entry.isFile() || !entry.name.endsWith(".tex")) continue;
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
  const languages = requiredLangArray(value.languages, `item ${index}.languages`, title, description);
  return { slug, date, tags, title, description, languages };
};

const requiredString = (value, path) => {
  if (typeof value !== "string" || value.trim() === "") throw new Error(`Invalid article index: ${path} must be a non-empty string`);
  return value;
};

const requiredStringArray = (value, path) => {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string" || item.trim() === "")) throw new Error(`Invalid article index: ${path} must be a string array`);
  return [...new Set(value)];
};

const requiredLangRecord = (value, path) => {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`Invalid article index: ${path} must be an object`);
  const result = {};
  for (const [lang, text] of Object.entries(value)) result[normalizeLang(lang)] = requiredString(text, `${path}.${lang}`);
  if (Object.keys(result).length === 0) throw new Error(`Invalid article index: ${path} must not be empty`);
  return result;
};

const requiredLangArray = (value, path, title, description) => {
  const languages = [...new Set(requiredStringArray(value, path).map(normalizeLang))];
  for (const lang of languages) {
    if (!title[lang]) throw new Error(`Missing title.${lang}`);
    if (!description[lang]) throw new Error(`Missing description.${lang}`);
  }
  return languages;
};

const articleMetaForLang = (articles, article, lang, source) => {
  const langArticles = articles.filter((item) => item.languages.includes(lang)).sort((a, b) => b.date.localeCompare(a.date));
  const index = langArticles.findIndex((item) => item.slug === article.slug);
  const previous = index > 0 ? langArticles[index - 1] : null;
  const next = index >= 0 && index < langArticles.length - 1 ? langArticles[index + 1] : null;
  const words = countWords(source);
  return {
    ...article,
    pdfPath: articlePdfPath(lang, article.slug),
    canonicalPath: articlePath(lang, article.slug),
    translations: articleAlternates(article),
    prev: previous ? { title: previous.title[lang], path: articlePath(lang, previous.slug) } : null,
    next: next ? { title: next.title[lang], path: articlePath(lang, next.slug) } : null,
    wordCount: words,
    readingTime: Math.max(1, Math.ceil(words / 220))
  };
};

const countWords = (source) => source
  .replace(/\\[a-z]+(?:\[[^\]]*\])?\{([^{}]*)\}/gi, "$1")
  .replace(/\\[a-z]+/gi, " ")
  .replace(/[{}\\]/g, " ")
  .trim()
  .split(/\s+/)
  .filter(Boolean).length;

const escapeHtml = (value) => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
const xmlEscape = (value) => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&apos;");
const slugify = (value) => value.toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "").replace(/[^\p{Letter}\p{Number}]+/gu, "-").replace(/^-+|-+$/g, "") || "section";
const inlineLatexToHtml = (value) => escapeHtml(value).replace(/\\texttt\{([^{}]*)\}/g, "<code>$1</code>").replace(/\\emph\{([^{}]*)\}/g, "<em>$1</em>").replace(/\\textbf\{([^{}]*)\}/g, "<strong>$1</strong>").replace(/\\\\/g, "<br>");
const flushParagraph = (buffer, out) => { const text = buffer.join(" ").trim(); buffer.length = 0; if (text) out.push(`<p>${inlineLatexToHtml(text)}</p>`); };
const flushListItem = (buffer, out) => { const text = buffer.join(" ").trim(); buffer.length = 0; if (text) out.push(`<li>${inlineLatexToHtml(text)}</li>`); };

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
  const lines = source.replace(/\r\n?/g, "\n").split("\n");
  const out = [], paragraph = [], listItem = [], counters = new Map();
  let mode = "normal", listTag = "", envLines = [], quoteLines = [];
  const startList = (tag) => { flushParagraph(paragraph, out); out.push(`<${tag}>`); mode = tag === "ul" ? "itemize" : "enumerate"; listTag = tag; };
  const closeList = (expectedTag) => { if (listTag !== expectedTag) throw new Error(`Unexpected list close while in ${mode}`); flushListItem(listItem, out); out.push(`</${expectedTag}>`); listTag = ""; mode = "normal"; };

  for (const rawLine of lines) {
    const lineWithoutComment = mode === "verbatim" ? rawLine : stripLatexComment(rawLine);
    const line = lineWithoutComment.trim();
    if (mode === "verbatim") { if (line === "\\end{verbatim}") { out.push(`<pre><code>${escapeHtml(envLines.join("\n"))}</code></pre>`); envLines = []; mode = "normal"; } else envLines.push(rawLine); continue; }
    if (mode === "quote") { if (line === "\\end{quote}") { out.push(`<blockquote>${quoteLines.map(inlineLatexToHtml).join("<br>")}</blockquote>`); quoteLines = []; mode = "normal"; } else if (line) quoteLines.push(line); continue; }
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

const normalizeSiteUrl = (value) => value.replace(/\/+$/g, "");
const articlePath = (lang, slug) => `/${lang}/articles/${encodeURIComponent(slug)}`;
const articlePdfPath = (lang, slug) => `${articlePath(lang, slug)}.pdf`;
const tagPath = (lang, tag) => `/${lang}/tags/${encodeURIComponent(tag)}`;
const collectLanguages = (articles) => [...new Set(articles.flatMap((article) => article.languages))].sort((a, b) => a.localeCompare(b));
const collectTagsByLang = (articles) => {
  const result = Object.fromEntries(collectLanguages(articles).map((lang) => [lang, new Set()]));
  for (const article of articles) for (const lang of article.languages) for (const tag of article.tags) result[lang].add(tag);
  return result;
};
const sectionAlternates = (languages, buildPath) => { const alternates = {}; for (const lang of languages) alternates[lang] = buildPath(lang); alternates["x-default"] = alternates.en ?? alternates[languages[0]]; return alternates; };
const articleAlternates = (article) => { const alternates = {}; for (const lang of article.languages) alternates[lang] = articlePath(lang, article.slug); alternates["x-default"] = alternates.en ?? alternates[article.languages[0]]; return alternates; };
const tagAlternates = (tag, tagsByLang) => { const alternates = {}; for (const [lang, tags] of Object.entries(tagsByLang)) if (tags.has(tag)) alternates[lang] = tagPath(lang, tag); alternates["x-default"] = alternates.en ?? alternates[Object.keys(alternates)[0]]; return alternates; };
const articlesWithTag = (articles, lang, tag) => articles.filter((article) => article.languages.includes(lang) && article.tags.includes(tag));
const latestDate = (articles) => articles.reduce((latest, article) => article.date > latest ? article.date : latest, DEFAULT_LASTMOD);
const buildSitemapEntries = (articles, tagsByLang) => {
  const languages = collectLanguages(articles);
  const entries = [];
  for (const lang of languages) {
    entries.push({ path: `/${lang}`, lastmod: DEFAULT_LASTMOD, alternates: sectionAlternates(languages, (itemLang) => `/${itemLang}`) });
    entries.push({ path: `/${lang}/articles`, lastmod: latestDate(articles), alternates: sectionAlternates(languages, (itemLang) => `/${itemLang}/articles`) });
    entries.push({ path: `/${lang}/tags`, lastmod: latestDate(articles), alternates: sectionAlternates(languages, (itemLang) => `/${itemLang}/tags`) });
  }
  for (const lang of languages) for (const tag of tagsByLang[lang]) entries.push({ path: tagPath(lang, tag), lastmod: latestDate(articlesWithTag(articles, lang, tag)), alternates: tagAlternates(tag, tagsByLang) });
  for (const article of articles) for (const lang of article.languages) entries.push({ path: articlePath(lang, article.slug), lastmod: article.date, alternates: articleAlternates(article) });
  return entries;
};
const renderSitemap = (entries, siteUrl) => [XML_HEADER, SITEMAP_ROOT, ...entries.map((entry) => renderSitemapEntry(entry, siteUrl)), "</urlset>"].join("\n");
const renderSitemapEntry = (entry, siteUrl) => { const lines = ["  <url>", `    <loc>${xmlEscape(siteUrl + entry.path)}</loc>`, `    <lastmod>${xmlEscape(entry.lastmod)}</lastmod>`]; for (const [hreflang, path] of Object.entries(entry.alternates ?? {})) if (path) lines.push(`    <xhtml:link rel="alternate" hreflang="${xmlEscape(hreflang)}" href="${xmlEscape(siteUrl + path)}" />`); lines.push("  </url>"); return lines.join("\n"); };
const renderRobots = (siteUrl) => ["User-agent: *", "Allow: /", "Disallow: /generated/", `Sitemap: ${siteUrl}/sitemap.xml`, ""].join("\n");
const renderHeaders = (articles, siteUrl) => {
  const lines = ["/*", "  X-Content-Type-Options: nosniff", "  Referrer-Policy: strict-origin-when-cross-origin", "", "/404.html", "  X-Robots-Tag: noindex, nofollow", "", "/generated/*", "  X-Robots-Tag: noindex, nofollow", ""];
  for (const article of articles) for (const lang of article.languages) { lines.push(articlePdfPath(lang, article.slug)); lines.push(`  Link: <${siteUrl}${articlePath(lang, article.slug)}>; rel=\"canonical\"`); lines.push("  X-Robots-Tag: index, follow", ""); }
  return lines.join("\n");
};
const renderRssFeed = (lang, articles, siteUrl) => {
  const langArticles = articles.filter((article) => article.languages.includes(lang)).sort((a, b) => b.date.localeCompare(a.date)).slice(0, 20);
  return [XML_HEADER, '<rss version="2.0">', '  <channel>', `    <title>${xmlEscape(`autophany.space — ${lang} articles`)}</title>`, `    <link>${xmlEscape(siteUrl + `/${lang}/articles`)}</link>`, `    <description>${xmlEscape(`New LaTeX articles from autophany.space (${lang})`)}</description>`, `    <language>${lang}</language>`, ...langArticles.map((article) => ["    <item>", `      <title>${xmlEscape(article.title[lang])}</title>`, `      <link>${xmlEscape(siteUrl + articlePath(lang, article.slug))}</link>`, `      <guid>${xmlEscape(siteUrl + articlePath(lang, article.slug))}</guid>`, `      <pubDate>${new Date(article.date + "T00:00:00Z").toUTCString()}</pubDate>`, `      <description>${xmlEscape(article.description[lang])}</description>`, "    </item>"].join("\n")), '  </channel>', '</rss>'].join("\n");
};
const render404 = () => `<!doctype html>
<html lang="en" data-theme="dark">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="robots" content="noindex,nofollow" />
    <title>signal lost :: autophany.space</title>
    <style>:root{color-scheme:dark;--bg:#080a0f;--text:#d7dde7;--accent:#8ab4f8;--accent2:#66e3c4;--border:rgba(141,153,170,.22)}*{box-sizing:border-box}body{min-height:100vh;margin:0;display:grid;place-items:center;background:linear-gradient(180deg,#080a0f,#0c1118);color:var(--text);font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace}main{width:min(92vw,40rem);padding:2rem;border:1px dashed var(--border);text-align:center}h1{margin:0 0 1rem;color:var(--accent);font-size:clamp(2rem,9vw,5rem);font-weight:700;text-transform:lowercase}a{color:var(--text);text-decoration:none;border-bottom:1px dashed var(--accent2)}</style>
  </head>
  <body><main aria-label="404"><h1>signal lost</h1><a href="/">cd /</a></main></body>
</html>`;

const main = async () => {
  const articleIndex = normalizeArticleIndex(JSON.parse(await readFile(metadataPath, "utf8")));
  const sourceFiles = await readSourceFiles(sourceDir);
  validateSourcesAgainstIndex(sourceFiles, articleIndex);

  await rm(generatedDir, { recursive: true, force: true });
  await mkdir(outputDir, { recursive: true });
  await mkdir(metaDir, { recursive: true });
  await mkdir(feedsDir, { recursive: true });

  for (const article of articleIndex) {
    for (const lang of article.languages) {
      const sourcePath = resolve(sourceDir, `${article.slug}.${lang}.tex`);
      const source = await readFile(sourcePath, "utf8");
      await writeFile(resolve(outputDir, `${article.slug}.${lang}.html`), convertLatexToHtml(source), "utf8");
      await writeFile(resolve(metaDir, `${article.slug}.${lang}.json`), JSON.stringify(articleMetaForLang(articleIndex, article, lang, source), null, 2) + "\n", "utf8");
    }
  }

  const siteUrl = normalizeSiteUrl(process.env.SITE_URL || DEFAULT_SITE_URL);
  const languages = collectLanguages(articleIndex);
  const tagsByLang = collectTagsByLang(articleIndex);
  await writeFile(resolve(generatedDir, "articles-index.json"), JSON.stringify(articleIndex, null, 2) + "\n", "utf8");
  await writeFile(resolve(generatedDir, "sitemap.xml"), renderSitemap(buildSitemapEntries(articleIndex, tagsByLang), siteUrl), "utf8");
  await writeFile(resolve(root, "public", "robots.txt"), renderRobots(siteUrl), "utf8");
  await writeFile(resolve(root, "public", "404.html"), render404(), "utf8");
  await writeFile(resolve(root, "public", "_headers"), renderHeaders(articleIndex, siteUrl), "utf8");
  for (const lang of languages) await writeFile(resolve(feedsDir, `${lang}.xml`), renderRssFeed(lang, articleIndex, siteUrl), "utf8");
  console.log(`content_ok: ${articleIndex.length} articles, ${sourceFiles.size} source files, generated/ updated`);
};

await main();
