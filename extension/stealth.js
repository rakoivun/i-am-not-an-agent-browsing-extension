// Injected into MAIN world at document_start, before any page JS runs.
// Patches navigator.userAgentData.brands to include "Google Chrome".
// Spoofs toString() and property descriptors to resist introspection.

(function () {
  const BRANDS = [
    { brand: "Chromium", version: "145" },
    { brand: "Google Chrome", version: "145" },
    { brand: "Not-A.Brand", version: "24" },
  ];

  const FULL_VERSION_LIST = [
    { brand: "Chromium", version: "145.0.7832.6" },
    { brand: "Google Chrome", version: "145.0.7832.6" },
    { brand: "Not-A.Brand", version: "24.0.0.0" },
  ];

  if (!navigator.userAgentData) return;

  // --- toString spoofing utility ---
  const nativeToString = Function.prototype.toString;
  const spoofedFns = new Map();

  function makeNative(fn, nativeName) {
    spoofedFns.set(fn, `function ${nativeName}() { [native code] }`);
    return fn;
  }

  const originalToString = nativeToString.call.bind(nativeToString);
  Function.prototype.toString = function () {
    if (spoofedFns.has(this)) return spoofedFns.get(this);
    return originalToString(this);
  };
  spoofedFns.set(Function.prototype.toString, "function toString() { [native code] }");

  // --- Build patched userAgentData ---
  const originalUAData = navigator.userAgentData;
  const originalGetHEV = originalUAData.getHighEntropyValues.bind(originalUAData);

  const getHighEntropyValues = makeNative(function getHighEntropyValues(hints) {
    return originalGetHEV(hints).then((values) => {
      if (values.brands) values.brands = BRANDS;
      if (values.fullVersionList) values.fullVersionList = FULL_VERSION_LIST;
      return values;
    });
  }, "getHighEntropyValues");

  const toJSON = makeNative(function toJSON() {
    return { brands: BRANDS, mobile: false, platform: originalUAData.platform };
  }, "toJSON");

  const patchedUAData = Object.create(NavigatorUAData.prototype, {
    brands: { get: makeNative(function brands() { return BRANDS; }, "get brands"), configurable: true, enumerable: true },
    mobile: { get: makeNative(function mobile() { return originalUAData.mobile; }, "get mobile"), configurable: true, enumerable: true },
    platform: { get: makeNative(function platform() { return originalUAData.platform; }, "get platform"), configurable: true, enumerable: true },
    getHighEntropyValues: { value: getHighEntropyValues, writable: true, configurable: true },
    toJSON: { value: toJSON, writable: true, configurable: true },
  });

  Object.defineProperty(patchedUAData, Symbol.toStringTag, {
    value: "NavigatorUAData",
    configurable: true,
  });

  // --- Patch navigator.userAgentData getter ---
  const uaDataGetter = makeNative(function userAgentData() {
    return patchedUAData;
  }, "get userAgentData");

  const originalDescriptor = Object.getOwnPropertyDescriptor(Navigator.prototype, "userAgentData");

  Object.defineProperty(Navigator.prototype, "userAgentData", {
    get: uaDataGetter,
    configurable: true,
    enumerable: true,
  });

  // --- Trap getOwnPropertyDescriptor so the getter looks native ---
  const originalGetOPD = Object.getOwnPropertyDescriptor;
  Object.getOwnPropertyDescriptor = function (obj, prop) {
    if (obj === Navigator.prototype && prop === "userAgentData") {
      return { get: uaDataGetter, set: undefined, enumerable: true, configurable: true };
    }
    if (obj === navigator && prop === "userAgentData") {
      return undefined;
    }
    return originalGetOPD.call(this, obj, prop);
  };
  spoofedFns.set(Object.getOwnPropertyDescriptor, "function getOwnPropertyDescriptor() { [native code] }");
})();
