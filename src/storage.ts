export function storageGet(storage: Storage, key: string): string | null { try { return storage.getItem(key); } catch { return null; } }
export function storageSet(storage: Storage, key: string, value: string): boolean { try { storage.setItem(key, value); return true; } catch { return false; } }
export function storageRemove(storage: Storage, key: string): void { try { storage.removeItem(key); } catch {} }
export function localGet(key: string): string | null { return storageGet(localStorage, key); }
export function localSet(key: string, value: string): boolean { return storageSet(localStorage, key, value); }
export function sessionGet(key: string): string | null { return storageGet(sessionStorage, key); }
export function sessionSet(key: string, value: string): boolean { return storageSet(sessionStorage, key, value); }
export function sessionRemove(key: string): void { storageRemove(sessionStorage, key); }
