// Thin IndexedDB wrapper. Two stores for now:
//   kv     — small client state (active child id, cached board snapshot)
//   outbox — queued mutations awaiting a network connection (see outbox.js)
//
// No personal media is stored here. Phase 2 uses the Cache API (via the service
// worker) for card audio/icons, keyed by the stable /api/media/<id> URL.

const DB_NAME = "alut4u";
const DB_VERSION = 1;

let dbp;

function open() {
  if (dbp) return dbp;
  dbp = new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains("kv")) db.createObjectStore("kv");
      if (!db.objectStoreNames.contains("outbox")) {
        db.createObjectStore("outbox", { keyPath: "id" });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  return dbp;
}

function tx(store, mode, fn) {
  return open().then(
    (db) =>
      new Promise((resolve, reject) => {
        const t = db.transaction(store, mode);
        const result = fn(t.objectStore(store));
        t.oncomplete = () => resolve(result?.value ?? result);
        t.onerror = () => reject(t.error);
        t.onabort = () => reject(t.error);
      }),
  );
}

export const kv = {
  get: (key) => tx("kv", "readonly", (s) => s.get(key)),
  set: (key, val) => tx("kv", "readwrite", (s) => s.put(val, key)),
  del: (key) => tx("kv", "readwrite", (s) => s.delete(key)),
};

export const outboxStore = {
  add: (entry) => tx("outbox", "readwrite", (s) => s.put(entry)),
  all: () => tx("outbox", "readonly", (s) => s.getAll()),
  del: (id) => tx("outbox", "readwrite", (s) => s.delete(id)),
};
