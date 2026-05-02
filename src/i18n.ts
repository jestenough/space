import { UI } from "./config";
import { controls } from "./components/controls";
import { dom } from "./dom";
import type { Lang, UiText } from "./types";

const ASCII_LOGO = [
  "                 _              _                       ",
  "  __ _ _   _| |_ ___  _ __ | |__   __ _ _ __  _   _ ",
  " / _  | | | | __/ _ \| '_ \| '_ \ / _  | '_ \| | | |",
  "| (_| | |_| | || (_) | |_) | | | | (_| | | | | |_| |",
  " \__,_|\__,_|\__\___/| .__/|_| |_|\__,_|_| |_|\__, |",
  "                         |_|                      |___/ ",
  "                 autophany.space"
].join("\n");

export function text(lang: Lang): UiText {
  return UI[lang];
}

export function applyUiText(lang: Lang): void {
  const t = text(lang);
  dom.html.lang = lang;
  document.title = t.brand;
  dom.asciiLogo.textContent = ASCII_LOGO;
  dom.langLabel.textContent = t.language;
  dom.themeLabel.textContent = t.theme;
  dom.treeHome.textContent = t.navHome;
  dom.treeArticles.textContent = t.navArticles;
  dom.treeTags.textContent = t.navTags;
  dom.welcomeTitle.textContent = t.welcomeTitle;
  dom.welcomeLead.textContent = t.welcomeLead;
  dom.welcomeBody.textContent = t.welcomeBody;
  dom.listTitle.textContent = t.listTitle;
  const placeholders: Array<[HTMLInputElement, string]> = [
    [controls.articles.searchInput, t.searchPlaceholder],
    [controls.tags.searchInput, t.tagSearchPlaceholder]
  ];
  placeholders.forEach(([element, value]) => {
    element.placeholder = value;
  });
  [controls.articles.sortLabel, controls.tags.sortLabel].forEach((element) => {
    element.textContent = t.sortLabel;
  });
  [controls.articles.sizeLabel, controls.tags.sizeLabel].forEach((element) => {
    element.textContent = t.sizeLabel;
  });
  dom.tagsHeadline.textContent = t.tagsHeadline;
  dom.backLink.textContent = t.back;
  [controls.articles.pagePrev, controls.tags.pagePrev].forEach((element) => {
    element.textContent = t.pagePrev;
  });
  [controls.articles.pageNext, controls.tags.pageNext].forEach((element) => {
    element.textContent = t.pageNext;
  });
  dom.footerMotto.textContent = t.footerMotto;
  dom.errorTitle.textContent = t.errorTitle;
  dom.errorText.textContent = t.errorText;

  dom.themeSwitcher.options[0].textContent = t.themeReading;
  dom.themeSwitcher.options[1].textContent = t.themeLight;
  dom.themeSwitcher.options[2].textContent = t.themeSystem;
  dom.themeSwitcher.options[3].textContent = t.themeDark;
  dom.langSwitcher.options[0].textContent = "en_US.UTF-8";
  dom.langSwitcher.options[1].textContent = "ru_RU.UTF-8";
}
