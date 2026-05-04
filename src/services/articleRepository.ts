import { loadArticle, loadArticleContent, loadArticleIndex, loadArticleMeta } from "@/features/articles/articles";
export const articleRepository = { loadIndex: loadArticleIndex, loadArticle, loadMeta: loadArticleMeta, loadContent: loadArticleContent } as const;
