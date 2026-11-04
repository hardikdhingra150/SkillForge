// Node 25 ships an experimental global localStorage that shadows jsdom's; use the browser one.
Object.defineProperty(globalThis, "localStorage", {
  configurable: true,
  value: globalThis.jsdom.window.localStorage,
});
