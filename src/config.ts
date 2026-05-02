import type { Lang, UiText } from "./types";

export const SUPPORTED_LANGS: readonly Lang[] = ["ru", "en"];
export const DEFAULT_LANG: Lang = "en";
export const DEFAULT_HREFLANG = "x-default" as const;
export const LANG_EN: Lang = "en";
export const LANG_RU: Lang = "ru";
export const OG_LOCALE_BY_LANG: Record<Lang, string> = { en: "en_US", ru: "ru_RU" };
export const ALL_TAGS = "__all__";
export const PAGE_SIZE_OPTIONS = [4, 8, 16, 32] as const;
export const DEFAULT_PAGE_SIZE: number = PAGE_SIZE_OPTIONS[0];
export const GITHUB_EDIT_BASE = "https://github.com/jestenough/personal/edit/main/blog/content/articles";

export const ROUTE_PREFIX = /^(\/$|\/(en|ru)(\/|$))/;

export const UI: Record<Lang, UiText> = {
  ru: {
    brand: "autophany.space",
    language: "$ localectl set-locale LANG=",
    theme: "$ export THEME=",
    navHome: "root/",
    navArticles: "articles/",
    navTags: "tags/",
    welcomeTitle: "root",
    welcomeLead: "Корневая директория пространства.",
    welcomeBody: "Здесь лежат прокликиваемые служебные файлы пространства.",
    listTitle: "Статьи",
    tagsHeadline: "Тэги",
    tagsTitle: "Теги:",
    allTags: "Все",
    back: "cd ..",
    noArticles: "Нет статей для выбранного языка",
    searchPlaceholder: "pattern",
    tagSearchPlaceholder: "tag",
    sortLabel: "$ sort -k",
    sizeLabel: "$ head -n",
    pagePrev: "prev",
    pageNext: "next",
    views: "просмотров",
    footerMotto: "Следуй любопытству. Веди человечество вперёд",
    errorTitle: "Не удалось загрузить article",
    errorText: "Если у статьи нет перевода, открывается главная страница.",
    themeReading: "paper/бумага",
    themeSystem: "system/система",
    themeLight: "day/день",
    themeDark: "night/ночь"
  },
  en: {
    brand: "autophany.space",
    language: "$ localectl set-locale LANG=",
    theme: "$ export THEME=",
    navHome: "root/",
    navArticles: "articles/",
    navTags: "tags/",
    welcomeTitle: "root",
    welcomeLead: "Root directory of the space.",
    welcomeBody: "Service files of the space live here.",
    listTitle: "articles",
    tagsHeadline: "Tags",
    tagsTitle: "Tags:",
    allTags: "All",
    back: "cd ..",
    noArticles: "No articles available for this language",
    searchPlaceholder: "pattern",
    tagSearchPlaceholder: "tag",
    sortLabel: "$ sort -k",
    sizeLabel: "$ head -n",
    pagePrev: "prev",
    pageNext: "next",
    views: "views",
    footerMotto: "Follow your curiosity. Lead humanity forward",
    errorTitle: "Could not load article",
    errorText: "If translation is missing, the app redirects to the home page.",
    themeReading: "paper",
    themeSystem: "system",
    themeLight: "day",
    themeDark: "night"
  }
};
