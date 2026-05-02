import type { Lang } from "../core/types";
import { articlePdfPath } from "../router/routePaths";
export const pdfService = { articlePdfPath, openArticlePdf(lang: Lang, slug: string): void { window.open(articlePdfPath(lang, slug), "_blank", "noopener,noreferrer"); } } as const;
