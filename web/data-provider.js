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

  // A date-only deadline means the opportunity is open through the
  // entire calendar day. Normalize it to the end of that day so the
  // table countdown and active/expired classification share the same
  // semantics.
  const deadlineRaw = String(item.deadline).trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(deadlineRaw)) {
    item.deadline = `${deadlineRaw}T23:59:59`;
  }

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

function parseDateOnlyOrValue(value, endOfDay = false) {
  if (!value) {
    return null;
  }

  const raw = String(value).trim();
  const date = /^\d{4}-\d{2}-\d{2}$/.test(raw)
    ? new Date(
        `${raw}T${endOfDay ? "23:59:59" : "00:00:00"}`,
      )
    : new Date(raw);

  return Number.isNaN(date.getTime())
    ? null
    : date;
}

function deadlineHasPassed(opportunity) {
  if (!opportunity.deadline) {
    return false;
  }

  const deadline = parseDateOnlyOrValue(
    opportunity.deadline,
    true,
  );

  return Boolean(
    deadline &&
    deadline.getTime() < Date.now(),
  );
}

function activityHasEnded(opportunity) {
  if (!opportunity.end_date) {
    return false;
  }

  const endDate = parseDateOnlyOrValue(
    opportunity.end_date,
    true,
  );

  return Boolean(
    endDate &&
    endDate.getTime() < Date.now(),
  );
}

function shouldArchive(opportunity) {
  // An application deadline is decisive when one exists.
  // For no-deadline opportunities, the activity itself must have ended
  // before the opportunity can move to the expired section.
  if (deadlineHasPassed(opportunity)) {
    return true;
  }

  if (!opportunity.deadline) {
    return activityHasEnded(opportunity);
  }

  return false;
}

function mergeArchived(
  archived,
  expiredFromActive,
) {
  const merged = [];
  const seen = new Set();

  for (const opportunity of [
    ...archived,
    ...expiredFromActive,
  ]) {
    const id = String(
      opportunity.id || "",
    ).trim();

    if (id && seen.has(id)) {
      continue;
    }

    if (id) {
      seen.add(id);
    }

    merged.push(opportunity);
  }

  return merged;
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

  const rawActive =
    normalizeList(
      activePayload,
    );

  const archived =
    normalizeList(
      expiredPayload,
    );

  if (!rawActive.length) {
    throw new Error(
      "Active opportunity dataset is empty.",
    );
  }

  // Keep the UI truthful when the backend dataset has not yet moved a
  // record to the archive. Deadline-based opportunities expire when the
  // deadline passes. No-deadline opportunities expire only after the
  // activity itself has ended.
  const active = [];
  const expiredFromActive = [];

  for (const opportunity of rawActive) {
    if (shouldArchive(opportunity)) {
      expiredFromActive.push(opportunity);
    } else {
      active.push(opportunity);
    }
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
    archived: mergeArchived(
      archived,
      expiredFromActive,
    ),
    newIds,
    generatedAt:
      activePayload.generated_at ||
      null,
  };
}
