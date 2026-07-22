export const initCitations = (root: HTMLElement): void => {
  const groups = new Map<string, HTMLElement[]>();
  root.querySelectorAll<HTMLElement>("[data-ref]").forEach((element) => {
    const ref = element.dataset.ref;
    if (!ref) return;
    const group = groups.get(ref) ?? [];
    group.push(element);
    groups.set(ref, group);
  });
  if (groups.size === 0) return;

  const leaveTimers = new Map<string, number>();
  let suppressHoverUntil = 0;
  const refFromTarget = (target: EventTarget | null): string | null => target instanceof Element
    ? target.closest<HTMLElement>("[data-ref]")?.dataset.ref ?? null
    : null;
  const highlight = (ref: string, on: boolean): void => {
    groups.get(ref)?.forEach((element) => element.classList.toggle("highlight", on));
  };
  const enter = (ref: string): void => {
    const timer = leaveTimers.get(ref);
    if (timer !== undefined) window.clearTimeout(timer);
    leaveTimers.delete(ref);
    highlight(ref, true);
  };
  const leave = (ref: string): void => {
    const timer = leaveTimers.get(ref);
    if (timer !== undefined) window.clearTimeout(timer);
    leaveTimers.set(ref, window.setTimeout(() => {
      highlight(ref, false);
      leaveTimers.delete(ref);
    }, 100));
  };

  root.addEventListener("pointerover", (event) => {
    if (performance.now() < suppressHoverUntil) return;
    const ref = refFromTarget(event.target);
    if (ref && ref !== refFromTarget(event.relatedTarget)) enter(ref);
  });
  root.addEventListener("pointerout", (event) => {
    if (performance.now() < suppressHoverUntil) return;
    const ref = refFromTarget(event.target);
    if (ref && ref !== refFromTarget(event.relatedTarget)) leave(ref);
  });
  root.addEventListener("focusin", (event) => {
    const ref = refFromTarget(event.target);
    if (ref) enter(ref);
  });
  root.addEventListener("focusout", (event) => {
    const ref = refFromTarget(event.target);
    if (ref && ref !== refFromTarget(event.relatedTarget)) highlight(ref, false);
  });
  root.addEventListener("click", (event) => {
    const citation = (event.target as HTMLElement).closest<HTMLAnchorElement>("a.citation[data-ref]");
    const ref = citation?.dataset.ref;
    if (!citation || !ref) return;
    event.preventDefault();
    suppressHoverUntil = performance.now() + 200;
    groups.forEach((_, groupRef) => highlight(groupRef, false));
    const reference = root.querySelector<HTMLElement>(`.ref-item[data-ref="${CSS.escape(ref)}"]`);
    if (!reference) return;
    window.history.replaceState({}, "", `${window.location.pathname}${window.location.search}#${reference.id}`);
    reference.scrollIntoView({ behavior: "auto", block: "center" });
    enter(ref);
    window.setTimeout(() => leave(ref), 700);
  });
};
