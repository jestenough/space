export type Lang = string;
export type Theme = "reading" | "light" | "system" | "dark";

export type Panel = string;
export type SectionRoute = { lang: Lang; page: "section"; section: string };
export type HomeRoute = { lang: Lang; page: "home"; panel: Panel };
export type ArticlesRoute = { lang: Lang; page: "articles" };
export type TagsRoute = { lang: Lang; page: "tags"; tag?: string };
export type ArticleRoute = { lang: Lang; page: "article"; slug: string };
export type InfoFileRoute = { lang: Lang; page: "info-file"; section: string; slug: string };
export type NotFoundRoute = { lang: Lang; page: "not-found"; slug?: string };
export type Route = HomeRoute | SectionRoute | ArticlesRoute | TagsRoute | ArticleRoute | InfoFileRoute | NotFoundRoute;

export type SectionMeta = {
  slug: string;
  label: Record<string, string>;
  title: Record<string, string>;
  description: Record<string, string>;
  system: boolean;
  count: number;
};

export type ArticleNeighbor = {
  title: string;
  path: string;
};

export type ArticleMeta = {
  slug: string;
  date: string;
  tags: string[];
  title: Record<string, string>;
  description: Record<string, string>;
  languages: Lang[];
  pdfPath?: string;
  canonicalPath?: string;
  translations?: Partial<Record<Lang, string>>;
  prev?: ArticleNeighbor | null;
  next?: ArticleNeighbor | null;
  wordCount?: number;
  readingTime?: number;
};

export type ArticlePayload = {
  meta: ArticleMeta;
  html: string;
};

export type InfoFileMeta = {
  section: string;
  slug: string;
  label: Record<string, string>;
  type: string;
  format: "markdown" | "text" | "tex" | string;
  date: string;
  title: Record<string, string>;
  description: Record<string, string>;
  languages: Lang[];
  translations?: Partial<Record<Lang, string>>;
  canonicalPath?: string;
  downloadPath?: string | null;
};

export type TagInfo = {
  name: string;
  count: number;
};

export type SortBy = "date-desc" | "date-asc" | "title-asc" | "title-desc";
export type TagSortBy = "name-asc" | "name-desc" | "count-desc" | "count-asc";

export type UiText = {
  brand: string;
  language: string;
  theme: string;
  navHome: string;
  navArticles: string;
  navTags: string;
  listTitle: string;
  tagsHeadline: string;
  welcomeTitle: string;
  welcomeLead: string;
  welcomeBody: string;
  tagsTitle: string;
  allTags: string;
  back: string;
  noArticles: string;
  searchPlaceholder: string;
  tagSearchPlaceholder: string;
  sortLabel: string;
  sizeLabel: string;
  pagePrev: string;
  pageNext: string;
  footerMotto: string;
  errorTitle: string;
  errorText: string;
  themeReading: string;
  themeSystem: string;
  themeLight: string;
  themeDark: string;
  articlesDescription: string;
  tagsDescription: string;
  taggedDescription: string;
  routeLostDescription: string;
  panelArticlesLead: string;
  panelArticlesBody: string;
  panelTagsLead: string;
  panelTagsBody: string;
  panelTagLead: string;
  panelTagBody: string;
};
