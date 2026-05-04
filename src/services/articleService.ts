import { articleDescription, articleFallbackMeta, articleTitle, hasTranslation } from "@/features/articles/articles";
import { articleRepository } from "@/services/articleRepository";
export const loadArticleIndex = articleRepository.loadIndex;
export const loadArticle = articleRepository.loadArticle;
export { articleDescription, articleFallbackMeta, articleTitle, hasTranslation };
