import type { TagInfo, TagSortBy } from "@/core/types";
export const compareTags = (a: TagInfo, b: TagInfo, sortBy: TagSortBy): number => { if (sortBy === "name-desc") return b.name.localeCompare(a.name); if (sortBy === "count-desc") return b.count - a.count || a.name.localeCompare(b.name); if (sortBy === "count-asc") return a.count - b.count || a.name.localeCompare(b.name); return a.name.localeCompare(b.name); };
export const sortTags = (tags: readonly TagInfo[], sortBy: TagSortBy): TagInfo[] => [...tags].sort((a, b) => compareTags(a, b, sortBy));
