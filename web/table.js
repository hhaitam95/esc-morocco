const TOPIC_ICONS = {
  "Education and training": "📚",
  "Creativity and culture": "🎨",
  "Social challenges": "🤝",
  "Citizenship and democratic participation": "🗳️",
  "Environment and natural protection": "🌱",
  "Health and wellbeing": "❤️",
  "Employment and entrepreneurship": "💼",
  "Physical education and sport": "⚽",
  "Working against discrimination (including gender discrimination)": "🫱🏻‍🫲🏽",
  "Reception and integration of refugees and migrants": "🏠",
  "Support to local Small and Medium Enterprises": "🏢",
  "Nutrition and subsistence agriculture": "🌾",
  Shelter: "🏠",
  "Disaster prevention and recovery": "🛟",
  "Disaster Preparedness": "🚨",
  "Post Disaster relief": "🆘",
  "WASH (Water, sanitation and hygiene)": "🚿",
};

const ACTIVITY_TYPE_ICONS = {
  "Individual volunteering": "👤",
  "Team volunteering": "👥",
  "Volunteering teams": "👥",
  "Volunteering": "🤝",
  "Traineeship": "🎓",
  "Job": "💼",
};

export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function parseDate(value) {
  if (!value) return null;
  const raw = String(value).trim();
  const date = /^\d{4}-\d{2}-\d{2}$/.test(raw)
    ? new Date(`${raw}T00:00:00`)
    : new Date(raw);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDate(value, locale, fallback = "—") {
  const date = parseDate(value);
  if (!date) return fallback;
  return new Intl.DateTimeFormat(locale, {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function filterRows(opportunities, filters) {
  const search = String(filters.search || "").trim().toLocaleLowerCase();
  const country = String(filters.country || "").trim().toUpperCase();
  const type = String(filters.type || "").trim();

  return opportunities.filter((opportunity) => {
    if (search) {
      const text = [
        opportunity.title,
        opportunity.town,
        opportunity.location,
        opportunity.country,
        opportunity.activity_type,
        Array.isArray(opportunity.topics) ? opportunity.topics.join(" ") : "",
      ].join(" ").toLocaleLowerCase();
      if (!text.includes(search)) return false;
    }

    if (country && String(opportunity.country || "").toUpperCase() !== country) return false;
    if (type && String(opportunity.activity_type || "") !== type) return false;
    return true;
  });
}

function dateValue(value) {
  const date = parseDate(value);
  return date ? date.getTime() : Number.POSITIVE_INFINITY;
}

export function sortRows(opportunities, sort) {
  const result = [...opportunities];
  if (sort === "created") {
    return result.sort((a, b) => String(b.created || "").localeCompare(String(a.created || "")));
  }
  if (sort === "start") {
    return result.sort((a, b) => dateValue(a.start_date) - dateValue(b.start_date));
  }
  return result.sort((a, b) => dateValue(a.deadline) - dateValue(b.deadline));
}

function safeUrl(value) {
  if (!value) return "";
  try {
    const url = new URL(value, "https://youth.europa.eu");
    if (url.protocol !== "http:" && url.protocol !== "https:") return "";
    return url.href;
  } catch {
    return "";
  }
}

function renderCountry(opportunity, locale) {
  const code = String(opportunity.country || "").trim().toUpperCase();
  if (!code) return "";

  let name = code;
  let flag = "🌍";
  try {
    if (typeof Intl !== "undefined" && typeof Intl.DisplayNames === "function") {
      name = new Intl.DisplayNames([locale], { type: "region" }).of(code) || code;
    }
    if (/^[A-Z]{2}$/.test(code)) {
      flag = String.fromCodePoint(...code.split("").map((letter) => 127397 + letter.charCodeAt(0)));
    }
  } catch {
    // Keep fallback values.
  }

  return `<span class="country-display"><span class="country-flag" aria-hidden="true">${flag}</span><span>${escapeHtml(name)}</span></span>`;
}

function renderTopics(topics) {
  if (!Array.isArray(topics) || !topics.length) return "";
  return `<div class="topic-tags">${topics.map((topic) => `
    <span class="topic-tag" title="${escapeHtml(topic)}">
      ${TOPIC_ICONS[topic] ? `<span class="topic-icon">${TOPIC_ICONS[topic]}</span>` : ""}
      <span>${escapeHtml(topic)}</span>
    </span>
  `).join("")}</div>`;
}

function renderActivityDates(opportunity, locale, t) {
  const activity = [
    opportunity.start_date ? formatDate(opportunity.start_date, locale, "") : "",
    opportunity.end_date ? formatDate(opportunity.end_date, locale, "") : "",
  ].filter(Boolean).join(" → ");

  if (!activity) return `<span class="date-display">📅 ${escapeHtml(t("noDates"))}</span>`;
  return `<span class="date-display"><span class="date-icon" aria-hidden="true">📅</span><span>${escapeHtml(activity)}</span></span>`;
}

function renderDeadline(opportunity, locale, t) {
  const formatted = formatDate(opportunity.deadline, locale, t("noDeadline"));
  if (!opportunity.deadline) {
    return `<span class="deadline-display"><span class="deadline-icon" aria-hidden="true">⏰</span><span>${escapeHtml(formatted)}</span></span>`;
  }

  const deadline = parseDate(opportunity.deadline);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const target = new Date(deadline.getFullYear(), deadline.getMonth(), deadline.getDate());
  const days = Math.round((target - today) / 86400000);

  let statusClass = "";
  let statusText = "";
  if (days < 0) {
    statusClass = "deadline-expired";
  } else if (days === 0) {
    statusClass = "deadline-today";
    statusText = t("deadlineToday");
  } else if (days === 1) {
    statusClass = "deadline-soon";
    statusText = `1 ${t("dayLeft")}`;
  } else if (days <= 7) {
    statusClass = "deadline-soon";
    statusText = `${days} ${t("daysLeft")}`;
  }

  return `<span class="deadline-display ${statusClass}"><span class="deadline-icon" aria-hidden="true">⏰</span><span><span class="deadline-date">${escapeHtml(formatted)}</span>${statusText ? `<span class="deadline-countdown">${escapeHtml(statusText)}</span>` : ""}</span></span>`;
}

function renderActivityType(opportunity, t) {
  const type = opportunity.activity_type || t("noType");
  const icon = ACTIVITY_TYPE_ICONS[type] || "🤝";
  return `<span class="activity-type-display"><span class="activity-type-icon" aria-hidden="true">${icon}</span><span>${escapeHtml(type)}</span></span>`;
}

function renderRow(opportunity, options) {
  const { archived, newIds, locale, t } = options;
  const id = String(opportunity.id || opportunity.opid || "");
  const image = safeUrl(opportunity.image_url);
  const link = safeUrl(opportunity.url);
  const title = String(opportunity.title || "");
  const location = opportunity.town || opportunity.location || t("noLocation");
  const isNew = !archived && newIds.has(id);

  return `<tr>
    <td class="title-cell">
      <div class="title-main">
        ${image ? `<img class="opportunity-image" src="${escapeHtml(image)}" alt="" loading="lazy" onerror="this.remove()">` : ""}
        ${isNew ? `<span class="new-badge">✨ ${escapeHtml(t("new"))}</span>` : ""}
        <span>${escapeHtml(title)}</span>
      </div>
      ${renderTopics(opportunity.topics)}
    </td>
    <td class="location-cell">
      <div class="location-main">${escapeHtml(location)}</div>
      <div class="location-country">${renderCountry(opportunity, locale)}</div>
    </td>
    <td class="activity-cell">${renderActivityDates(opportunity, locale, t)}</td>
    <td class="deadline-cell">${renderDeadline(opportunity, locale, t)}</td>
    <td class="type-cell">${renderActivityType(opportunity, t)}</td>
    <td class="apply-column">${link ? `<a class="apply-button" href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer">${escapeHtml(t("view"))}</a>` : ""}</td>
  </tr>`;
}

export function renderRows(opportunities, options) {
  return opportunities.map((opportunity) => renderRow(opportunity, options)).join("");
}
