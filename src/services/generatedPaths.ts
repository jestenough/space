import type { InfoFileMeta, Lang } from "@/core/types";

const generatedPath = (...parts: string[]): string => `/generated/${parts.map((part) => encodeURIComponent(part)).join("/")}`;

export const generatedSiteMetaPath = (): string => generatedPath("site-meta.json");
export const generatedSectionsIndexPath = (): string => generatedPath("sections-index.json");
export const generatedSectionIndexPath = (section: string): string => generatedPath("sections", `${section}.json`);

export const generatedFileHtmlPath = (section: string, slug: string, lang: Lang): string => generatedPath("files", section, `${slug}.${lang}.html`);

export const generatedInfoFileHtmlPath = (file: InfoFileMeta, lang: Lang): string => generatedFileHtmlPath(file.section, file.slug, lang);
