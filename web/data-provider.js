// ESC Opportunity Finder — static backend data provider
//
// GitHub Pages is a static frontend, so the published backend
// dataset is consumed from web/opportunities.json.
//
// The backend scraper remains the source of truth.
// This provider is the browser-side boundary between that
// generated dataset and web/app.js.

window.ESC_DATA_PROVIDER = {
  enabled: true,

  async load() {
    const response = await fetch(
      `https://raw.githubusercontent.com/hhaitam95/esc-opportunity-finder/main/data/opportunities.json?v=${Date.now()}`,
      {
        cache: 'no-store',
      },
    );

    if (!response.ok) {
      throw new Error(
        `Could not load opportunities.json (${response.status})`,
      );
    }

    const payload = await response.json();

    if (!payload || typeof payload !== 'object') {
      throw new Error('Opportunity dataset has an invalid root object.');
    }

    const sourceOpportunities = Array.isArray(payload.opportunities)
      ? payload.opportunities
      : [];

    if (!sourceOpportunities.length) {
      throw new Error('Opportunity dataset contains no opportunities.');
    }

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const recentExpiredCutoff = new Date(today);
    recentExpiredCutoff.setDate(
      recentExpiredCutoff.getDate() - 30,
    );

    const normalizeCode = (value) =>
      String(value || '')
        .trim()
        .toUpperCase();

    const normalizeOpportunity = (opportunity) => {
      const item = { ...opportunity };

      const dates =
        item.activity_dates &&
        typeof item.activity_dates === 'object'
          ? item.activity_dates
          : {};

      item.start_date =
        dates.start ||
        item.start_date ||
        '';

      item.end_date =
        dates.end ||
        item.end_date ||
        '';

      item.deadline =
        item.application_deadline ||
        item.deadline ||
        '';

      item.image_url =
        item.logo_url ||
        item.image_url ||
        '';

      item.town =
        item.town ||
        item.city ||
        '';

      const participantCountries =
        Array.isArray(item.participant_countries)
          ? item.participant_countries
          : Array.isArray(item.eligible_countries)
            ? item.eligible_countries
            : [];

      item.participant_countries = [
        ...new Set(
          participantCountries
            .map(normalizeCode)
            .filter(Boolean),
        ),
      ];

      item.eligible_countries = [
        ...new Set(
          (Array.isArray(item.eligible_countries)
            ? item.eligible_countries
            : item.participant_countries
          )
            .map(normalizeCode)
            .filter(Boolean),
        ),
      ];

      return item;
    };

    const normalized = sourceOpportunities
      .filter(
        (item) => item && typeof item === 'object',
      )
      .map(normalizeOpportunity);

    const activeOpportunities = [];
    const recentlyExpired = [];

    normalized.forEach((opportunity) => {
      const deadline = String(opportunity.deadline || '').trim();

      if (!deadline) {
        activeOpportunities.push(opportunity);
        return;
      }

      const deadlineDate = new Date(`${deadline}T23:59:59`);

      if (Number.isNaN(deadlineDate.getTime())) {
        activeOpportunities.push(opportunity);
        return;
      }

      if (deadlineDate >= today) {
        activeOpportunities.push(opportunity);
        return;
      }

      if (deadlineDate >= recentExpiredCutoff) {
        recentlyExpired.push(opportunity);
      }
    });

    const participantCountryIndex = {};

    activeOpportunities.forEach((opportunity) => {
      const opportunityId = String(
        opportunity.id ?? opportunity.opid ?? '',
      );

      opportunity.participant_countries.forEach((code) => {
        if (!participantCountryIndex[code]) {
          participantCountryIndex[code] = [];
        }

        participantCountryIndex[code].push(opportunityId);
      });
    });

    Object.keys(participantCountryIndex).forEach((code) => {
      participantCountryIndex[code] = [
        ...new Set(participantCountryIndex[code]),
      ];
    });

    const activeData = {
      ...payload,
      opportunities: activeOpportunities,
      count: activeOpportunities.length,
    };

    const expiredData = {
      ...payload,
      opportunities: recentlyExpired,
      count: recentlyExpired.length,
    };

    return {
      activeData,
      expiredData,
      participantCountryIndex,
    };
  },
};
