const COUNTRY_ALIASES = Object.freeze({
  EL: "GR",
  UK: "GB",
});

export function normalizeCountryCode(value) {
  const code = String(value ?? "")
    .trim()
    .toUpperCase();

  if (!code) {
    return "";
  }

  return COUNTRY_ALIASES[code] || code;
}

export function flagForCountry(value) {
  const code =
    normalizeCountryCode(value);

  if (!/^[A-Z]{2}$/.test(code)) {
    return "🌍";
  }

  return String.fromCodePoint(
    ...code.split("").map(
      (letter) =>
        127397 +
        letter.charCodeAt(0),
    ),
  );
}

export function nameForCountry(
  value,
  locale = "en-GB",
) {
  const code =
    normalizeCountryCode(value);

  if (!code) {
    return "";
  }

  try {
    if (
      typeof Intl !== "undefined" &&
      typeof Intl.DisplayNames === "function"
    ) {
      return (
        new Intl.DisplayNames(
          [locale],
          { type: "region" },
        ).of(code) || code
      );
    }
  } catch {
    // Fall back to the code.
  }

  return code;
}

export function displayCountry(
  value,
  locale,
) {
  const code =
    normalizeCountryCode(value);

  return {
    code,
    name: nameForCountry(
      code,
      locale,
    ),
    flag: flagForCountry(code),
  };
}

export function participantCodes(
  opportunity,
) {
  const values = [
    ...(Array.isArray(
      opportunity?.participant_countries,
    )
      ? opportunity.participant_countries
      : []),
    ...(Array.isArray(
      opportunity?.eligible_countries,
    )
      ? opportunity.eligible_countries
      : []),
  ];

  return [
    ...new Set(
      values
        .map(normalizeCountryCode)
        .filter(Boolean),
    ),
  ];
}

export function matchesParticipantCountry(
  opportunity,
  selectedCountry,
) {
  const selected =
    normalizeCountryCode(
      selectedCountry,
    );

  if (!selected) {
    return false;
  }

  return participantCodes(
    opportunity,
  ).includes(selected);
}

export function collectParticipantCountries(
  opportunities,
) {
  const countries = new Set();

  for (const opportunity of opportunities) {
    for (
      const code
      of participantCodes(
        opportunity,
      )
    ) {
      countries.add(code);
    }
  }

  return [...countries].sort();
}
