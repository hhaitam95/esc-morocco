const FEATURES = Object.freeze({
  language: true,
  theme: true,
  participantCountry: true,
  search: true,
  filters: true,
  sorting: true,
  clearFilters: true,
  archives: true,
  newBadges: true,
    clear: true,
    expired: true,
});

export function enabled(name) {
  return FEATURES[name] === true;
}

export { FEATURES };
