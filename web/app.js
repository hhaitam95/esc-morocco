// Complete participant-country list exposed // by the ESC API.
// The backend currently has cached opportunity // data only for Morocco.
const ESC_PARTICIPANT_COUNTRIES = [
  { name: "Albania", flag: "🇦🇱" },
  { name: "Algeria", flag: "🇩🇿" },
  { name: "Armenia", flag: "🇦🇲" },
  { name: "Aruba", flag: "🇦🇼" },
  { name: "Austria", flag: "🇦🇹" },
  { name: "Azerbaijan", flag: "🇦🇿" },
  { name: "Belarus", flag: "🇧🇾" },
  { name: "Belgium", flag: "🇧🇪" },
  { name: "Bonaire Sint Eustatius and Saba", flag: "🇧🇶" },
  { name: "Bosnia and Herzegovina", flag: "🇧🇦" },
  { name: "Bulgaria", flag: "🇧🇬" },
  { name: "Croatia", flag: "🇭🇷" },
  { name: "Curaçao", flag: "🇨🇼" },
  { name: "Cyprus", flag: "🇨🇾" },
  { name: "Czechia", flag: "🇨🇿" },
  { name: "Denmark", flag: "🇩🇰" },
  { name: "Egypt", flag: "🇪🇬" },
  { name: "Estonia", flag: "🇪🇪" },
  { name: "Finland", flag: "🇫🇮" },
  { name: "France", flag: "🇫🇷" },
  { name: "French Polynesia", flag: "🇵🇫" },
  { name: "French Southern and Antarctic Territories", flag: "🇹🇫" },
  { name: "Georgia", flag: "🇬🇪" },
  { name: "Germany", flag: "🇩🇪" },
  { name: "Greece", flag: "🇬🇷" },
  { name: "Greenland", flag: "🇬🇱" },
  { name: "Hungary", flag: "🇭🇺" },
  { name: "Iceland", flag: "🇮🇸" },
  { name: "Ireland", flag: "🇮🇪" },
  { name: "Israel", flag: "🇮🇱" },
  { name: "Italy", flag: "🇮🇹" },
  { name: "Jordan", flag: "🇯🇴" },
  { name: "Kosovo * UN resolution", flag: "🇽🇰" },
  { name: "Latvia", flag: "🇱🇻" },
  { name: "Lebanon", flag: "🇱🇧" },
  { name: "Libya", flag: "🇱🇾" },
  { name: "Liechtenstein", flag: "🇱🇮" },
  { name: "Lithuania", flag: "🇱🇹" },
  { name: "Luxembourg", flag: "🇱🇺" },
  { name: "Malta", flag: "🇲🇹" },
  { name: "Moldova", flag: "🇲🇩" },
  { name: "Montenegro", flag: "🇲🇪" },
  { name: "Morocco", flag: "🇲🇦" },
  { name: "Netherlands", flag: "🇳🇱" },
  { name: "New Caledonia", flag: "🇳🇨" },
  { name: "North Macedonia", flag: "🇲🇰" },
  { name: "Norway", flag: "🇳🇴" },
  { name: "Palestine", flag: "🇵🇸" },
  { name: "Poland", flag: "🇵🇱" },
  { name: "Portugal", flag: "🇵🇹" },
  { name: "Romania", flag: "🇷🇴" },
  { name: "Russia", flag: "🇷🇺" },
  { name: "Saint Barthélemy", flag: "🇧🇱" },
  { name: "Serbia", flag: "🇷🇸" },
  { name: "Sint Maarten (dutch part)", flag: "🇸🇽" },
  { name: "Slovakia", flag: "🇸🇰" },
  { name: "Slovenia", flag: "🇸🇮" },
  { name: "Spain", flag: "🇪🇸" },
  { name: "St Pierre and Miquelon", flag: "🇵🇲" },
  { name: "Sweden", flag: "🇸🇪" },
  { name: "Syria", flag: "🇸🇾" },
  { name: "Tunisia", flag: "🇹🇳" },
  { name: "Türkiye", flag: "🇹🇷" },
  { name: "Ukraine", flag: "🇺🇦" },
  { name: "Wallis and Futuna", flag: "🇼🇫" },
];

// ============================================================
// ESC MOROCCO OPPORTUNITIES
// Frontend logic
// ============================================================

const DATA_URL = "opportunities.json";
const EXPIRED_DATA_URL = "expired.json";
const PARTICIPANT_COUNTRY_INDEX_URL = "participant_country_index.json";

// ============================================================
// STATE
// ============================================================

let activeOpportunities = [];
let expiredOpportunities = [];
let currentLanguage = 'en';
let currentActiveData = null;
let participantCountryIndex = null;

// ============================================================
// DOM ELEMENTS
// ============================================================

const opportunityCount = document.getElementById("opportunity-count");

const lastUpdated = document.getElementById("last-updated");

const activeResultCount = document.getElementById("active-result-count");

const opportunitiesBody = document.getElementById("opportunities-body");

const expiredBody = document.getElementById("expired-body");

const expiredSection = document.getElementById("expired-section");

const expiredContent = document.getElementById("expired-content");

const expiredCount = document.getElementById("expired-count");

const expiredArrow = document.getElementById("expired-arrow");

const loadingMessage = document.getElementById("loading-message");

const errorMessage = document.getElementById("error-message");

const emptyMessage = document.getElementById("empty-message");

const searchInput = document.getElementById("search-input");

const countryFilter = document.getElementById("country-filter");

const typeFilter = document.getElementById("type-filter");

const sortSelect = document.getElementById("sort-select");

const refreshButton = document.getElementById("refresh-button");

// ============================================================
// TRANSLATIONS
// ============================================================

const translations = {
  en: {
    participantCountry: "Participant Country",
    selectParticipantCountry: "Select Participant Country",
    apply: "Search",
    allParticipantCountries: "All participant countries",
    title: "ESC Opportunity Finder",
    subtitle: "Find European Solidarity Corps volunteering opportunities open to participants from your country",
    activeOpportunities: "Active opportunities",

    lastUpdated: "Last updated",

    intro:
      "Find active European Solidarity Corps volunteering opportunities open to participants from your country.",
    introNote:
      "The list is automatically refreshed from the European Youth Portal.",

    search: "Search",

    searchPlaceholder: "Search opportunities...",

    country: "Country",

    allCountries: "All countries",

    type: "Type",

    allTypes: "All types",

    sortBy: "Sort by",

    sortDeadline: "Application deadline",

    sortStart: "Activity start date",

    sortCreated: "Recently added",

    refresh: "Refresh",

    loading: "Loading opportunities...",

    errorTitle: "We couldn't load the opportunities.",

    errorText: "Please try again later.",

    availableNow: "Available now",

    opportunity: "Opportunity",

    location: "Location",

    activity: "Activity",

    deadline: "Deadline",

    expired: "Expired",

    noResultsTitle: "No opportunities found.",

    noResultsText: "Try changing your search or filters.",

    recentlyExpired: "Recently expired",

    source: "Data sourced from",

    footerNote: "Always check the official opportunity page before applying.",

    view: "View",

    new: "NEW",

    noDeadline: "No deadline",

    deadlineToday: "Deadline today",

    dayLeft: "day left",

    daysLeft: "days left",

    hour: "hour",

    hourLeft: "hour left",

    hoursLeft: "hours left",

    expiredToday: "Expired today",

    expiredAgo: "days ago",

    noLocation: "Location unavailable",

    noDates: "Dates unavailable",

    noType: "Not specified",

    results: "results",

    result: "result",

     lightMode: "Light mode",

     darkMode: "Dark mode",

},
  fr: {
    participantCountry: "Pays du participant",
    selectParticipantCountry: "Sélectionnez le pays du participant",
    apply: "Rechercher",
    allParticipantCountries: "Tous les pays participants",
    title: "Outil de recherche d’opportunités du CES",
    subtitle: "Trouvez des opportunités de volontariat du Corps européen de solidarité ouvertes aux participants de votre pays",
    activeOpportunities: "Opportunités actives",

    lastUpdated: "Dernière mise à jour",

    intro:
      "Voici les opportunités de volontariat actives du Corps européen de solidarité ouvertes aux participants de votre pays.",
    introNote:
      "La liste est automatiquement actualisée depuis le Portail européen de la jeunesse.",

    search: "Rechercher",

    searchPlaceholder: "Rechercher une opportunité...",

    country: "Pays",

    allCountries: "Tous les pays",

    type: "Type",

    allTypes: "Tous les types",

    sortBy: "Trier par",

    sortDeadline: "Date limite de candidature",

    sortStart: "Date de début",

    sortCreated: "Ajoutées récemment",

    refresh: "Actualiser",

    loading: "Chargement des opportunités...",

    errorTitle: "Impossible de charger les opportunités.",

    errorText: "Veuillez réessayer plus tard.",

    availableNow: "Disponibles actuellement",

    opportunity: "Opportunité",

    location: "Lieu",

    activity: "Activité",

    deadline: "Date limite",

    expired: "Expirée",

    noResultsTitle: "Aucune opportunité trouvée.",

    noResultsText: "Essayez de modifier votre recherche ou vos filtres.",

    recentlyExpired: "Récemment expirées",

    source: "Données provenant du",

    footerNote:
      "Consultez toujours la page officielle de l'opportunité avant de postuler.",

    view: "Voir",

    new: "NOUVEAU",

    noDeadline: "Aucune date limite",

    deadlineToday: "Date limite aujourd'hui",

    dayLeft: "jour restant",

    daysLeft: "jours restants",

    hour: "heure",

    hourLeft: "heure restante",

    hoursLeft: "heures restantes",

    expiredToday: "Expirée aujourd'hui",

    expiredAgo: "jours",

    noLocation: "Lieu indisponible",

    noDates: "Dates indisponibles",

    noType: "Non précisé",

    results: "résultats",

    result: "résultat",

     lightMode: "Mode clair",

     darkMode: "Mode sombre",

},
  ar: {
    participantCountry: "بلد المشارك",
    selectParticipantCountry: "اختر بلد المشارك",
    apply: "بحث",
    allParticipantCountries: "جميع بلدان المشاركين",
    title: "البحث عن فرص الفيلق الأوروبي للتضامن",
    subtitle: "ابحث عن فرص التطوع ضمن الفيلق الأوروبي للتضامن المفتوحة للمشاركين من بلدك",
    activeOpportunities: "الفرص المتاحة",

    lastUpdated: "آخر تحديث",

    intro:
      "هذه هي فرص التطوع النشطة ضمن الفيلق الأوروبي للتضامن المفتوحة للمشاركين من بلدك.",
    introNote: "يتم تحديث القائمة تلقائياً من بوابة الشباب الأوروبية.",

    search: "بحث",

    searchPlaceholder: "ابحث عن فرصة...",

    country: "الدولة",

    allCountries: "جميع الدول",

    type: "النوع",

    allTypes: "جميع الأنواع",

    sortBy: "ترتيب حسب",

    sortDeadline: "آخر موعد للتقديم",

    sortStart: "تاريخ بداية النشاط",

    sortCreated: "الأحدث",

    refresh: "تحديث",

    loading: "جارٍ تحميل الفرص...",

    errorTitle: "تعذر تحميل الفرص.",

    errorText: "يرجى المحاولة مرة أخرى لاحقاً.",

    availableNow: "الفرص المتاحة الآن",

    opportunity: "الفرصة",

    location: "الموقع",

    activity: "النشاط",

    deadline: "الموعد النهائي",

    expired: "منتهية",

    noResultsTitle: "لم يتم العثور على فرص.",

    noResultsText: "حاول تغيير البحث أو عوامل التصفية.",

    recentlyExpired: "الفرص المنتهية مؤخراً",

    source: "البيانات من",

    footerNote: "تحقق دائماً من صفحة الفرصة الرسمية قبل التقديم.",

    view: "عرض",

    new: "جديد",

    noDeadline: "لا يوجد موعد نهائي",

    deadlineToday: "الموعد النهائي اليوم",

    dayLeft: "يوم متبقٍ",

    daysLeft: "أيام متبقية",

    hour: "ساعة",

    hourLeft: "ساعة متبقية",

    hoursLeft: "ساعات متبقية",

    expiredToday: "انتهت اليوم",

    expiredAgo: "يوماً مضت",

    noLocation: "الموقع غير متوفر",

    noDates: "التواريخ غير متوفرة",

    noType: "غير محدد",

    results: "نتائج",

    result: "نتيجة",

     lightMode: "الوضع الفاتح",

     darkMode: "الوضع الداكن",

},

};

// ============================================================
// TRANSLATION HELPERS
// ============================================================

function t(key) {
  return translations[currentLanguage]?.[key] ?? translations.en[key] ?? key;
}

function applyTranslations() {
  document.documentElement.lang = currentLanguage;

  document.documentElement.dir =
    currentLanguage === "ar"
      ? "rtl"
      : "ltr";

  document
    .querySelectorAll("[data-i18n]")
    .forEach((element) => {
      const key = element.dataset.i18n;

      element.textContent = t(key);
    });

  document
    .querySelectorAll("[data-i18n-placeholder]")
    .forEach((element) => {
      const key =
        element.dataset.i18nPlaceholder;

      element.placeholder = t(key);
    });

  populateFilters();

  if (currentActiveData) {
    populateParticipantCountries(currentActiveData);
  }

  if (participantSearchApplied) {
    // Preserve the participant-country zero-result/error state
    // when switching languages.
    opportunityCount.textContent =
      `0 ${t("results")}`;

    activeResultCount.textContent =
      `0 ${t("results")}`;

    lastUpdated.textContent = "—";

    opportunitiesBody.innerHTML = "";

    emptyMessage.classList.add("hidden");
    errorMessage.classList.remove("hidden");
  } else {
    renderActive();

    if (currentActiveData) {
      updateHeader(currentActiveData);
    }
  }

  renderExpired();

  updateLanguageDropdown();

  updateThemeToggleLabel();
}


// ============================================================
// LANGUAGE SWITCHING
// ============================================================

const languageDropdownToggle =
  document.getElementById(
    "language-dropdown-toggle",
  );

const languageDropdownMenu =
  document.getElementById(
    "language-dropdown-menu",
  );

const languageDropdownFlag =
  document.getElementById(
    "language-dropdown-flag",
  );

const languageDropdownLabel =
  document.getElementById(
    "language-dropdown-label",
  );

const languageFlags = {
  en: "🇬🇧",
  fr: "🇫🇷",
  ar: "🇸🇦",
};

const languageNames = {
  en: "English",
  fr: "Français",
  ar: "العربية",
};

const languageShortNames = {
  en: "EN",
  fr: "FR",
  ar: "AR",
};

function updateLanguageDropdown() {
  if (
    !languageDropdownToggle ||
    !languageDropdownFlag ||
    !languageDropdownLabel
  ) {
    return;
  }

  const language =
    languageNames[currentLanguage]
      ? currentLanguage
      : "en";

  languageDropdownFlag.textContent =
    languageFlags[language];

  languageDropdownLabel.textContent =
    languageShortNames[language];

  languageDropdownToggle.setAttribute(
    "title",
    languageNames[language],
  );

  languageDropdownToggle.setAttribute(
    "aria-label",
    languageNames[language],
  );

  document
    .querySelectorAll(".language-option")
    .forEach((button) => {
      const active =
        button.dataset.language === language;

      button.classList.toggle(
        "active",
        active,
      );

      if (active) {
        button.setAttribute(
          "aria-current",
          "true",
        );
      } else {
        button.removeAttribute(
          "aria-current",
        );
      }
    });
}

function closeLanguageDropdown() {
  if (
    !languageDropdownToggle ||
    !languageDropdownMenu
  ) {
    return;
  }

  languageDropdownMenu.hidden = true;

  languageDropdownToggle.setAttribute(
    "aria-expanded",
    "false",
  );
}

function openLanguageDropdown() {
  if (
    !languageDropdownToggle ||
    !languageDropdownMenu
  ) {
    return;
  }

  languageDropdownMenu.hidden = false;

  languageDropdownToggle.setAttribute(
    "aria-expanded",
    "true",
  );
}

if (
  languageDropdownToggle &&
  languageDropdownMenu
) {
  languageDropdownToggle.addEventListener(
    "click",
    (event) => {
      event.stopPropagation();

      if (languageDropdownMenu.hidden) {
        openLanguageDropdown();
      } else {
        closeLanguageDropdown();
      }
    },
  );

  document
    .querySelectorAll(".language-option")
    .forEach((button) => {
      button.addEventListener(
        "click",
        (event) => {
          event.stopPropagation();

          const language =
            button.dataset.language;

          if (
            !language ||
            !translations[language]
          ) {
            return;
          }

          currentLanguage =
            language;

          localStorage.setItem(
            "esc_language",
            currentLanguage,
          );

          applyTranslations();

          closeLanguageDropdown();
        },
      );
    });

  document.addEventListener(
    "click",
    (event) => {
      if (
        !event.target.closest(
          ".language-dropdown",
        )
      ) {
        closeLanguageDropdown();
      }
    },
  );

  document.addEventListener(
    "keydown",
    (event) => {
      if (event.key === "Escape") {
        closeLanguageDropdown();
      }
    },
  );
}

const savedLanguage =
  localStorage.getItem(
    "esc_language",
  );

if (
  savedLanguage &&
  translations[savedLanguage]
) {
  currentLanguage =
    savedLanguage;
}

updateLanguageDropdown();

// ============================================================
// DARK MODE
// ============================================================

const themeToggle =
  document.getElementById("theme-toggle");

const themeIcon =
  document.getElementById("theme-icon");

function updateThemeToggleLabel() {
  if (!themeToggle || !themeIcon) {
    return;
  }

  const isDark =
    document.documentElement.dataset.theme === "dark";

  themeIcon.textContent =
    isDark
      ? "☀️"
      : "🌙";

  const label =
    isDark
      ? t("lightMode")
      : t("darkMode");

  themeToggle.setAttribute(
    "aria-label",
    label,
  );

  themeToggle.setAttribute(
    "title",
    label,
  );
}

function applyTheme(theme) {
  const normalizedTheme =
    theme === "dark"
      ? "dark"
      : "light";

  document.documentElement.dataset.theme =
    normalizedTheme;

  localStorage.setItem(
    "esc_theme",
    normalizedTheme,
  );

  updateThemeToggleLabel();
}

if (themeToggle) {
  themeToggle.addEventListener(
    "click",
    () => {
      const current =
        document.documentElement.dataset.theme === "dark"
          ? "dark"
          : "light";

      applyTheme(
        current === "dark"
          ? "light"
          : "dark",
      );
    },
  );

  updateThemeToggleLabel();
}

// ============================================================
// DATE HELPERS
// ============================================================

function parseDate(value) {
  if (!value) {
    return null;
  }

  const date = new Date(`${value}T00:00:00`);

  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return date;
}

function parseDateTime(value) {
  if (!value) {
    return null;
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return date;
}

function formatDate(value) {
  const date = parseDate(value);

  if (!date) {
    return t("noDeadline");
  }

  return new Intl.DateTimeFormat(
    currentLanguage === "ar"
      ? "ar-MA"
      : currentLanguage === "fr"
        ? "fr-FR"
        : "en-GB",
    {
      day: "2-digit",
      month: "short",
      year: "numeric",
    },
  ).format(date);
}

function calculateActivityDuration(start, end) {
  const startDate = parseDate(start);

  const endDate = parseDate(end);

  if (!startDate || !endDate || endDate < startDate) {
    return null;
  }

  let months =
    (endDate.getFullYear() - startDate.getFullYear()) * 12 +
    (endDate.getMonth() - startDate.getMonth());

  let anchor = new Date(startDate);

  anchor.setMonth(anchor.getMonth() + months);

  if (anchor > endDate) {
    months--;

    anchor = new Date(startDate);

    anchor.setMonth(anchor.getMonth() + months);
  }

  const remainingDays = Math.floor(
    (endDate.getTime() - anchor.getTime()) / (1000 * 60 * 60 * 24),
  );

  return {
    months,
    days: remainingDays,
  };
}

function formatActivityDuration(start, end) {
  const duration = calculateActivityDuration(start, end);

  if (!duration) {
    return "";
  }

  const months = duration.months;

  const days = duration.days;

  if (months === 0 && days === 0) {
    return currentLanguage === "fr"
      ? "1 jour"
      : currentLanguage === "ar"
        ? "يوم واحد"
        : "1 day";
  }

  if (currentLanguage === "fr") {
    const parts = [];

    if (months > 0) {
      parts.push(`${months} ` + (months === 1 ? "mois" : "mois"));
    }

    if (days > 0) {
      parts.push(`${days} ` + (days === 1 ? "jour" : "jours"));
    }

    return parts.join(" ");
  }

  if (currentLanguage === "ar") {
    const parts = [];

    if (months > 0) {
      parts.push(months === 1 ? "شهر واحد" : `${months} أشهر`);
    }

    if (days > 0) {
      parts.push(days === 1 ? "يوم واحد" : `${days} أيام`);
    }

    return parts.join(" و ");
  }

  const parts = [];

  if (months > 0) {
    parts.push(`${months} ` + (months === 1 ? "month" : "months"));
  }

  if (days > 0) {
    parts.push(`${days} ` + (days === 1 ? "day" : "days"));
  }

  return parts.join(" ");
}

function formatActivityDates(start, end) {
  if (!start && !end) {
    return `
            <span class="activity-dates">
                ${escapeHtml(t("noDates"))}
            </span>
        `;
  }

  let datesHtml = "";

  if (!start) {
    datesHtml = `
            <span class="activity-dates">
                → ${escapeHtml(formatDate(end))}
            </span>
        `;
  } else if (!end) {
    datesHtml = `
            <span class="activity-dates">
                ${escapeHtml(formatDate(start))} →
            </span>
        `;
  } else {
    datesHtml = `
            <span class="activity-dates">
                ${escapeHtml(formatDate(start))}
                →
                ${escapeHtml(formatDate(end))}
            </span>
        `;
  }

  const duration = formatActivityDuration(start, end);

  if (!duration) {
    return datesHtml;
  }

  return `
        ${datesHtml}

        <span class="activity-duration">
            📅
            ${escapeHtml(duration)}
        </span>
    `;
}

function startOfToday() {
  const date = new Date();

  date.setHours(0, 0, 0, 0);

  return date;
}

function daysFromToday(value) {
  const date = parseDate(value);

  if (!date) {
    return null;
  }

  const difference = date.getTime() - startOfToday().getTime();

  return Math.ceil(difference / (1000 * 60 * 60 * 24));
}

function hoursFromNow(value) {
  const date = parseDate(value);

  if (!date) {
    return null;
  }

  // Assume deadline is at 12:00 (noon) on the given date
  // This is a reasonable default since we only have dates, not times
  date.setHours(12, 0, 0, 0);

  const now = new Date();

  const difference = date.getTime() - now.getTime();

  return Math.ceil(difference / (1000 * 60 * 60));
}

function deadlineClass(deadline) {
  const days = daysFromToday(deadline);

  if (days === null) {
    return "deadline-none";
  }

  if (days <= 3) {
    return "deadline-urgent";
  }

  if (days <= 7) {
    return "deadline-soon";
  }

  return "deadline-normal";
}

function deadlineRelative(deadline) {
  const days = daysFromToday(deadline);

  if (days === null) {
    return "";
  }

  if (days < 0) {
    return "";
  }

  // Check if less than 24 hours remaining (today or tomorrow with early deadline)
  if (days === 0 || days === 1) {
    const hours = hoursFromNow(deadline);

    if (hours === null || hours < 0) {
      return "";
    }

    // Show hourly countdown only if less than 24 hours remain
    if (hours <= 24) {
      if (hours === 0) {
        return `⏰ ${t("deadlineToday")}`;
      }

      if (hours === 1) {
        return `⏰ 1 ${t("hourLeft")}`;
      }

      return `⏰ ${hours} ${t("hoursLeft")}`;
    }
  }

  if (days === 1) {
    return `⏰ 1 ${t("dayLeft")}`;
  }

  if (days > 1 && days <= 30) {
    return `⏰ ${days} ${t("daysLeft")}`;
  }

  return "";
}

function daysSince(value) {
  const date = parseDate(value);

  if (!date) {
    return null;
  }

  const difference = startOfToday().getTime() - date.getTime();

  return Math.max(0, Math.floor(difference / (1000 * 60 * 60 * 24)));
}

function expiredRelative(deadline) {
  const days = daysSince(deadline);

  if (days === null) {
    return "";
  }

  if (days === 0) {
    return t("expiredToday");
  }

  return `${days} ${t("expiredAgo")}`;
}

// ============================================================
// HTML ESCAPING
// ============================================================

function escapeHtml(value) {
  if (value === null || value === undefined) {
    return "";
  }

  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

// ============================================================
// NEW OPPORTUNITIES
// ============================================================

const SEEN_OPPORTUNITIES_KEY = "esc_seen_opportunities";

let newOpportunityIds = new Set();

function loadSeenOpportunities() {
  try {
    const stored = localStorage.getItem(SEEN_OPPORTUNITIES_KEY);

    if (!stored) {
      return null;
    }

    const parsed = JSON.parse(stored);

    if (!Array.isArray(parsed)) {
      return null;
    }

    return new Set(parsed.map((id) => String(id)));
  } catch {
    return null;
  }
}

function saveSeenOpportunities(opportunities) {
  try {
    const ids = opportunities.map((opportunity) => String(opportunity.id));

    localStorage.setItem(SEEN_OPPORTUNITIES_KEY, JSON.stringify(ids));
  } catch {
    // Ignore localStorage failures.
  }
}

function calculateNewOpportunities(opportunities) {
  const previousIds = loadSeenOpportunities();

  /*
   * First visit:
   *
   * There is no previous dataset, so we cannot know
   * which opportunities are genuinely new.
   *
   * Remember the current dataset but show NO NEW badges.
   */

  if (!previousIds) {
    saveSeenOpportunities(opportunities);

    newOpportunityIds = new Set();

    return;
  }

  /*
   * Every opportunity currently visible that wasn't present
   * in the previous dataset is genuinely new.
   */

  newOpportunityIds = new Set(
    opportunities
      .map((opportunity) => String(opportunity.id))
      .filter((id) => !previousIds.has(id)),
  );

  /*
   * Save the current dataset so the next refresh compares
   * against this one.
   */

  saveSeenOpportunities(opportunities);
}

// ============================================================
// COUNTRY NAMES
// ============================================================

const countryNames = new Intl.DisplayNames(["en"], {
  type: "region",
});

const countryCodeOverrides = {
  EL: "GR",

  UK: "GB",
};

function normalizeCountryCode(code) {
  if (!code) {
    return "";
  }

  return countryCodeOverrides[code] || code;
}

function getCountryName(code) {
  if (!code) {
    return "";
  }

  const normalizedCode = normalizeCountryCode(code);

  try {
    return countryNames.of(normalizedCode) || code;
  } catch {
    return code;
  }
}

function getCountryFlag(code) {
  const normalizedCode = normalizeCountryCode(code);

  if (!normalizedCode || normalizedCode.length !== 2) {
    return "🌍";
  }

  const upper = normalizedCode.toUpperCase();

  return String.fromCodePoint(
    ...[...upper].map((char) => 127397 + char.charCodeAt(0)),
  );
}

function renderCountry(code) {
  const name = getCountryName(code);

  if (!name) {
    return "";
  }

  const flag = getCountryFlag(code);

  return `
        <span class="country-display">

            <span
                class="country-flag"
                aria-hidden="true"
            >
                ${flag}
            </span>

            <span>
                ${escapeHtml(name)}
            </span>

        </span>
    `;
}

// ============================================================
// ACTIVITY TYPE ICONS
// ============================================================

const activityTypeIcons = {
  "Individual volunteering": "👤",

  "Volunteering teams": "👥",
};

function renderActivityType(type) {
  if (!type) {
    return `
            <span class="type-label">

                <span
                    class="type-icon"
                    aria-hidden="true"
                >
                    🤝
                </span>

                <span>
                    ${escapeHtml(t("noType"))}
                </span>

            </span>
        `;
  }

  const icon = activityTypeIcons[type] || "🤝";

  return `
        <span
            class="type-label"
            title="${escapeHtml(type)}"
        >

            <span
                class="type-icon"
                aria-hidden="true"
            >
                ${icon}
            </span>

            <span>
                ${escapeHtml(type)}
            </span>

        </span>
    `;
}

// ============================================================
// TOPIC ICONS
// ============================================================

const topicIcons = {
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

function renderTopics(topics) {
  if (!Array.isArray(topics) || topics.length === 0) {
    return "";
  }

  return `
        <div class="topic-tags">

            ${topics
              .map((topic) => {
                const icon = topicIcons[topic] || "•";

                return `
                            <span
                                class="topic-tag"
                                title="${escapeHtml(topic)}"
                            >

                                <span
                                    class="topic-icon"
                                    aria-hidden="true"
                                >
                                    ${icon}
                                </span>

                                <span>
                                    ${escapeHtml(topic)}
                                </span>

                            </span>
                        `;
              })
              .join("")}

        </div>
    `;
}


// ============================================================
// PARTICIPANT COUNTRY FILTER
// ============================================================

const PARTICIPANT_COUNTRY_STORAGE_KEY =
  "esc_participant_country";

const participantCountryFilter =
  document.getElementById(
    "participant-country",
  );

const applyParticipantCountryButton =
  document.getElementById(
    "apply-participant-country",
  );

let selectedParticipantCountry = "";
let participantCountryDraft = "";
let participantSearchApplied = false;

function normalizeParticipantCountry(value) {
  return String(value || "")
    .trim()
    .replace(/\s+/g, " ")
    .toLocaleLowerCase();
}

function getParticipantCountryCode(name) {
  const normalizedName =
    normalizeParticipantCountry(name);

  const country =
    ESC_PARTICIPANT_COUNTRIES.find(
      (item) =>
        normalizeParticipantCountry(
          item.name,
        ) === normalizedName,
    );

  if (!country) {
    return "";
  }

  const regionalIndicators =
    [...country.flag]
      .map((character) =>
        character.codePointAt(0),
      )
      .filter(
        (codePoint) =>
          codePoint >= 0x1f1e6 &&
          codePoint <= 0x1f1ff,
      );

  if (
    regionalIndicators.length !== 2
  ) {
    return "";
  }

  return regionalIndicators
    .map(
      (codePoint) =>
        String.fromCharCode(
          codePoint - 0x1f1e6 + 65,
        ),
    )
    .join("");
}

function getParticipantCountryOpportunityIds() {
  if (!selectedParticipantCountry) {
    return null;
  }

  if (
    !participantCountryIndex ||
    typeof participantCountryIndex.countries !==
      "object"
  ) {
    return new Set();
  }

  const countryCode =
    getParticipantCountryCode(
      selectedParticipantCountry,
    );

  if (!countryCode) {
    return new Set();
  }

  const ids =
    participantCountryIndex.countries[
      countryCode
    ];

  if (!Array.isArray(ids)) {
    return new Set();
  }

  return new Set(
    ids.map((id) =>
      String(id),
    ),
  );
}

async function ensureParticipantCountryIndex() {
  if (
    participantCountryIndex &&
    typeof participantCountryIndex.countries ===
      "object"
  ) {
    return participantCountryIndex;
  }

  const data = await fetchJson(
    PARTICIPANT_COUNTRY_INDEX_URL,
  );

  if (
    !data ||
    typeof data !== "object" ||
    !data.countries ||
    typeof data.countries !== "object"
  ) {
    throw new Error(
      "Participant-country index has an invalid structure.",
    );
  }

  participantCountryIndex = data;

  return participantCountryIndex;
}


function getTranslatedCountryName(code, fallback) {
  const translations = {
    fr: {
      AL: "Albanie",
      DZ: "Algérie",
      AM: "Arménie",
      AW: "Aruba",
      AT: "Autriche",
      AZ: "Azerbaïdjan",
      BY: "Biélorussie",
      BE: "Belgique",
      BA: "Bosnie-Herzégovine",
      BG: "Bulgarie",
      HR: "Croatie",
      CY: "Chypre",
      CZ: "Tchéquie",
      DK: "Danemark",
      EG: "Égypte",
      EE: "Estonie",
      FI: "Finlande",
      FR: "France",
      GE: "Géorgie",
      DE: "Allemagne",
      GR: "Grèce",
      HU: "Hongrie",
      IS: "Islande",
      IE: "Irlande",
      IL: "Israël",
      IT: "Italie",
      JO: "Jordanie",
      LV: "Lettonie",
      LB: "Liban",
      LY: "Libye",
      LI: "Liechtenstein",
      LT: "Lituanie",
      LU: "Luxembourg",
      MT: "Malte",
      MD: "Moldavie",
      ME: "Monténégro",
      MA: "Maroc",
      NL: "Pays-Bas",
      MK: "Macédoine du Nord",
      NO: "Norvège",
      PS: "Palestine",
      PL: "Pologne",
      PT: "Portugal",
      RO: "Roumanie",
      RU: "Russie",
      RS: "Serbie",
      SK: "Slovaquie",
      SI: "Slovénie",
      ES: "Espagne",
      SE: "Suède",
      SY: "Syrie",
      TN: "Tunisie",
      TR: "Türkiye",
      UA: "Ukraine"
    },
    ar: {
      AL: "ألبانيا",
      DZ: "الجزائر",
      AM: "أرمينيا",
      AW: "أروبا",
      AT: "النمسا",
      AZ: "أذربيجان",
      BY: "بيلاروسيا",
      BE: "بلجيكا",
      BA: "البوسنة والهرسك",
      BG: "بلغاريا",
      HR: "كرواتيا",
      CY: "قبرص",
      CZ: "التشيك",
      DK: "الدنمارك",
      EG: "مصر",
      EE: "إستونيا",
      FI: "فنلندا",
      FR: "فرنسا",
      GE: "جورجيا",
      DE: "ألمانيا",
      GR: "اليونان",
      HU: "المجر",
      IS: "آيسلندا",
      IE: "أيرلندا",
      IL: "إسرائيل",
      IT: "إيطاليا",
      JO: "الأردن",
      LV: "لاتفيا",
      LB: "لبنان",
      LY: "ليبيا",
      LI: "ليختنشتاين",
      LT: "ليتوانيا",
      LU: "لوكسمبورغ",
      MT: "مالطا",
      MD: "مولدوفا",
      ME: "الجبل الأسود",
      MA: "المغرب",
      NL: "هولندا",
      MK: "مقدونيا الشمالية",
      NO: "النرويج",
      PS: "فلسطين",
      PL: "بولندا",
      PT: "البرتغال",
      RO: "رومانيا",
      RU: "روسيا",
      RS: "صربيا",
      SK: "سلوفاكيا",
      SI: "سلوفينيا",
      ES: "إسبانيا",
      SE: "السويد",
      SY: "سوريا",
      TN: "تونس",
      TR: "تركيا",
      UA: "أوكرانيا"
    }
  };

  const language = currentLanguage || "en";
  return translations[language]?.[code] || fallback;
}

function populateParticipantCountries() {
  if (!participantCountryFilter) {
    return;
  }

  const currentValue =
    participantCountryFilter.value;

  participantCountryFilter.innerHTML = "";

  const placeholder =
    document.createElement("option");

  placeholder.value = "";
  placeholder.textContent =
    t("selectParticipantCountry");

  participantCountryFilter.appendChild(
    placeholder,
  );

  ESC_PARTICIPANT_COUNTRIES.forEach(
    (country) => {
      const option =
        document.createElement("option");

      option.value =
        country.name;

      option.textContent = getTranslatedCountryName(country.code, country.name);

      participantCountryFilter.appendChild(
        option,
      );
    },
  );

  const exists =
    [...participantCountryFilter.options]
      .some(
        (option) =>
          option.value === currentValue,
      );

  participantCountryFilter.value =
    exists ? currentValue : "";
}

async function applyParticipantCountry() {
  if (!participantCountryFilter) {
    return;
  }

  selectedParticipantCountry =
    participantCountryFilter.value.trim();

  participantCountryDraft =
    selectedParticipantCountry;

  participantSearchApplied =
    Boolean(selectedParticipantCountry);

  if (!participantSearchApplied) {
    resetParticipantSearchDisplay();
    errorMessage.classList.add("hidden");
    return;
  }

  loadingMessage.classList.add("hidden");

  // Participant-country data is not being loaded yet.
  // For every selected participant country, show the requested
  // zero-result state together with the existing error message.
  activeOpportunities = [];
  opportunitiesBody.innerHTML = "";

  opportunityCount.textContent =
    `0 ${t("results")}`;

  activeResultCount.textContent =
    `0 ${t("results")}`;

  lastUpdated.textContent = "—";

  emptyMessage.classList.add("hidden");
  errorMessage.classList.remove("hidden");
}

if (participantCountryFilter) {
  participantCountryFilter.addEventListener(
    "change",
    () => {
      participantCountryDraft =
        participantCountryFilter.value;
    },
  );
}

if (applyParticipantCountryButton) {
  applyParticipantCountryButton.addEventListener(
    "click",
    applyParticipantCountry,
  );
}
// ============================================================
// FILTER OPTIONS
// ============================================================

function uniqueSortedValues(items, property) {
  return [...new Set(items.map((item) => item[property]).filter(Boolean))].sort(
    (a, b) => String(a).localeCompare(String(b)),
  );
}

function populateFilters() {
  const countries = uniqueSortedValues(activeOpportunities, "country");

  const types = uniqueSortedValues(activeOpportunities, "activity_type");

  const selectedCountry = countryFilter.value;

  const selectedType = typeFilter.value;

  countryFilter.innerHTML = `<option value="">
            ${escapeHtml(t("allCountries"))}
        </option>`;

  countries.forEach((code) => {
    const option = document.createElement("option");

    option.value = code;

    option.textContent = `${getCountryFlag(code)} ` + `${getCountryName(code)}`;

    countryFilter.appendChild(option);
  });

  typeFilter.innerHTML = `<option value="">
            ${escapeHtml(t("allTypes"))}
        </option>`;

  types.forEach((type) => {
    const option = document.createElement("option");

    option.value = type;

    option.textContent = `${activityTypeIcons[type] || "🤝"} ` + `${type}`;

    typeFilter.appendChild(option);
  });

  if (countries.includes(selectedCountry)) {
    countryFilter.value = selectedCountry;
  }

  if (types.includes(selectedType)) {
    typeFilter.value = selectedType;
  }
}

// ============================================================
// FILTERING
// ============================================================

function getFilteredActive() {
  const search =
    searchInput.value
      .trim()
      .toLowerCase();

  const country =
    countryFilter.value;

  const type =
    typeFilter.value;

  const participantOpportunityIds =
    getParticipantCountryOpportunityIds();

  return activeOpportunities.filter(
    (opportunity) => {
      const searchable = [
        opportunity.title,
        opportunity.location,
        opportunity.town,
        getCountryName(
          opportunity.country,
        ),
        opportunity.activity_type,
        ...(opportunity.topics || []),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      if (
        search &&
        !searchable.includes(search)
      ) {
        return false;
      }

      if (
        country &&
        opportunity.country !== country
      ) {
        return false;
      }

      if (
        participantOpportunityIds !==
          null &&
        !participantOpportunityIds.has(
          String(opportunity.id),
        )
      ) {
        return false;
      }

      if (
        type &&
        opportunity.activity_type !==
          type
      ) {
        return false;
      }

      return true;
    },
  );
}
// ============================================================
// SORTING
// ============================================================
// ============================================================
// SORTING
// ============================================================
// ============================================================
// SORTING
// ============================================================

function sortOpportunities(items) {
  const sorted = [...items];

  const sortType = sortSelect.value;

  if (sortType === "start") {
    sorted.sort((a, b) => {
      const dateA = parseDate(a.start_date);

      const dateB = parseDate(b.start_date);

      if (!dateA && !dateB) {
        return 0;
      }

      if (!dateA) {
        return 1;
      }

      if (!dateB) {
        return -1;
      }

      return dateA - dateB;
    });

    return sorted;
  }

  if (sortType === "created") {
    sorted.sort((a, b) => {
      const dateA = parseDateTime(a.created);

      const dateB = parseDateTime(b.created);

      if (!dateA && !dateB) {
        return 0;
      }

      if (!dateA) {
        return 1;
      }

      if (!dateB) {
        return -1;
      }

      return dateB - dateA;
    });

    return sorted;
  }

  sorted.sort((a, b) => {
    const dateA = parseDate(a.deadline);

    const dateB = parseDate(b.deadline);

    if (!dateA && !dateB) {
      return a.title.localeCompare(b.title);
    }

    if (!dateA) {
      return 1;
    }

    if (!dateB) {
      return -1;
    }

    return dateA - dateB;
  });

  return sorted;
}


function resetParticipantSearchDisplay() {
  opportunityCount.textContent = "—";
  activeResultCount.textContent = "—";
  lastUpdated.textContent = "—";

  opportunitiesBody.innerHTML = "";
  emptyMessage.classList.add("hidden");
}

function updateHeaderForParticipantSearch() {
  const filtered = sortOpportunities(getFilteredActive());

  const count = filtered.length;

  opportunityCount.textContent =
    count === 1
      ? `1 ${t("result")}`
      : `${count} ${t("results")}`;

  activeResultCount.textContent =
    count === 1
      ? `1 ${t("result")}`
      : `${count} ${t("results")}`;

  if (currentActiveData?.generated_at) {
    const date = parseDateTime(currentActiveData.generated_at);

    if (date) {
      lastUpdated.textContent = new Intl.DateTimeFormat(
        currentLanguage === "ar"
          ? "ar-MA"
          : currentLanguage === "fr"
            ? "fr-FR"
            : "en-GB",
        {
          day: "2-digit",
          month: "short",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        },
      ).format(date);

      return;
    }
  }

  lastUpdated.textContent = "—";
}

// ============================================================
// ACTIVE TABLE
// ============================================================

function renderActive() {
  if (!participantSearchApplied) {
    resetParticipantSearchDisplay();
    return;
  }

  const filtered = sortOpportunities(getFilteredActive());

  opportunityCount.textContent =
    filtered.length === 1
      ? `1 ${t("result")}`
      : `${filtered.length} ${t("results")}`;

  activeResultCount.textContent =
    `${filtered.length} ` +
    (filtered.length === 1 ? t("result") : t("results"));

  if (filtered.length === 0) {
    opportunitiesBody.innerHTML = "";

    emptyMessage.classList.remove("hidden");

    return;
  }

  emptyMessage.classList.add("hidden");

  opportunitiesBody.innerHTML = filtered
    .map((opportunity) => {
      const location =
        opportunity.town || opportunity.location || t("noLocation");

      const deadlineClassName = deadlineClass(opportunity.deadline);

      const relative = deadlineRelative(opportunity.deadline);

      const isNew = newOpportunityIds.has(String(opportunity.id));

      const imageSrc = opportunity.image_url
        ? new URL(
            opportunity.image_url,
            "https://youth.europa.eu",
          ).href
        : "";

      return `
                    <tr>

                        <td class="title-cell">

                            <div class="opportunity-title">

                                ${
                                  imageSrc
                                    ? `
                                            <img
                                                class="opportunity-image"
                                                src="${escapeHtml(imageSrc)}"
                                                alt="${escapeHtml(opportunity.title)}"
                                                loading="lazy"
                                                onerror="this.style.display='none'"
                                            />
                                        `
                                    : ""
                                }

                                ${
                                  isNew
                                    ? `
                                            <span
                                                class="new-badge"
                                            >
                                                ✨
                                                ${escapeHtml(t("new"))}
                                            </span>
                                        `
                                    : ""
                                }

                                <span>
                                    ${escapeHtml(opportunity.title)}
                                </span>

                            </div>


                            ${
                              opportunity.topics?.length
                                ? renderTopics(opportunity.topics)
                                : ""
                            }

                        </td>


                        <td class="location-cell">

                            <div class="location-main">

                                ${escapeHtml(location)}

                            </div>

                            <div class="location-country">

                                ${renderCountry(opportunity.country)}

                            </div>

                        </td>


                        <td class="activity-cell">

${formatActivityDates(opportunity.start_date, opportunity.end_date)}

                        </td>


                        <td class="deadline-cell">

                            <span
                                class="deadline-date ${deadlineClassName}"
                            >

                                ${escapeHtml(
                                  opportunity.deadline
                                    ? formatDate(opportunity.deadline)
                                    : t("noDeadline"),
                                )}

                            </span>


                            ${
                              relative
                                ? `
                                        <span
                                            class="deadline-relative"
                                        >
                                            ${escapeHtml(relative)}
                                        </span>
                                    `
                                : ""
                            }

                        </td>


                        <td class="type-cell">

                            ${renderActivityType(opportunity.activity_type)}

                        </td>


                        <td class="apply-cell">

                            <a
                                class="apply-button"
                                href="${escapeHtml(opportunity.url)}"
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                ${escapeHtml(t("view"))}
                            </a>

                        </td>

                    </tr>
                `;
    })
    .join("");
}

// ============================================================
// EXPIRED TABLE
// ============================================================

function renderExpired() {
  if (!expiredOpportunities.length) {
    expiredSection.classList.add("hidden");

    return;
  }

  expiredSection.classList.remove("hidden");

  expiredCount.textContent = expiredOpportunities.length;

  expiredBody.innerHTML = expiredOpportunities
    .map((opportunity) => {
      const location =
        opportunity.town || opportunity.location || t("noLocation");

      return `
                        <tr>

                            <td>

                                <strong>
                                    ${escapeHtml(opportunity.title)}
                                </strong>

                            </td>


                            <td>

                                <div>
                                    ${escapeHtml(location)}
                                </div>

                                <div
                                    class="location-country"
                                >

                                    ${renderCountry(opportunity.country)}

                                </div>

                            </td>


                            <td>

                                ${escapeHtml(formatDate(opportunity.deadline))}

                            </td>


                            <td>

                                ${escapeHtml(
                                  expiredRelative(opportunity.deadline),
                                )}

                            </td>

                        </tr>
                    `;
    })
    .join("");
}

// ============================================================
// STATUS HEADER
// ============================================================

function updateHeader(data) {
  if (!participantSearchApplied) {
    resetParticipantSearchDisplay();
    return;
  }

  const count = Number.isFinite(data?.count)
    ? data.count
    : activeOpportunities.length;

  opportunityCount.textContent =
    count === 1 ? `1 ${t("result")}` : `${count} ${t("results")}`;

  if (data?.generated_at) {
    const date = parseDateTime(data.generated_at);

    if (date) {
      lastUpdated.textContent = new Intl.DateTimeFormat(
        currentLanguage === "ar"
          ? "ar-MA"
          : currentLanguage === "fr"
            ? "fr-FR"
            : "en-GB",
        {
          day: "2-digit",
          month: "short",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        },
      ).format(date);
    } else {
      lastUpdated.textContent = "—";
    }
  } else {
    lastUpdated.textContent = "—";
  }
}

// ============================================================
// DATA FETCHING
// ============================================================

async function fetchJson(url) {
  const response = await fetch(`${url}?t=${Date.now()}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json();
}

// ============================================================
// LOAD DATA
// ============================================================

async function loadData() {
  loadingMessage.classList.remove(
    "hidden",
  );

  errorMessage.classList.add(
    "hidden",
  );

  try {
    const activeData =
      await fetchJson(DATA_URL);

    if (
      !activeData ||
      !Array.isArray(
        activeData.opportunities,
      )
    ) {
      throw new Error(
        "Published opportunity cache has an invalid structure.",
      );
    }

    currentActiveData =
      activeData;

    activeOpportunities =
      activeData.opportunities;

    /*
     * The participant-country index is intentionally loaded
     * through the single shared loader.
     *
     * loadData() must not fetch PARTICIPANT_COUNTRY_INDEX_URL
     * directly. The index is loaded on demand by
     * ensureParticipantCountryIndex().
     */
    await ensureParticipantCountryIndex();

    calculateNewOpportunities(
      activeOpportunities,
    );

    try {
      const expiredData =
        await fetchJson(
          EXPIRED_DATA_URL,
        );

      expiredOpportunities =
        Array.isArray(
          expiredData?.opportunities,
        )
          ? expiredData.opportunities
          : [];
    } catch {
      expiredOpportunities = [];
    }

    populateFilters();
    populateParticipantCountries();

    resetParticipantSearchDisplay();
    renderExpired();
  } catch (error) {
    console.error(
      "Could not load opportunities:",
      error,
    );

    activeOpportunities = [];
    currentActiveData = null;
    participantCountryIndex = null;

    opportunityCount.textContent = "—";
    activeResultCount.textContent = "—";
    lastUpdated.textContent = "—";

    errorMessage.classList.remove(
      "hidden",
    );
  } finally {
    loadingMessage.classList.add(
      "hidden",
    );
  }
}

// ============================================================
// REFRESH BUTTON
// ============================================================
// ============================================================
// REFRESH BUTTON
// ============================================================

refreshButton.addEventListener("click", async () => {
  refreshButton.disabled = true;

  refreshButton.innerHTML = `↻ <span>${escapeHtml(t("loading"))}</span>`;

  try {
    await loadData();
  } finally {
    refreshButton.disabled = false;

    refreshButton.innerHTML = `↻ <span>${escapeHtml(t("refresh"))}</span>`;
  }
});

// ============================================================
// FILTER EVENTS
// ============================================================

searchInput.addEventListener("input", renderActive);

countryFilter.addEventListener("change", renderActive);

typeFilter.addEventListener("change", renderActive);

sortSelect.addEventListener("change", renderActive);

// ============================================================
// EXPIRED TOGGLE
// ============================================================

document.getElementById("expired-toggle").addEventListener("click", () => {
  const isHidden = expiredContent.classList.contains("hidden");

  expiredContent.classList.toggle("hidden");

  expiredArrow.classList.toggle("open", isHidden);
});

// ============================================================
// COUNTDOWN REFRESH
// ============================================================

function startCountdownRefresh() {
  // Refresh the countdown display every minute to keep it current
  setInterval(() => {
    // Only re-render active opportunities if they exist
    // This updates the deadline-relative display (hourly countdown)
    if (activeOpportunities.length > 0) {
      renderActive();
    }
  }, 60000); // 60000 ms = 1 minute
}

// ============================================================
// INITIAL LOAD
// ============================================================

applyTranslations();

loadData();

startCountdownRefresh();


// ============================================================
// PHASE FIVE — PARTICIPANT-COUNTRY INDEX INTEGRATION
// ============================================================
//
// GitHub Pages is a static frontend.
//
// The browser reads:
//
//   1. opportunities.json
//   2. participant_country_index.json
//
// The participant-country index maps a normalized country code
// to opportunity IDs. The canonical opportunity cache remains
// the authoritative source for the full opportunity objects.
//
// No Morocco-specific filtering is performed here.
// ============================================================
