export type TextStats = { words: number; chars: number };
export function countTextStats(value: string): TextStats {
  let words = 0, chars = 0, inWord = false, hasContent = false, pendingSpace = false;
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index);
    if (code === 32 || code === 9 || code === 10 || code === 11 || code === 12 || code === 13 || code === 160) {
      if (hasContent) pendingSpace = true;
      inWord = false;
      continue;
    }
    if (pendingSpace) { chars += 1; pendingSpace = false; }
    chars += 1; hasContent = true;
    if (!inWord) { words += 1; inWord = true; }
  }
  return { words, chars };
}
