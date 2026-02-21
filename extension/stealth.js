// Injected into MAIN world at document_start, before any page JS runs.
// Patches navigator.userAgentData.brands to include "Google Chrome".

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

  const originalUAData = navigator.userAgentData;
  const originalGetHighEntropyValues = originalUAData.getHighEntropyValues.bind(originalUAData);

  const patchedUAData = {
    brands: BRANDS,
    mobile: originalUAData.mobile,
    platform: originalUAData.platform,
    getHighEntropyValues(hints) {
      return originalGetHighEntropyValues(hints).then((values) => {
        if (values.brands) values.brands = BRANDS;
        if (values.fullVersionList) values.fullVersionList = FULL_VERSION_LIST;
        return values;
      });
    },
    toJSON() {
      return {
        brands: BRANDS,
        mobile: this.mobile,
        platform: this.platform,
      };
    },
  };

  Object.defineProperty(patchedUAData, Symbol.toStringTag, {
    value: "NavigatorUAData",
  });

  Object.setPrototypeOf(patchedUAData, NavigatorUAData.prototype);

  Object.defineProperty(navigator, "userAgentData", {
    get: () => patchedUAData,
    configurable: true,
  });
})();
