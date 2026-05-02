import { copyFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
const LANGS = ["en", "ru"];
const DEFAULT_SITE_URL = "https://autophany.space";
const INDEX_FILE = "index.html";
const GENERATED_DIR = "generated";
const FEEDS_DIR = "feeds";

const root = resolve(process.cwd());
const dist = resolve(root, "dist");
const siteUrl = (process.env.SITE_URL || DEFAULT_SITE_URL).replace(/\/+$/g, "");
const articles = JSON.parse(await readFile(resolve(root, GENERATED_DIR, "articles-index.json"), "utf8"));
const template = await readFile(resolve(dist, INDEX_FILE), "utf8");
let tagsByLang;

const copyGeneratedSeoFiles = async () => {
  await copyFile(resolve(root, GENERATED_DIR, "sitemap.xml"), resolve(dist, "sitemap.xml"));
  for (const lang of LANGS) {
    await mkdir(resolve(dist, lang), { recursive: true });
    await copyFile(resolve(root, GENERATED_DIR, FEEDS_DIR, `${lang}.xml`), resolve(dist, lang, "feed.xml"));
  }
};

const renderArticle = async (article, lang) => {
  const body = await readFile(resolve(dist, GENERATED_DIR, "articles", `${article.slug}.${lang}.html`), "utf8");
  const path = articlePath(lang, article.slug);
  const content = `<nav class="article-breadcrumbs" aria-label="Breadcrumbs"><a href="/${lang}">root</a> / <a href="/${lang}/articles">articles</a> / <span>${escapeHtml(article.slug)}</span></nav>\n${body}\n<nav class="article-seo-links" aria-label="Article links"><p>tags: ${article.tags.map((tag) => `<a href="${tagPath(lang, tag)}">#${escapeHtml(tag)}</a>`).join(" ")}</p><p><a href="${articlePdfPath(lang, article.slug)}" target="_blank" rel="noopener noreferrer">download PDF</a></p></nav>`;
  return applySeo(setArticleView(template, content, lang, article), { lang, title: `${article.title[lang]} :: autophany.space`, description: article.description[lang], path, type: "article", alternates: articleAlternates(article), jsonLd: [articleJsonLd(article, lang), breadcrumbsJsonLd([["autophany.space", `/${lang}`], [lang === "ru" ? "Статьи" : "Articles", `/${lang}/articles`], [article.title[lang], path]])] });
};
const renderHome = (lang) => { const path = `/${lang}`; const description = lang === "ru" ? "autophany.space: LaTeX-статьи, заметки, тэги, метаданные и PDF-версии." : "autophany.space: LaTeX articles, notes, tags, metadata, and PDF versions."; return applySeo(template.replace(/<html lang="[^"]+"/, `<html lang="${lang}"`), { lang, title: "autophany.space — LaTeX articles and notes", description, path, type: "website", alternates: { en: "/en", ru: "/ru", "x-default": "/en" }, jsonLd: [websiteJsonLd(lang, path, description)] }); };
const renderArticleCatalog = (lang) => { const path = `/${lang}/articles`; const description = lang === "ru" ? "Каталог LaTeX-статей autophany.space с HTML-страницами и PDF-версиями." : "autophany.space LaTeX article catalog with HTML pages and PDF versions."; return applySeo(setListView(template, lang, renderArticleList(lang)), { lang, title: lang === "ru" ? "Статьи :: autophany.space" : "Articles :: autophany.space", description, path, type: "website", alternates: { en: "/en/articles", ru: "/ru/articles", "x-default": "/en/articles" }, jsonLd: [websiteJsonLd(lang, path, description)] }); };
const renderTags = (lang) => { const path = `/${lang}/tags`; const description = lang === "ru" ? "Индекс тэгов и тематических подборок autophany.space." : "autophany.space tag index and topical clusters."; return applySeo(setTagsView(template, lang, renderTagList(lang)), { lang, title: lang === "ru" ? "Тэги :: autophany.space" : "Tags :: autophany.space", description, path, type: "website", alternates: { en: "/en/tags", ru: "/ru/tags", "x-default": "/en/tags" }, jsonLd: [websiteJsonLd(lang, path, description)] }); };
const renderTagPage = (lang, tag) => { const path = tagPath(lang, tag); const description = lang === "ru" ? `Материалы autophany.space с тэгом #${tag}.` : `autophany.space articles tagged #${tag}.`; return applySeo(setListView(template, lang, renderArticleList(lang, articles.filter((a) => a.languages.includes(lang) && a.tags.includes(tag)))), { lang, title: `#${tag} :: autophany.space`, description, path, type: "website", alternates: tagAlternates(tag), jsonLd: [websiteJsonLd(lang, path, description)] }); };
const setArticleView = (html, content, lang, article) => html.replace(/<html lang="[^"]+"/, `<html lang="${lang}"`).replace('body data-default-panel="home"', 'body data-default-panel="articles"').replace('<section id="article-list-view" class="list-stage"', '<section id="article-list-view" class="list-stage hidden"').replace('<article id="article-view" class="article-stage hidden"', '<article id="article-view" class="article-stage"').replace(/<a id="back-link" href="[^"]*" class="back-link">/, `<a id="back-link" href="/${lang}/articles" class="back-link">`).replace('<div id="article-content"></div>', `<div id="article-content">${content}</div>`).replace('<p id="welcome-title" class="welcome-title">root</p>', `<p id="welcome-title" class="welcome-title">${escapeHtml(article.title[lang])}</p>`);
const setListView = (html, lang, list) => html.replace(/<html lang="[^"]+"/, `<html lang="${lang}"`).replace('body data-default-panel="home"', 'body data-default-panel="articles"').replace('<section id="home-files-panel" class="panel info-panel"', '<section id="home-files-panel" class="panel info-panel hidden"').replace('<section id="articles-panel" class="panel hidden directory-panel"', '<section id="articles-panel" class="panel directory-panel"').replace('<ul id="article-list" class="article-list"></ul>', `<ul id="article-list" class="article-list">${list}</ul>`);
const setTagsView = (html, lang, list) => html.replace(/<html lang="[^"]+"/, `<html lang="${lang}"`).replace('body data-default-panel="home"', 'body data-default-panel="tags"').replace('<section id="home-files-panel" class="panel info-panel"', '<section id="home-files-panel" class="panel info-panel hidden"').replace('<section id="tags-panel" class="panel hidden directory-panel"', '<section id="tags-panel" class="panel directory-panel"').replace('<ul id="tag-list" class="article-list"></ul>', `<ul id="tag-list" class="article-list">${list}</ul>`);
const applySeo = (html, seo) => html.replace(/<title>[\s\S]*?<\/title>\n?/i, "").replace(/\s*<meta name="description"[^>]*>\n?/gi, "").replace(/\s*<meta name="robots"[^>]*>\n?/gi, "").replace(/\s*<meta property="og:[^"]+"[^>]*>\n?/gi, "").replace(/\s*<meta name="twitter:[^"]+"[^>]*>\n?/gi, "").replace(/\s*<link rel="canonical"[^>]*>\n?/gi, "").replace(/\s*<link rel="alternate" hreflang="[^"]+"[^>]*>\n?/gi, "").replace(/\s*<script type="application\/ld\+json"[\s\S]*?<\/script>\n?/gi, "").replace("</head>", `${renderHead(seo)}\n  </head>`);
const renderHead = (seo) => { const canonical = siteUrl + seo.path, description = seo.description.replace(/\s+/g, " ").trim().slice(0, 155); const alternates = Object.entries(seo.alternates ?? {}).map(([h, p]) => `    <link rel="alternate" hreflang="${escapeHtml(h)}" href="${escapeHtml(siteUrl + p)}" />`).join("\n"); return [`    <title>${escapeHtml(seo.title)}</title>`, `    <meta name="description" content="${escapeHtml(description)}" />`, '    <meta name="robots" content="index,follow" />', `    <link rel="canonical" href="${escapeHtml(canonical)}" />`, alternates, `    <meta property="og:title" content="${escapeHtml(seo.title)}" />`, `    <meta property="og:description" content="${escapeHtml(description)}" />`, `    <meta property="og:type" content="${seo.type === "article" ? "article" : "website"}" />`, `    <meta property="og:url" content="${escapeHtml(canonical)}" />`, `    <meta property="og:locale" content="${seo.lang === "ru" ? "ru_RU" : "en_US"}" />`, '    <meta name="twitter:card" content="summary" />', `    <meta name="twitter:title" content="${escapeHtml(seo.title)}" />`, `    <meta name="twitter:description" content="${escapeHtml(description)}" />`, `    <script type="application/ld+json">${JSON.stringify(seo.jsonLd.length === 1 ? seo.jsonLd[0] : seo.jsonLd).replace(/</g, "\\u003c")}</script>`].filter(Boolean).join("\n"); };
const renderArticleList = (lang, source = articles.filter((a) => a.languages.includes(lang))) => source.sort((a, b) => b.date.localeCompare(a.date)).map((a) => `<li class="article-card"><a class="article-card-link article-card-full" href="${articlePath(lang, a.slug)}"><strong>${escapeHtml(a.title[lang])}</strong><div class="meta">${escapeHtml(a.date)} · ${escapeHtml(a.description[lang])}</div></a></li>`).join("\n");
const renderTagList = (lang) => [...tagsByLang[lang]].sort((a, b) => a.localeCompare(b)).map((tag) => `<li><a class="tag-row" href="${tagPath(lang, tag)}"><span class="tag-name">#${escapeHtml(tag)}</span><span class="tag-count">${articles.filter((a) => a.languages.includes(lang) && a.tags.includes(tag)).length} files</span></a></li>`).join("\n");
const articleJsonLd = (article, lang) => { const path = articlePath(lang, article.slug); return { "@context": "https://schema.org", "@type": "BlogPosting", headline: article.title[lang], description: article.description[lang], author: { "@type": "Person", name: "autophany.space" }, datePublished: article.date, dateModified: article.date, mainEntityOfPage: { "@type": "WebPage", "@id": siteUrl + path }, inLanguage: lang, url: siteUrl + path, keywords: article.tags.join(", "), isPartOf: { "@type": "Blog", name: "autophany.space", url: siteUrl + `/${lang}` } }; };
const websiteJsonLd = (lang, path, description) => ({ "@context": "https://schema.org", "@type": "WebSite", name: "autophany.space", description, inLanguage: lang, url: siteUrl + path });
const breadcrumbsJsonLd = (items) => ({ "@context": "https://schema.org", "@type": "BreadcrumbList", itemListElement: items.map(([name, path], i) => ({ "@type": "ListItem", position: i + 1, name, item: siteUrl + path })) });
const collectTagsByLang = (src) => { const tags = { en: new Set(), ru: new Set() }; for (const a of src) for (const lang of a.languages) for (const tag of a.tags) tags[lang].add(tag); return tags; };
const articleAlternates = (article) => { const o = {}; for (const lang of article.languages) o[lang] = articlePath(lang, article.slug); o["x-default"] = o.en ?? o.ru; return o; };
const tagAlternates = (tag) => { const o = {}; for (const lang of LANGS) if (tagsByLang[lang].has(tag)) o[lang] = tagPath(lang, tag); o["x-default"] = o.en ?? o.ru; return o; };
const articlePath = (lang, slug) => `/${lang}/articles/${encodeURIComponent(slug)}`;
const articlePdfPath = (lang, slug) => `${articlePath(lang, slug)}.pdf`;
const tagPath = (lang, tag) => `/${lang}/tags/${encodeURIComponent(tag)}`;
const writePage = async (path, html) => { const dir = resolve(dist, path.replace(/^\//, "")); await mkdir(dir, { recursive: true }); await writeFile(resolve(dir, INDEX_FILE), html, "utf8"); };
const escapeHtml = (v) => String(v).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");

tagsByLang = collectTagsByLang(articles);
await writePage(`/`, renderHome("en"));
for (const lang of LANGS) {
  await writePage(`/${lang}`, renderHome(lang));
  await writePage(`/${lang}/articles`, renderArticleCatalog(lang));
  await writePage(`/${lang}/tags`, renderTags(lang));
  for (const tag of tagsByLang[lang]) await writePage(`/${lang}/tags/${encodeURIComponent(tag)}`, renderTagPage(lang, tag));
}
for (const article of articles) for (const lang of article.languages) await writePage(`/${lang}/articles/${encodeURIComponent(article.slug)}`, await renderArticle(article, lang));
await copyGeneratedSeoFiles();
console.log(`prerender_ok: ${articles.length} articles, ${Object.values(tagsByLang).reduce((s, v) => s + v.size, 0)} tag pages`);
