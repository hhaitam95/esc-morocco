// ESC Opportunity Finder — data provider boundary
//
// Backend loading is intentionally disabled during the UI-only phase.
// Future backend work should be connected here instead of directly
// inside web/app.js.

window.ESC_DATA_PROVIDER = {
  enabled: false,

  async load() {
    return {
      activeData: null,
      expiredData: null,
      participantCountryIndex: null,
    };
  },
};
