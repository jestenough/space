## v1.4.0

Дата: **2026.07.22**
- добавлены нумерованные интерактивные цитаты с явными диапазонами `\citetext{key}[location]{text}`, hover-подсветкой, переходом к источнику, открытием ссылок и копированием Reference в один клик
- добавлены строгие локализованные библиографии `references.<lang>.bib`, локализованное форматирование источников и preflight-проверки отсутствующих файлов, некорректных команд и неизвестных citation keys
- добавлены метаданные автора и соавторов с опциональными ссылками, видимый byline, авторы в JSON-LD и поддержка экспорта BibTeX
- PDF приведён к паритету с HTML: локализованные авторы, citations и библиография, стабильный порядок нумерации, улучшенная диагностика компилятора и кеширование по content fingerprint
- добавлен локальный JetBrains Mono с Latin/Cyrillic subsets для terminal UI, Inter сохранён для читаемого текста статей
- frontend разделён на независимые actions, citations, clipboard и panels modules; stateful PageController заменён явной композицией `initPage()`
- исправлено перемещение панелей между mobile/desktop при изменении viewport, сокращены лишние listeners, DOM-операции, paint-эффекты и повторные build-time проходы по HTML
- улучшены responsive image variants, явные размеры изображений, cache headers для media/fonts, Docker source mounts и повторяемость prerender/PDF сборок

## v1.3.0

Дата: **2026.06.28**
- добавлен отдельный renderer секции notes для коротких мыслей, сниппетов и gist-like записей
- добавлены тестовые заметки для Markdown code blocks, plain text snippets и заметок без кода
- добавлены подписи языка и копирование в один клик для всего code block и отдельных строк при hover/focus

## v1.2.6

Дата: **2026.06.26**
- уменьшен mobile CLS: visibility overlay, visibility TOC control и начальное состояние пагинации теперь пререндерятся
- сглажено переключение заголовков/TOC: убран двойной scroll handling и добавлена анимация active indicator

## v1.2.5

Дата: **2026.06.26**
- добавлены локальные webfont-файлы Inter, читаемый file content переведён на Inter
- добавлена публичная страница лицензий для исходного кода, контента и локального шрифта
- добавлена публичная privacy notice про cookies, аналитику, tracking, profiling и localStorage только для настроек интерфейса
- в file listing/stat ownership заменён с `root` на `guest`
- доработан desktop-шрифт логотипа для более стабильного отображения
- стабилизирован sticky header при скролле контента
- скорректированы spacing и weight desktop ASCII-логотипа
- desktop header переведён со sticky на fixed, чтобы убрать дёргание при скролле
- увеличен desktop-отступ контента под fixed header

## v1.2.4

Дата: **2026.06.25**
- исправлено использование `label`/`title`: списки секций теперь везде показывают `label`
- Dockerfile перенесены в отдельные Docker-директории по сервисам

## v1.2.3

Дата: **2026.06.24**
- changelog переведён на Markdown-исходники
- для Markdown-файлов добавлена навигация по заголовкам как у статей
- из статистики секций удалены строки `articles` и `downloads`


## v1.2.2

Дата: **2026.06.24**
- личный раздел переименован с `about/` в `profile/`
- обновлены текст навигации, метаданные section и примеры route validation
- в раздел profile добавлены `BIO.md`, `CONTACTS`, GPG-ключ

## v1.2.1

Дата: **2026.06.24**
- добавлена команда `python3 -m scripts.cli create` для создания content sections и items;
- Удален устаревший ContentFormat enum

## v1.2

Дата: **2026.06.23**
- доработан desktop terminal workstation layout; 
- команда навигации заменена на `tree -d -L 1 .`; 
- локализованы заголовки окон и tooltip кнопки `!ls`; 
- состояние desktop-панелей сохраняется в localStorage только на desktop; 
- мобильный интерфейс перестроен вокруг reader-first потока, компактных file actions и overlay-панелей; 
- zen mode включён только для читаемых файлов; 
- добавлен выход из zen mode по Escape и по пустой области; 
- кнопка выхода из zen mode сделана квадратной и более заметной; 
- raw/non-readable файлы не показывают zen actions

## v1

Дата: **2026.06.05**
- Инициализирована v1 сайта.
