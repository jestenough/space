
export const homePath = (lang: string): string => `/${lang}`;
export const rootPath = (): string => "/";
export const articlesPath = (lang: string): string => `/${lang}/articles`;
export const tagsPath = (lang: string): string => `/${lang}/tags`;
export const tagPath = (lang: string, tag: string): string => `${tagsPath(lang)}/${encodeURIComponent(tag)}`;
export const articlePath = (lang: string, slug: string): string => `${articlesPath(lang)}/${encodeURIComponent(slug)}`;
export const articlePdfPath = (lang: string, slug: string): string => `${articlePath(lang, slug)}.pdf`;
export const infoFilePath = (lang: string, slug: string): string => `/${lang}/${encodeURIComponent(slug)}`;
