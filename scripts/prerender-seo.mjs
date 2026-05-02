import { copyFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const DEFAULT_SITE_URL = "https://autophany.space";
const INDEX_FILE = "index.html";
const GENERATED_DIR = "generated";
const FEEDS_DIR = "feeds";

const root = resolve(process.cwd());
const dist = resolve(root, "dist");
const siteUrl = (process.env.SITE_URL || DEFAULT_SITE_URL).replace(/\/+$/g, "");
const articles = JSON.parse(await readFile(resolve(root, GENERATED_DIR, "articles-index.json"), "utf8"));
const template = await readFile(resolve(dist, INDEX_FILE), "utf8");

const collectLanguages = (source) => [...new Set(source.flatMap((article) => article.languages))].sort((a, b) => a.localeCompare(b));
const languages = collectLanguages(articles);

const collectTagsByLang = (source) => Object.fromEntries(collectLanguages(source).map((lang) => [lang, new Set(source.filter((article) => article.languages.includes(lang)).flatMap((article) => article.tags))]));
const tagsByLang = collectTagsByLang(articles);

const copyGeneratedSeoFiles = async () => {
  await copyFile(resolve(root, GENERATED_DIR, "sitemap.xml"), resolve(dist, "sitemap.xml"));
  for (const lang of languages) {
    await mkdir(resolve(dist, lang), { recursive: true });
    await copyFile(resolve(root, GENERATED_DIR, FEEDS_DIR, `${lang}.xml`), resolve(dist, lang, "feed.xml"));
  }
};

const renderArticle = async (article, lang) => {
  const body = await readFile(resolve(dist, GENERATED_DIR, "articles", `${article.slug}.${lang}.html`), "utf8");
  const path = articlePath(lang, article.slug);
  const content = [
    `<nav class="article-breadcrumbs" aria-label="Breadcrumbs"><a href="/${lang}">root</a> / <a href="/${lang}/articles">articles</a> / <span>${escapeHtml(article.slug)}</span></nav>`,
    body,
    `<nav class="article-seo-links" aria-label="Article links"><p>tags: ${article.tags.map((tag) => `<a href="${tagPath(lang, tag)}">#${escapeHtml(tag)}</a>`).join(" ")}</p><p><a href="${articlePdfPath(lang, article.slug)}" target="_blank" rel="noopener noreferrer">download PDF</a></p></nav>`
  ].join("\n");
  return applySeo(setArticleView(template, content, lang, article), {
    lang,
    title: `${localized(article.title, lang)} :: autophany.space`,
    description: localized(article.description, lang),
    path,
    type: "article",
    alternates: articleAlternates(article),
    jsonLd: [articleJsonLd(article, lang), breadcrumbsJsonLd([["autophany.space", `/${lang}`], ["articles", `/${lang}/articles`], [localized(article.title, lang), path]])]
  });
};

const renderHome = (lang) => {
  const path = `/${lang}`;
  const description = `autophany.space: LaTeX articles, notes, tags, metadata, and PDF versions (${lang}).`;
  return applySeo(withHtmlLang(template, lang), { lang, title: "autophany.space — LaTeX articles and notes", description, path, type: "website", alternates: sectionAlternates((itemLang) => `/${itemLang}`), jsonLd: [websiteJsonLd(lang, path, description)] });
};

const renderArticleCatalog = (lang) => {
  const path = `/${lang}/articles`;
  const description = `autophany.space LaTeX article catalog with HTML pages and PDF versions (${lang}).`;
  return applySeo(setListView(template, lang, renderArticleList(lang)), { lang, title: `Articles :: autophany.space`, description, path, type: "website", alternates: sectionAlternates((itemLang) => `/${itemLang}/articles`), jsonLd: [websiteJsonLd(lang, path, description)] });
};

const renderTags = (lang) => {
  const path = `/${lang}/tags`;
  const description = `autophany.space tag index and topical clusters (${lang}).`;
  return applySeo(setTagsView(template, lang, renderTagList(lang)), { lang, title: `Tags :: autophany.space`, description, path, type: "website", alternates: sectionAlternates((itemLang) => `/${itemLang}/tags`), jsonLd: [websiteJsonLd(lang, path, description)] });
};

const renderTagPage = (lang, tag) => {
  const path = tagPath(lang, tag);
  const description = `autophany.space articles tagged #${tag}.`;
  return applySeo(setListView(template, lang, renderArticleList(lang, articles.filter((article) => article.languages.includes(lang) && article.tags.includes(tag)))), { lang, title: `#${tag} :: autophany.space`, description, path, type: "website", alternates: tagAlternates(tag), jsonLd: [websiteJsonLd(lang, path, description)] });
};

const setArticleView = (html, content, lang, article) => withHtmlLang(html, lang)
  .replace('body data-default-panel="home"', 'body data-default-panel="articles"')
  .replace('<section id="article-list-view" class="list-stage"', '<section id="article-list-view" class="list-stage hidden"')
  .replace('<article id="article-view" class="article-stage hidden"', '<article id="article-view" class="article-stage"')
  .replace(/<a id="back-link" href="[^"]*" class="back-link">/, `<a id="back-link" href="/${lang}/articles" class="back-link">`)
  .replace('<div id="article-content"></div>', `<div id="article-content">${content}</div>`)
  .replace('<p id="welcome-title" class="welcome-title">root</p>', `<p id="welcome-title" class="welcome-title">${escapeHtml(localized(article.title, lang))}</p>`);

const setListView = (html, lang, list) => withHtmlLang(html, lang)
  .replace('body data-default-panel="home"', 'body data-default-panel="articles"')
  .replace('<section id="home-files-panel" class="panel info-panel"', '<section id="home-files-panel" class="panel info-panel hidden"')
  .replace('<section id="articles-panel" class="panel hidden directory-panel"', '<section id="articles-panel" class="panel directory-panel"')
  .replace('<ul id="article-list" class="article-list"></ul>', `<ul id="article-list" class="article-list">${list}</ul>`);

const setTagsView = (html, lang, list) => withHtmlLang(html, lang)
  .replace('body data-default-panel="home"', 'body data-default-panel="tags"')
  .replace('<section id="home-files-panel" class="panel info-panel"', '<section id="home-files-panel" class="panel info-panel hidden"')
  .replace('<section id="tags-panel" class="panel hidden directory-panel"', '<section id="tags-panel" class="panel directory-panel"')
  .replace('<ul id="tag-list" class="article-list"></ul>', `<ul id="tag-list" class="article-list">${list}</ul>`);

const withHtmlLang = (html, lang) => html.replace(/<html lang="[^"]+"/, `<html lang="${lang}"`);

const applySeo = (html, seo) => html
  .replace(/<title>[\s\S]*?<\/title>\n?/i, "")
  .replace(/\s*<meta name="description"[^>]*>\n?/gi, "")
  .replace(/\s*<meta name="robots"[^>]*>\n?/gi, "")
  .replace(/\s*<meta property="og:[^"]+"[^>]*>\n?/gi, "")
  .replace(/\s*<meta name="twitter:[^"]+"[^>]*>\n?/gi, "")
  .replace(/\s*<link rel="canonical"[^>]*>\n?/gi, "")
  .replace(/\s*<link rel="alternate" hreflang="[^"]+"[^>]*>\n?/gi, "")
  .replace(/\s*<script type="application\/ld\+json"[\s\S]*?<\/script>\n?/gi, "")
  .replace("</head>", `${renderHead(seo)}\n  </head>`);

const renderHead = (seo) => {
  const canonical = siteUrl + seo.path;
  const description = seo.description.replace(/\s+/g, " ").trim().slice(0, 155);
  const alternates = Object.entries(seo.alternates ?? {}).map(([hreflang, path]) => `    <link rel="alternate" hreflang="${escapeHtml(hreflang)}" href="${escapeHtml(siteUrl + path)}" />`).join("\n");
  return [
    `    <title>${escapeHtml(seo.title)}</title>`,
    `    <meta name="description" content="${escapeHtml(description)}" />`,
    '    <meta name="robots" content="index,follow" />',
    `    <link rel="canonical" href="${escapeHtml(canonical)}" />`,
    alternates,
    `    <meta property="og:title" content="${escapeHtml(seo.title)}" />`,
    `    <meta property="og:description" content="${escapeHtml(description)}" />`,
    `    <meta property="og:type" content="${seo.type === "article" ? "article" : "website"}" />`,
    `    <meta property="og:url" content="${escapeHtml(canonical)}" />`,
    `    <meta property="og:locale" content="${escapeHtml(formatOgLocale(seo.lang))}" />`,
    '    <meta name="twitter:card" content="summary" />',
    `    <meta name="twitter:title" content="${escapeHtml(seo.title)}" />`,
    `    <meta name="twitter:description" content="${escapeHtml(description)}" />`,
    `    <script type="application/ld+json">${JSON.stringify(seo.jsonLd.length === 1 ? seo.jsonLd[0] : seo.jsonLd).replace(/</g, "\\u003c")}</script>`
  ].filter(Boolean).join("\n");
};

const renderArticleList = (lang, source = articles.filter((article) => article.languages.includes(lang))) => [...source]
  .sort((a, b) => b.date.localeCompare(a.date))
  .map((article) => `<li class="article-card"><a class="article-card-link article-card-full" href="${articlePath(lang, article.slug)}"><strong>${escapeHtml(localized(article.title, lang))}</strong><div class="meta">${escapeHtml(article.date)} · ${escapeHtml(localized(article.description, lang))}</div></a></li>`)
  .join("\n");

const renderTagList = (lang) => [...tagsByLang[lang]]
  .sort((a, b) => a.localeCompare(b))
  .map((tag) => `<li><a class="tag-row" href="${tagPath(lang, tag)}"><span class="tag-name">#${escapeHtml(tag)}</span><span class="tag-count">${tagCountsByLang(lang).get(tag) ?? 0} files</span></a></li>`)
  .join("\n");

const tagCountsByLang = (lang) => {
  const counts = new Map();
  for (const article of articles) if (article.languages.includes(lang)) for (const tag of article.tags) counts.set(tag, (counts.get(tag) ?? 0) + 1);
  return counts;
};

const articleJsonLd = (article, lang) => {
  const path = articlePath(lang, article.slug);
  return { "@context": "https://schema.org", "@type": "BlogPosting", headline: localized(article.title, lang), description: localized(article.description, lang), author: { "@type": "Person", name: "autophany.space" }, datePublished: article.date, dateModified: article.date, mainEntityOfPage: { "@type": "WebPage", "@id": siteUrl + path }, inLanguage: lang, url: siteUrl + path, keywords: article.tags.join(", "), isPartOf: { "@type": "Blog", name: "autophany.space", url: siteUrl + `/${lang}` } };
};
const websiteJsonLd = (lang, path, description) => ({ "@context": "https://schema.org", "@type": "WebSite", name: "autophany.space", description, inLanguage: lang, url: siteUrl + path });
const breadcrumbsJsonLd = (items) => ({ "@context": "https://schema.org", "@type": "BreadcrumbList", itemListElement: items.map(([name, path], index) => ({ "@type": "ListItem", position: index + 1, name, item: siteUrl + path })) });
const sectionAlternates = (buildPath) => { const paths = {}; for (const lang of languages) paths[lang] = buildPath(lang); paths["x-default"] = paths.en ?? paths[languages[0]]; return paths; };
const articleAlternates = (article) => { const paths = {}; for (const lang of article.languages) paths[lang] = articlePath(lang, article.slug); paths["x-default"] = paths.en ?? paths[article.languages[0]]; return paths; };
const tagAlternates = (tag) => { const paths = {}; for (const lang of languages) if (tagsByLang[lang]?.has(tag)) paths[lang] = tagPath(lang, tag); paths["x-default"] = paths.en ?? paths[Object.keys(paths)[0]]; return paths; };
const articlePath = (lang, slug) => `/${lang}/articles/${encodeURIComponent(slug)}`;
const articlePdfPath = (lang, slug) => `${articlePath(lang, slug)}.pdf`;
const tagPath = (lang, tag) => `/${lang}/tags/${encodeURIComponent(tag)}`;
const writePage = async (path, html) => { const dir = resolve(dist, path.replace(/^\//, "")); await mkdir(dir, { recursive: true }); await writeFile(resolve(dir, INDEX_FILE), html, "utf8"); };
const localized = (texts, lang) => texts[lang] ?? texts.en ?? Object.values(texts)[0] ?? "";
const formatOgLocale = (lang) => {
  const [base, region] = String(lang).split("-");
  const resolvedRegion = (region ?? ({ en: "US", ru: "RU" }[base] ?? base)).toUpperCase();
  return `${base.toLowerCase()}_${resolvedRegion}`;
};
const escapeHtml = (value) => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");

tagsByLang;
await writePage(`/`, renderHome(languages[0] ?? "en"));
for (const lang of languages) {
  await writePage(`/${lang}`, renderHome(lang));
  await writePage(`/${lang}/articles`, renderArticleCatalog(lang));
  await writePage(`/${lang}/tags`, renderTags(lang));
  for (const tag of tagsByLang[lang]) await writePage(`/${lang}/tags/${encodeURIComponent(tag)}`, renderTagPage(lang, tag));
}
for (const article of articles) for (const lang of article.languages) await writePage(`/${lang}/articles/${encodeURIComponent(article.slug)}`, await renderArticle(article, lang));
await copyGeneratedSeoFiles();
console.log(`prerender_ok: ${articles.length} articles, ${Object.values(tagsByLang).reduce((sum, tags) => sum + tags.size, 0)} tag pages`);
