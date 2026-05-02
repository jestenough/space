import { text } from "../i18n";
import type { Lang } from "../types";

export type PanelName = "home" | "articles" | "tags";

export function panelInfo(lang: Lang, panel: PanelName, tag?: string): { title: string; lead: string; body: string } {
  const ui = text(lang);
  if (panel === "home") {
    return {
      title: lang === "ru" ? "root" : "root",
      lead: lang === "ru"
        ? "Корневая директория пространства."
        : "Root directory of the space.",
      body: lang === "ru"
        ? "Здесь лежат прокликиваемые служебные файлы пространства."
        : "Clickable service files of the space live here."
    };
  }

  if (panel === "articles") {
    return {
      title: lang === "ru" ? "articles" : "articles",
      lead: lang === "ru"
        ? "Тексты, заметки и длинные материалы."
        : "Essays, notes, and long-form texts.",
      body: lang === "ru"
        ? "Список статей с поиском, сортировкой и постраничной навигацией."
        : "Article catalog with search, sorting, and pagination."
    };
  }

  if (panel === "tags") {
    if (tag) {
      return {
        title: lang === "ru" ? `тэг: ${tag}` : `tag: ${tag}`,
        lead: lang === "ru" ? `Описание тэга #${tag}` : `Description for #${tag}`,
        body: lang === "ru"
          ? `SEO-описание тэга #${tag}: тематическая подборка материалов, связанных этим маркером.`
          : `SEO description for #${tag}: a focused cluster of articles connected by this marker.`
      };
    }

    return {
      title: lang === "ru" ? "тэги" : "tags",
      lead: lang === "ru" ? "Индекс тематических маркеров." : "Index of topic markers.",
      body: lang === "ru"
        ? "Ниже выводятся только тэги и количество связанных файлов. Статьи появятся после выбора конкретного тэга."
        : "Only tags and related file counts are shown here. Articles appear after selecting a concrete tag."
    };
  }

  return {
    title: ui.welcomeTitle,
    lead: ui.welcomeLead,
    body: ui.welcomeBody
  };
}
