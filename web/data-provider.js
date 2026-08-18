const DATA_BASE =
  "https://raw.githubusercontent.com/"
  + "hhaitam95/esc-opportunity-finder/main/data/";

async function fetchJson(filename) {
  const response = await fetch(
    `${DATA_BASE}${filename}?v=${Date.now()}`,
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      `Could not load ${filename} (${response.status})`,
    );
  }

  const payload =
    await response.json();

  if (
    !payload ||
    typeof payload !== "object"
  ) {
    throw new Error(
      `${filename} returned invalid data.`,
    );
  }

  return payload;
}

function normalizeCodes(values) {
  if (!Array.isArray(values)) {
    return [];
  }

  return [
    ...new Set(
      values
        .map(
          (value) =>
            String(value)
              .trim()
              .toUpperCase(),
        )
        .filter(Boolean),
    ),
  ];
}

function normalizeOpportunity(
  opportunity,
) {
  const item = {
    ...opportunity,
  };

  item.id = String(
    item.id ??
    item.opid ??
    item.opportunity_id ??
    item.opportunityId ??
    "",
  ).trim();

  const dates =
    item.activity_dates &&
    typeof item.activity_dates === "object"
      ? item.activity_dates
      : {};

  item.start_date =
    item.start_date ||
    dates.start ||
    "";

  item.end_date =
    item.end_date ||
    dates.end ||
    "";

  item.deadline =
    item.application_deadline ||
    item.deadline ||
    "";

  item.town =
    item.town ||
    item.city ||
    "";

  item.image_url =
    item.logo_url ||
    item.image_url ||
    "";

  item.participant_countries =
    normalizeCodes(
      Array.isArray(
        item.participant_countries,
      )
        ? item.participant_countries
        : item.eligible_countries,
    );

  item.eligible_countries =
    normalizeCodes(
      item.eligible_countries ||
      item.participant_countries,
    );

  return item;
}

function normalizeList(payload) {
  const list =
    Array.isArray(
      payload?.opportunities,
    )
      ? payload.opportunities
      : [];

  return list
    .filter(
      (item) =>
        item &&
        typeof item === "object",
    )
    .map(
      normalizeOpportunity,
    );
}

export async function loadData() {
  const [
    activePayload,
    expiredPayload,
  ] = await Promise.all([
    fetchJson(
      "opportunities.json",
    ),
    fetchJson(
      "expired.json",
    ),
  ]);

  const active =
    normalizeList(
      activePayload,
    );

  const archived =
    normalizeList(
      expiredPayload,
    );

  if (!active.length) {
    throw new Error(
      "Active opportunity dataset is empty.",
    );
  }

  const newIds =
    new Set(
      Array.isArray(
        activePayload.new_opportunity_ids,
      )
        ? activePayload.new_opportunity_ids.map(
            (value) =>
              String(value),
          )
        : [],
    );

  return {
    active,
    archived,
    newIds,
    generatedAt:
      activePayload.generated_at ||
      null,
  };
}
