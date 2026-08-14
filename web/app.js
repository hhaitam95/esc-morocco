// ============================================================
// ESC MOROCCO OPPORTUNITIES
// Frontend logic
// ============================================================

const DATA_URL = "opportunities.json";
const EXPIRED_DATA_URL = "expired.json";


// ============================================================
// STATE
// ============================================================

let activeOpportunities = [];
let expiredOpportunities = [];
let currentLanguage = "en";


// ============================================================
// DOM ELEMENTS
// ============================================================

const opportunityCount =
    document.getElementById("opportunity-count");

const lastUpdated =
    document.getElementById("last-updated");

const activeResultCount =
    document.getElementById("active-result-count");

const opportunitiesBody =
    document.getElementById("opportunities-body");

const expiredBody =
    document.getElementById("expired-body");

const expiredSection =
    document.getElementById("expired-section");

const expiredContent =
    document.getElementById("expired-content");

const expiredCount =
    document.getElementById("expired-count");

const expiredArrow =
    document.getElementById("expired-arrow");

const loadingMessage =
    document.getElementById("loading-message");

const errorMessage =
    document.getElementById("error-message");

const emptyMessage =
    document.getElementById("empty-message");

const activeSection =
    document.getElementById("active-section");

const searchInput =
    document.getElementById("search-input");

const countryFilter =
    document.getElementById("country-filter");

const typeFilter =
    document.getElementById("type-filter");

const sortSelect =
    document.getElementById("sort-select");

const refreshButton =
    document.getElementById("refresh-button");


// ============================================================
// TRANSLATIONS
// ============================================================

const translations = {

    en: {
        title: "European Solidarity Corps",

        subtitle:
            "Volunteering opportunities for applicants from Morocco",

        activeOpportunities:
            "Active opportunities",

        lastUpdated:
            "Last updated",

        intro:
            "These are active European Solidarity Corps volunteering opportunities that accept participants from Morocco.",

        introNote:
            "The list is automatically refreshed from the European Youth Portal.",

        search:
            "Search",

        searchPlaceholder:
            "Search opportunities...",

        country:
            "Country",

        allCountries:
            "All countries",

        type:
            "Type",

        allTypes:
            "All types",

        sortBy:
            "Sort by",

        sortDeadline:
            "Application deadline",

        sortStart:
            "Activity start date",

        sortCreated:
            "Recently added",

        refresh:
            "Refresh",

        loading:
            "Loading opportunities...",

        errorTitle:
            "We couldn't load the opportunities.",

        errorText:
            "Please try again later.",

        availableNow:
            "Available now",

        opportunity:
            "Opportunity",

        location:
            "Location",

        activity:
            "Activity",

        deadline:
            "Deadline",

        expired:
            "Expired",

        noResultsTitle:
            "No opportunities found.",

        noResultsText:
            "Try changing your search or filters.",

        recentlyExpired:
            "Recently expired",

        source:
            "Data sourced from",

        footerNote:
            "Always check the official opportunity page before applying.",

        view:
            "View",

        noDeadline:
            "No deadline",

        deadlineToday:
            "Deadline today",

        dayLeft:
            "day left",

        daysLeft:
            "days left",

        expiredToday:
            "Expired today",

        expiredAgo:
            "days ago",

        noLocation:
            "Location unavailable",

        noDates:
            "Dates unavailable",

        noType:
            "Not specified",

        results:
            "results",

        result:
            "result"
    },


    fr: {
        title:
            "Corps européen de solidarité",

        subtitle:
            "Opportunités de volontariat pour les candidats du Maroc",

        activeOpportunities:
            "Opportunités actives",

        lastUpdated:
            "Dernière mise à jour",

        intro:
            "Voici les opportunités de volontariat du Corps européen de solidarité qui acceptent les participants du Maroc.",

        introNote:
            "La liste est automatiquement actualisée depuis le Portail européen de la jeunesse.",

        search:
            "Rechercher",

        searchPlaceholder:
            "Rechercher une opportunité...",

        country:
            "Pays",

        allCountries:
            "Tous les pays",

        type:
            "Type",

        allTypes:
            "Tous les types",

        sortBy:
            "Trier par",

        sortDeadline:
            "Date limite de candidature",

        sortStart:
            "Date de début",

        sortCreated:
            "Ajoutées récemment",

        refresh:
            "Actualiser",

        loading:
            "Chargement des opportunités...",

        errorTitle:
            "Impossible de charger les opportunités.",

        errorText:
            "Veuillez réessayer plus tard.",

        availableNow:
            "Disponibles actuellement",

        opportunity:
            "Opportunité",

        location:
            "Lieu",

        activity:
            "Activité",

        deadline:
            "Date limite",

        expired:
            "Expirée",

        noResultsTitle:
            "Aucune opportunité trouvée.",

        noResultsText:
            "Essayez de modifier votre recherche ou vos filtres.",

        recentlyExpired:
            "Récemment expirées",

        source:
            "Données provenant du",

        footerNote:
            "Consultez toujours la page officielle de l'opportunité avant de postuler.",

        view:
            "Voir",

        noDeadline:
            "Aucune date limite",

        deadlineToday:
            "Date limite aujourd'hui",

        dayLeft:
            "jour restant",

        daysLeft:
            "jours restants",

        expiredToday:
            "Expirée aujourd'hui",

        expiredAgo:
            "jours",

        noLocation:
            "Lieu indisponible",

        noDates:
            "Dates indisponibles",

        noType:
            "Non précisé",

        results:
            "résultats",

        result:
            "résultat"
    },


    ar: {
        title:
            "الفيلق الأوروبي للتضامن",

        subtitle:
            "فرص التطوع للمتقدمين من المغرب",

        activeOpportunities:
            "الفرص المتاحة",

        lastUpdated:
            "آخر تحديث",

        intro:
            "هذه هي فرص التطوع النشطة ضمن الفيلق الأوروبي للتضامن التي تقبل مشاركين من المغرب.",

        introNote:
            "يتم تحديث القائمة تلقائياً من بوابة الشباب الأوروبية.",

        search:
            "بحث",

        searchPlaceholder:
            "ابحث عن فرصة...",

        country:
            "الدولة",

        allCountries:
            "جميع الدول",

        type:
            "النوع",

        allTypes:
            "جميع الأنواع",

        sortBy:
            "ترتيب حسب",

        sortDeadline:
            "آخر موعد للتقديم",

        sortStart:
            "تاريخ بداية النشاط",

        sortCreated:
            "الأحدث",

        refresh:
            "تحديث",

        loading:
            "جارٍ تحميل الفرص...",

        errorTitle:
            "تعذر تحميل الفرص.",

        errorText:
            "يرجى المحاولة مرة أخرى لاحقاً.",

        availableNow:
            "الفرص المتاحة الآن",

        opportunity:
            "الفرصة",

        location:
            "الموقع",

        activity:
            "النشاط",

        deadline:
            "الموعد النهائي",

        expired:
            "منتهية",

        noResultsTitle:
            "لم يتم العثور على فرص.",

        noResultsText:
            "حاول تغيير البحث أو عوامل التصفية.",

        recentlyExpired:
            "الفرص المنتهية مؤخراً",

        source:
            "البيانات من",

        footerNote:
            "تحقق دائماً من صفحة الفرصة الرسمية قبل التقديم.",

        view:
            "عرض",

        noDeadline:
            "لا يوجد موعد نهائي",

        deadlineToday:
            "الموعد النهائي اليوم",

        dayLeft:
            "يوم متبقٍ",

        daysLeft:
            "أيام متبقية",

        expiredToday:
            "انتهت اليوم",

        expiredAgo:
            "يوماً مضت",

        noLocation:
            "الموقع غير متوفر",

        noDates:
            "التواريخ غير متوفرة",

        noType:
            "غير محدد",

        results:
            "نتائج",

        result:
            "نتيجة"
    }
};


// ============================================================
// TRANSLATION HELPERS
// ============================================================

function t(key) {
    return (
        translations[currentLanguage]?.[key]
        ??
        translations.en[key]
        ??
        key
    );
}


function applyTranslations() {

    document.documentElement.lang =
        currentLanguage;

    document.documentElement.dir =
        currentLanguage === "ar"
            ? "rtl"
            : "ltr";

    document
        .querySelectorAll("[data-i18n]")
        .forEach(element => {

            const key =
                element.dataset.i18n;

            element.textContent =
                t(key);
        });


    document
        .querySelectorAll("[data-i18n-placeholder]")
        .forEach(element => {

            const key =
                element.dataset.i18nPlaceholder;

            element.placeholder =
                t(key);
        });


    document
        .querySelectorAll(".language-button")
        .forEach(button => {

            button.classList.toggle(
                "active",
                button.dataset.language
                === currentLanguage
            );
        });


    updateCountryFilterLabels();
    updateTypeFilterLabels();

    renderActive();
    renderExpired();
}


// ============================================================
// LANGUAGE SWITCHING
// ============================================================

document
    .querySelectorAll(".language-button")
    .forEach(button => {

        button.addEventListener(
            "click",
            () => {

                currentLanguage =
                    button.dataset.language;

                localStorage.setItem(
                    "esc_language",
                    currentLanguage
                );

                applyTranslations();
            }
        );
    });


const savedLanguage =
    localStorage.getItem(
        "esc_language"
    );

if (
    savedLanguage
    && translations[savedLanguage]
) {
    currentLanguage = savedLanguage;
}


// ============================================================
// DATE HELPERS
// ============================================================

function parseDate(value) {

    if (!value) {
        return null;
    }

    const date =
        new Date(
            `${value}T00:00:00`
        );

    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return null;
    }

    return date;
}


function parseDateTime(value) {

    if (!value) {
        return null;
    }

    const date =
        new Date(value);

    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return null;
    }

    return date;
}


function formatDate(value) {

    const date =
        parseDate(value);

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
            year: "numeric"
        }
    ).format(date);
}


function formatActivityDates(
    start,
    end
) {

    if (!start && !end) {
        return t("noDates");
    }

    if (!start) {
        return `→ ${formatDate(end)}`;
    }

    if (!end) {
        return `${formatDate(start)} →`;
    }

    return (
        `${formatDate(start)} → `
        + `${formatDate(end)}`
    );
}


function startOfToday() {

    const date = new Date();

    date.setHours(
        0,
        0,
        0,
        0
    );

    return date;
}


function daysFromToday(
    value
) {

    const date =
        parseDate(value);

    if (!date) {
        return null;
    }

    const difference =
        date.getTime()
        - startOfToday().getTime();

    return Math.ceil(
        difference
        / (1000 * 60 * 60 * 24)
    );
}


function deadlineClass(
    deadline
) {

    const days =
        daysFromToday(deadline);

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


function deadlineRelative(
    deadline
) {

    const days =
        daysFromToday(deadline);

    if (days === null) {
        return t("noDeadline");
    }

    if (days === 0) {
        return t("deadlineToday");
    }

    if (days === 1) {
        return `1 ${t("dayLeft")}`;
    }

    if (days > 1 && days <= 30) {
        return `${days} ${t("daysLeft")}`;
    }

    return "";
}


function daysSince(
    value
) {

    const date =
        parseDate(value);

    if (!date) {
        return null;
    }

    const difference =
        startOfToday().getTime()
        - date.getTime();

    return Math.max(
        0,
        Math.floor(
            difference
            / (1000 * 60 * 60 * 24)
        )
    );
}


function expiredRelative(
    deadline
) {

    const days =
        daysSince(deadline);

    if (days === null) {
        return "";
    }

    if (days === 0) {
        return t("expiredToday");
    }

    if (currentLanguage === "ar") {
        return `${days} ${t("expiredAgo")}`;
    }

    return `${days} ${t("expiredAgo")}`;
}


// ============================================================
// HTML ESCAPING
// ============================================================

function escapeHtml(value) {

    if (
        value === null
        || value === undefined
    ) {
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
// COUNTRY NAMES
// ============================================================

const countryNames =
    new Intl.DisplayNames(
        ["en"],
        {
            type: "region"
        }
    );


function getCountryName(
    code
) {

    if (!code) {
        return "";
    }

    try {
        return (
            countryNames.of(code)
            || code
        );
    } catch {
        return code;
    }
}


// ============================================================
// FILTER OPTIONS
// ============================================================

function uniqueSortedValues(
    items,
    property
) {

    return [
        ...new Set(
            items
                .map(item => item[property])
                .filter(Boolean)
        )
    ].sort(
        (a, b) =>
            String(a)
                .localeCompare(
                    String(b)
                )
    );
}


function populateFilters() {

    const countries =
        uniqueSortedValues(
            activeOpportunities,
            "country"
        );

    const types =
        uniqueSortedValues(
            activeOpportunities,
            "activity_type"
        );


    countryFilter.innerHTML =
        `<option value="">
            ${escapeHtml(
                t("allCountries")
            )}
        </option>`;


    countries.forEach(code => {

        const option =
            document.createElement(
                "option"
            );

        option.value = code;

        option.textContent =
            getCountryName(code);

        countryFilter.appendChild(
            option
        );
    });


    typeFilter.innerHTML =
        `<option value="">
            ${escapeHtml(
                t("allTypes")
            )}
        </option>`;


    types.forEach(type => {

        const option =
            document.createElement(
                "option"
            );

        option.value = type;

        option.textContent = type;

        typeFilter.appendChild(
            option
        );
    });


    updateCountryFilterLabels();
    updateTypeFilterLabels();
}


function updateCountryFilterLabels() {

    const current =
        countryFilter.value;

    const first =
        countryFilter.querySelector(
            "option:first-child"
        );

    if (first) {
        first.textContent =
            t("allCountries");
    }

    countryFilter.value =
        current;
}


function updateTypeFilterLabels() {

    const current =
        typeFilter.value;

    const first =
        typeFilter.querySelector(
            "option:first-child"
        );

    if (first) {
        first.textContent =
            t("allTypes");
    }

    typeFilter.value =
        current;
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


    return activeOpportunities.filter(
        opportunity => {

            const searchable = [

                opportunity.title,

                opportunity.location,

                opportunity.town,

                getCountryName(
                    opportunity.country
                ),

                opportunity.activity_type,

                ...(opportunity.topics || [])

            ]
                .filter(Boolean)
                .join(" ")
                .toLowerCase();


            if (
                search
                && !searchable.includes(
                    search
                )
            ) {
                return false;
            }


            if (
                country
                && opportunity.country
                !== country
            ) {
                return false;
            }


            if (
                type
                && opportunity.activity_type
                !== type
            ) {
                return false;
            }


            return true;
        }
    );
}


// ============================================================
// SORTING
// ============================================================

function sortOpportunities(
    items
) {

    const sorted =
        [...items];

    const sortType =
        sortSelect.value;


    if (
        sortType === "start"
    ) {

        sorted.sort(
            (a, b) => {

                const dateA =
                    parseDate(
                        a.start_date
                    );

                const dateB =
                    parseDate(
                        b.start_date
                    );

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
            }
        );

        return sorted;
    }


    if (
        sortType === "created"
    ) {

        sorted.sort(
            (a, b) => {

                const dateA =
                    parseDateTime(
                        a.created
                    );

                const dateB =
                    parseDateTime(
                        b.created
                    );

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
            }
        );

        return sorted;
    }


    // Default: deadline
    sorted.sort(
        (a, b) => {

            const dateA =
                parseDate(
                    a.deadline
                );

            const dateB =
                parseDate(
                    b.deadline
                );

            // No deadline → last
            if (!dateA && !dateB) {
                return a.title.localeCompare(
                    b.title
                );
            }

            if (!dateA) {
                return 1;
            }

            if (!dateB) {
                return -1;
            }

            return dateA - dateB;
        }
    );

    return sorted;
}


// ============================================================
// TOPICS
// ============================================================

function renderTopics(
    topics
) {

    if (
        !Array.isArray(topics)
        || topics.length === 0
    ) {
        return "";
    }

    return `
        <div class="topic-tags">
            ${topics.map(topic => `
                <span class="topic-tag">
                    ${escapeHtml(topic)}
                </span>
            `).join("")}
        </div>
    `;
}


// ============================================================
// ACTIVE TABLE
// ============================================================

function renderActive() {

    const filtered =
        sortOpportunities(
            getFilteredActive()
        );


    activeResultCount.textContent =
        `${filtered.length} `
        + (
            filtered.length === 1
                ? t("result")
                : t("results")
        );


    if (
        filtered.length === 0
    ) {

        opportunitiesBody.innerHTML =
            "";

        emptyMessage.classList.remove(
            "hidden"
        );

        return;
    }


    emptyMessage.classList.add(
        "hidden"
    );


    opportunitiesBody.innerHTML =
        filtered.map(
            opportunity => {

                const locationCountry =
                    getCountryName(
                        opportunity.country
                    );


                const location =
                    opportunity.town
                        ? opportunity.town
                        : (
                            opportunity.location
                            || t("noLocation")
                        );


                const deadlineClassName =
                    deadlineClass(
                        opportunity.deadline
                    );


                const relative =
                    deadlineRelative(
                        opportunity.deadline
                    );


                return `
                    <tr>

                        <td class="title-cell">

                            <div class="opportunity-title">
                                ${escapeHtml(
                                    opportunity.title
                                )}
                            </div>

                            ${
                                opportunity.topics?.length
                                    ? renderTopics(
                                        opportunity.topics
                                    )
                                    : ""
                            }

                        </td>


                        <td class="location-cell">

                            <div class="location-main">
                                ${escapeHtml(
                                    location
                                )}
                            </div>

                            <div class="location-country">
                                ${escapeHtml(
                                    locationCountry
                                )}
                            </div>

                        </td>


                        <td class="activity-cell">

                            ${escapeHtml(
                                formatActivityDates(
                                    opportunity.start_date,
                                    opportunity.end_date
                                )
                            )}

                        </td>


                        <td class="deadline-cell">

                            <span
                                class="deadline-date ${deadlineClassName}"
                            >
                                ${escapeHtml(
                                    opportunity.deadline
                                        ? formatDate(
                                            opportunity.deadline
                                        )
                                        : t("noDeadline")
                                )}
                            </span>

                            ${
                                relative
                                    ? `
                                        <span class="deadline-relative">
                                            ${escapeHtml(
                                                relative
                                            )}
                                        </span>
                                    `
                                    : ""
                            }

                        </td>


                        <td class="type-cell">

                            <span class="type-label">
                                ${escapeHtml(
                                    opportunity.activity_type
                                    || t("noType")
                                )}
                            </span>

                        </td>


                        <td class="apply-cell">

                            <a
                                class="apply-button"
                                href="${escapeHtml(
                                    opportunity.url
                                )}"
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                ${escapeHtml(
                                    t("view")
                                )}
                            </a>

                        </td>

                    </tr>
                `;
            }
        ).join("");
}


// ============================================================
// EXPIRED TABLE
// ============================================================

function renderExpired() {

    if (
        !expiredOpportunities.length
    ) {

        expiredSection.classList.add(
            "hidden"
        );

        return;
    }


    expiredSection.classList.remove(
        "hidden"
    );


    expiredCount.textContent =
        expiredOpportunities.length;


    expiredBody.innerHTML =
        expiredOpportunities
            .map(
                opportunity => {

                    const location =
                        opportunity.town
                        || opportunity.location
                        || t("noLocation");


                    return `
                        <tr>

                            <td>
                                <strong>
                                    ${escapeHtml(
                                        opportunity.title
                                    )}
                                </strong>
                            </td>

                            <td>

                                ${escapeHtml(
                                    location
                                )}

                                ${
                                    opportunity.country
                                        ? `
                                            <div class="location-country">
                                                ${escapeHtml(
                                                    getCountryName(
                                                        opportunity.country
                                                    )
                                                )}
                                            </div>
                                        `
                                        : ""
                                }

                            </td>

                            <td>
                                ${escapeHtml(
                                    formatDate(
                                        opportunity.deadline
                                    )
                                )}
                            </td>

                            <td>
                                ${escapeHtml(
                                    expiredRelative(
                                        opportunity.deadline
                                    )
                                )}
                            </td>

                        </tr>
                    `;
                }
            )
            .join("");
}


// ============================================================
// STATUS HEADER
// ============================================================

function updateHeader(
    data
) {

    const count =
        activeOpportunities.length;


    opportunityCount.textContent =
        count === 1
            ? `1 ${t("result")}`
            : `${count} ${t("results")}`;


    if (
        data.generated_at
    ) {

        const date =
            parseDateTime(
                data.generated_at
            );


        if (date) {

            lastUpdated.textContent =
                new Intl.DateTimeFormat(
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
                        minute: "2-digit"
                    }
                ).format(
                    date
                );

        } else {

            lastUpdated.textContent =
                "—";
        }

    } else {

        lastUpdated.textContent =
            "—";
    }
}


// ============================================================
// DATA FETCHING
// ============================================================

async function fetchJson(
    url
) {

    const response =
        await fetch(
            `${url}?t=${Date.now()}`,
            {
                cache: "no-store"
            }
        );


    if (
        !response.ok
    ) {

        throw new Error(
            `HTTP ${response.status}`
        );
    }


    return response.json();
}


// ============================================================
// LOAD DATA
// ============================================================

async function loadData() {

    loadingMessage.classList.remove(
        "hidden"
    );

    errorMessage.classList.add(
        "hidden"
    );


    try {

        const activeData =
            await fetchJson(
                DATA_URL
            );


        activeOpportunities =
            Array.isArray(
                activeData?.opportunities
            )
                ? activeData.opportunities
                : [];


        // Expired data is optional.
        try {

            const expiredData =
                await fetchJson(
                    EXPIRED_DATA_URL
                );


            expiredOpportunities =
                Array.isArray(
                    expiredData?.opportunities
                )
                    ? expiredData.opportunities
                    : [];

        } catch {

            expiredOpportunities =
                [];
        }


        populateFilters();

        updateHeader(
            activeData
        );

        renderActive();

        renderExpired();


    } catch (error) {

        console.error(
            "Could not load opportunities:",
            error
        );


        activeOpportunities =
            [];

        opportunityCount.textContent =
            "—";

        lastUpdated.textContent =
            "—";


        errorMessage.classList.remove(
            "hidden"
        );

    } finally {

        loadingMessage.classList.add(
            "hidden"
        );
    }
}


// ============================================================
// REFRESH BUTTON
// ============================================================

refreshButton.addEventListener(
    "click",
    async () => {

        refreshButton.disabled =
            true;

        const originalText =
            refreshButton.innerHTML;


        refreshButton.innerHTML =
            `↻ <span>${escapeHtml(
                t("loading")
            )}</span>`;


        try {

            await loadData();

        } finally {

            refreshButton.disabled =
                false;

            refreshButton.innerHTML =
                `↻ <span>${escapeHtml(
                    t("refresh")
                )}</span>`;
        }
    }
);


// ============================================================
// FILTER EVENTS
// ============================================================

searchInput.addEventListener(
    "input",
    renderActive
);

countryFilter.addEventListener(
    "change",
    renderActive
);

typeFilter.addEventListener(
    "change",
    renderActive
);

sortSelect.addEventListener(
    "change",
    renderActive
);


// ============================================================
// EXPIRED TOGGLE
// ============================================================

document
    .getElementById("expired-toggle")
    .addEventListener(
        "click",
        () => {

            const isHidden =
                expiredContent.classList.contains(
                    "hidden"
                );


            expiredContent.classList.toggle(
                "hidden"
            );


            expiredArrow.classList.toggle(
                "open",
                isHidden
            );
        }
    );


// ============================================================
// INITIAL LOAD
// ============================================================

applyTranslations();

loadData();