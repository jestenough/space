const safeGet = (storage: Storage, key: string): string | null => {
  try {
    return storage.getItem(key);
  } catch {
    return null;
  }
};

const safeSet = (storage: Storage, key: string, value: string): boolean => {
  try {
    storage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
};

export const storageService = {
  get: (key: string): string | null => safeGet(window.localStorage, key),
  set: (key: string, value: string): boolean => safeSet(window.localStorage, key, value),
  getBoolean(key: string): boolean | null {
    const value = safeGet(window.localStorage, key);
    if (value === "true") return true;
    if (value === "false") return false;
    return null;
  },
  setBoolean: (key: string, value: boolean): boolean => safeSet(window.localStorage, key, String(value)),
} as const;
