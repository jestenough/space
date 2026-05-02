import type { Lang } from "./types";

export function homePath(lang: Lang): string { return `/${lang}`; }
export function articlesPath(lang: Lang): string { return `/${lang}/articles`; }
export function tagsPath(lang: Lang): string { return `/${lang}/tags`; }
export function tagPath(lang: Lang, tag: string): string { return `${tagsPath(lang)}/${encodeURIComponent(tag)}`; }
export function articlePath(lang: Lang, slug: string): string { return `${articlesPath(lang)}/${encodeURIComponent(slug)}`; }
export function articlePdfPath(lang: Lang, slug: string): string { return `${articlePath(lang, slug)}.pdf`; }
export function infoFilePath(lang: Lang, slug: string): string { return `/${lang}/${encodeURIComponent(slug)}`; }
