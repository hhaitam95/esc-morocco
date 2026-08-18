const COUNTRY_STORAGE_KEY =
  "esc_participant_country";

const DEFAULT_FILTERS = Object.freeze({
  search: "",
  country: "",
  type: "",
  sort: "deadline",
});

function readStoredCountry() {
  try {
    return (
      localStorage.getItem(
        COUNTRY_STORAGE_KEY,
      ) || ""
    );
  } catch {
    return "";
  }
}

function saveCountry(value) {
  try {
    if (value) {
      localStorage.setItem(
        COUNTRY_STORAGE_KEY,
        value,
      );
    } else {
      localStorage.removeItem(
        COUNTRY_STORAGE_KEY,
      );
    }
  } catch {
    // Optional persistence.
  }
}

export function createState() {
  return {
    data: null,
    selectedParticipantCountry:
      readStoredCountry(),
    participantSearchApplied: false,
    filters: {
      ...DEFAULT_FILTERS,
    },
  };
}

export function setParticipantCountry(
  state,
  value,
) {
  state.selectedParticipantCountry =
    value || "";

  state.participantSearchApplied =
    Boolean(value);

  saveCountry(
    state.selectedParticipantCountry,
  );

  resetFilters(state);
}

export function resetFilters(state) {
  state.filters = {
    ...DEFAULT_FILTERS,
  };
}

export function clearTableFilters(state) {
  resetFilters(state);
}
