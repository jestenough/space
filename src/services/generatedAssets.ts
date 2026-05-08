export class PromiseLruCache<T> {
  private readonly items = new Map<string, Promise<T>>();

  constructor(private readonly maxItems: number) {}

  get(key: string): Promise<T> | undefined {
    const value = this.items.get(key);
    if (!value) return undefined;
    this.items.delete(key);
    this.items.set(key, value);
    return value;
  }

  set(key: string, value: Promise<T>): void {
    if (this.items.has(key)) this.items.delete(key);
    this.items.set(key, value);
    while (this.items.size > this.maxItems) {
      const oldestKey = this.items.keys().next().value as string | undefined;
      if (!oldestKey) return;
      this.items.delete(oldestKey);
    }
  }

  delete(key: string): void {
    this.items.delete(key);
  }
}

export const fetchGeneratedJson = async (path: string): Promise<unknown> => {
  const response = await fetch(path, { cache: "no-cache" });
  if (!response.ok) throw new Error(`Failed to load ${path}: ${response.status}`);
  return response.json();
};

export const fetchGeneratedText = async (path: string): Promise<string> => {
  const response = await fetch(path, { cache: "no-cache" });
  if (!response.ok) throw new Error(`Failed to load ${path}: ${response.status}`);
  return response.text();
};
