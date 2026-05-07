import type { TagInfo } from "@/core/types";
import { normalizeQuery } from "@/features/articles/articleFilters";

export const filterTags = (tags: readonly TagInfo[], query: string): readonly TagInfo[] => {
  const normalizedQuery = normalizeQuery(query);
  return normalizedQuery ? tags.filter((tag) => tag.name.toLowerCase().includes(normalizedQuery)) : tags;
};
