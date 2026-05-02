export type TextStats = { words: number; chars: number };
export const countTextStats = (value: string): TextStats => {
  const text = value.replace(/<[^>]+>/g, " ").replace(/&[a-z]+;/gi, " ").trim();
  return { words: text ? text.split(/\s+/).length : 0, chars: text.length };
};
