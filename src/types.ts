export type Lang = "ru" | "en";
export type Theme = "reading" | "light" | "system" | "dark";

export type Panel = "home" | "articles" | "tags";
export type HomeRoute = { lang: Lang; page: "home"; panel: Panel };
export type ArticlesRoute = { lang: Lang; page: "articles" };
export type TagsRoute = { lang: Lang; page: "tags"; tag?: string };
export type ArticleRoute = { lang: Lang; page: "article"; slug: string };
export type InfoFileRoute = { lang: Lang; page: "info-file"; slug: string };
export type NotFoundRoute = { lang: Lang; page: "not-found"; slug?: string };
export type Route = HomeRoute | ArticlesRoute | TagsRoute | ArticleRoute | InfoFileRoute | NotFoundRoute;

export type ArticleMeta = {
  slug: string;
  date: string;
  tags: string[];
  title: Record<Lang, string>;
  description: Record<Lang, string>;
  languages: Lang[];
};

export type InfoFileMeta = {
  slug: string;
  sourcePath: string;
  publicPath: string;
  routeSlug: string;
  kind: "markdown" | "text";
  size: number;
  modified: string;
  permissions: string;
  owner: string;
  group: string;
  title: Record<Lang, string>;
  description: Record<Lang, string>;
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
  views: string;
  footerMotto: string;
  errorTitle: string;
  errorText: string;
  themeReading: string;
  themeSystem: string;
  themeLight: string;
  themeDark: string;
};
