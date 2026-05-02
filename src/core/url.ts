export const safeDecodeURIComponent = (value: string): string | null => { try { return decodeURIComponent(value); } catch { return null; } };
