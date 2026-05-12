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

export const storageService = {
  get: (key: StorageKey): string | null => safeGet(window.localStorage, key),
  set: (key: StorageKey, value: string): boolean => safeSet(window.localStorage, key, value),
} as const;
