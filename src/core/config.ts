import type { UiText } from "@/core/types";
import { DEFAULT_LANG } from "@/core/languages";
export { DEFAULT_HREFLANG, DEFAULT_LANG } from "@/core/languages";

export const SITE_NAME = "autophany.space";
export const SITE_URL = "https://autophany.space";
export const SYSTEM_SECTION = "site";
export const ALL_TAGS = "__all__";
export const PAGE_SIZE_OPTIONS = [4, 8, 16, 32] as const;
export const DEFAULT_PAGE_SIZE: number = PAGE_SIZE_OPTIONS[0];
export const GITHUB_EDIT_BASE = "https://github.com/jestenough/personal/edit/main/content/articles";
export const ROUTE_PREFIX = /^(\/|\/[a-z]{2,3}(?:-[A-Z]{2})?(\/|$))/;

export const normalizePageSize = (value: number): number => (
  PAGE_SIZE_OPTIONS.includes(value as (typeof PAGE_SIZE_OPTIONS)[number]) ? value : DEFAULT_PAGE_SIZE
);

export const ASCII_LOGO = `#                                                                                                             
#       mm            m                  #                                   mmmm                             
#       ##   m   m  mm#mm   mmm   mmmm   # mm    mmm   m mm   m   m         #"   " mmmm    mmm    mmm    mmm  
#      #  #  #   #    #    #" "#  #" "#  #"  #  "   #  #"  #  "m m"         "#mmm  #" "#  "   #  #"  "  #"  # 
#      #mm#  #   #    #    #   #  #   #  #   #  m"""#  #   #   #m#              "# #   #  m"""#  #      #"""" 
#     #    # "mm"#    "mm  "#m#"  ##m#"  #   #  "mm"#  #   #   "#           "mmm#" ##m#"  "mm"#  "#mm"  "#mm" 
#                                 #                            m"                  #                         
#                                 "                           ""                   "                         `;

const EN_UI: UiText = {
  brand: SITE_NAME,
  language: "$ localectl set-locale LANG=",
  theme: "$ export THEME=",
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
  footerMotto: "Follow your curiosity. Lead humanity forward",
  errorTitle: "Could not load article",
  errorText: "If translation is missing, the app redirects to the home page.",
  missingTranslationTitle: "Not written yet",
  missingTranslationDescription: "This version does not exist yet, but it will be written.",
  actionPdf: "pdf",
  actionEdit: "edit",
  actionZen: "zen",
  actionDownload: "download",
  themeReading: "paper",
  themeSystem: "system",
  themeLight: "day",
  themeDark: "night",
  articlesDescription: "autophany.space article catalog: LaTeX, notes, tags, and terminal navigation.",
  tagsDescription: "Tag index and topical clusters in autophany.space.",
  taggedDescription: "Articles tagged in autophany.space.",
  routeLostDescription: "Route signal lost.",
  panelArticlesLead: "Essays, notes, and long-form texts.",
  panelArticlesBody: "Article catalog with search, sorting, and pagination.",
  panelTagsLead: "Index of topic markers.",
  panelTagsBody: "Tags and related file counts are shown here.",
  panelTagLead: "Articles grouped by one marker.",
  panelTagBody: "The list below is filtered by the selected tag."
};

export const UI: Record<string, UiText> = {
  [DEFAULT_LANG]: EN_UI,
  ru: {
    ...EN_UI,
    language: "$ localectl set-locale LANG=",
    theme: "$ export THEME=",
    listTitle: "Статьи",
    tagsHeadline: "Тэги",
    tagsTitle: "Теги:",
    allTags: "Все",
    noArticles: "Нет статей для выбранного языка",
    tagSearchPlaceholder: "tag",
     footerMotto: "Следуй любопытству. Веди человечество вперёд",
     errorTitle: "Не удалось загрузить article",
     errorText: "Если у статьи нет перевода, открывается главная страница.",
     missingTranslationTitle: "Пока не написано",
     missingTranslationDescription: "Этой версии пока нет, но она обязательно будет.",
     actionPdf: "pdf",
     actionEdit: "edit",
     actionZen: "zen",
     actionDownload: "download",
     themeReading: "paper/бумага",
    themeSystem: "system/система",
    themeLight: "day/день",
    themeDark: "night/ночь",
    articlesDescription: "Каталог статей autophany.space: LaTeX, заметки, тэги и терминальная навигация.",
    tagsDescription: "Индекс тэгов и тематических подборок autophany.space.",
    taggedDescription: "Материалы с выбранным тэгом в autophany.space.",
    routeLostDescription: "Маршрут потерян.",
    panelArticlesLead: "Тексты, заметки и длинные материалы.",
    panelArticlesBody: "Список статей с поиском, сортировкой и постраничной навигацией.",
    panelTagsLead: "Индекс тематических маркеров.",
    panelTagsBody: "Здесь выводятся тэги и количество связанных файлов.",
    panelTagLead: "Статьи, собранные по одному маркеру.",
    panelTagBody: "Ниже список материалов, отфильтрованный по выбранному тэгу."
  }
};
