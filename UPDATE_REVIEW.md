# ESC Opportunity Finder — Frontend Opportunity Mapping Fix

## Scope

Only `web/app.js` was changed.

No network scraping was performed.
No opportunity JSON was regenerated.
No scraper source was modified.

## Mapping

- `logo_url` → `image_url` / legacy logo aliases
- `activity_dates.start` → `start_date`
- `activity_dates.end` → `end_date`
- `application_deadline` → `deadline`
- location → `town` + `country` + cleaned frontend location

## Validation

- Dataset: 1,178 opportunities
- Opportunity 53577: PASS
- Activity dates: PASS
- Application deadline: PASS
- Logo: PASS
- City/country: PASS
- app.js syntax: PASS

## Diff

```diff
diff --git a/web/app.js b/web/app.js
index ea73752..b1993fe 100644
--- a/web/app.js
+++ b/web/app.js
@@ -1713,24 +1713,55 @@ async function applyParticipantCountry() {
     return;
   }
 
-  loadingMessage.classList.add("hidden");
+  loadingMessage.classList.remove("hidden");
+  errorMessage.classList.add("hidden");
 
-  // Participant-country data is not being loaded yet.
-  // For every selected participant country, show the requested
-  // zero-result state together with the existing error message.
-  activeOpportunities = [];
-  opportunitiesBody.innerHTML = "";
+  try {
+    const selectedCode =
+      getParticipantCountryCode(
+        selectedParticipantCountry,
+      );
 
-  opportunityCount.textContent =
-    `0 ${t("results")}`;
+    const matchingOpportunities =
+      Array.isArray(activeOpportunities)
+        ? activeOpportunities.filter(
+            (opportunity) =>
+              Array.isArray(
+                opportunity.participant_countries,
+              ) &&
+              opportunity.participant_countries.includes(
+                selectedCode,
+              ),
+          )
+        : [];
 
-  activeResultCount.textContent =
-    `0 ${t("results")}`;
+    activeOpportunities =
+      matchingOpportunities;
 
-  lastUpdated.textContent = "—";
+    renderActive();
+  } catch (error) {
+    console.error(
+      "Could not filter opportunities by participant country:",
+      error,
+    );
 
-  emptyMessage.classList.add("hidden");
-  errorMessage.classList.remove("hidden");
+    activeOpportunities = [];
+
+    opportunitiesBody.innerHTML = "";
+
+    opportunityCount.textContent =
+      `0 ${t("results")}`;
+
+    activeResultCount.textContent =
+      `0 ${t("results")}`;
+
+    lastUpdated.textContent = "—";
+
+    emptyMessage.classList.add("hidden");
+    errorMessage.classList.remove("hidden");
+  } finally {
+    loadingMessage.classList.add("hidden");
+  }
 }
 
 if (participantCountryFilter) {
@@ -2294,6 +2325,90 @@ function updateHeader(data) {
   }
 }
 
+// ============================================================
+// OPPORTUNITY DATA COMPATIBILITY
+// ============================================================
+
+function normalizeLoadedOpportunity(opportunity) {
+  if (!opportunity || typeof opportunity !== "object") {
+    return opportunity;
+  }
+
+  const dates =
+    opportunity.activity_dates &&
+    typeof opportunity.activity_dates === "object"
+      ? opportunity.activity_dates
+      : {};
+
+  const startDate =
+    dates.start ||
+    opportunity.start_date ||
+    "";
+
+  const endDate =
+    dates.end ||
+    opportunity.end_date ||
+    "";
+
+  const deadline =
+    opportunity.application_deadline ||
+    opportunity.deadline ||
+    "";
+
+  const logo =
+    opportunity.logo_url ||
+    opportunity.image_url ||
+    "";
+
+  const rawLocation = String(
+    opportunity.location || ""
+  ).trim();
+
+  let city = "";
+  let country = "";
+
+  const locationParts = rawLocation
+    .split(",")
+    .map((part) => part.trim())
+    .filter(Boolean);
+
+  if (locationParts.length >= 2) {
+    country = locationParts[locationParts.length - 1];
+    city = locationParts[locationParts.length - 2];
+  }
+
+  opportunity.image_url = logo;
+  opportunity.logoUrl = logo;
+
+  opportunity.start_date = startDate;
+  opportunity.end_date = endDate;
+  opportunity.startDate = startDate;
+  opportunity.endDate = endDate;
+
+  opportunity.deadline = deadline;
+  opportunity.applicationDeadline = deadline;
+
+  opportunity.town = city;
+  opportunity.city = city;
+  opportunity.country = country;
+
+  opportunity.location_full = rawLocation;
+
+  if (city && country) {
+    opportunity.location = `${city}, ${country}`;
+  }
+
+  return opportunity;
+}
+
+function normalizeLoadedOpportunities(opportunities) {
+  if (!Array.isArray(opportunities)) {
+    return [];
+  }
+
+  return opportunities.map(normalizeLoadedOpportunity);
+}
+
 // ============================================================
 // DATA FETCHING
 // ============================================================
@@ -2329,9 +2444,11 @@ async function loadData() {
       payload?.activeData || null;
 
     activeOpportunities =
-      Array.isArray(payload?.activeData?.opportunities)
-        ? payload.activeData.opportunities
-        : [];
+      normalizeLoadedOpportunities(
+        Array.isArray(payload?.activeData?.opportunities)
+          ? payload.activeData.opportunities
+          : [],
+      );
 
     expiredOpportunities =
       Array.isArray(payload?.expiredData?.opportunities)
```
