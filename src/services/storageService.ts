import { StorageKey } from "@/core/enums";

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

const safeRemove = (storage: Storage, key: string): void => {
  try {
    storage.removeItem(key);
  } catch {}
};

export const storageService = {
  get: (key: StorageKey): string | null => safeGet(window.localStorage, key),
  set: (key: StorageKey, value: string): boolean => safeSet(window.localStorage, key, value),
  remove: (key: StorageKey): void => safeRemove(window.localStorage, key),
} as const;
