# ESC Opportunity Finder — Archived Opportunity Lifecycle

## Scope

Frontend-only change.

No scraper logic changed.
No backend/data-provider logic changed.
No opportunity JSON was regenerated.
No repair checkpoint was modified.

## Behavior

An opportunity whose deadline passes while the page remains open is now automatically moved from the active dataset into the existing Recently expired section.

Archived opportunities are retained for 30 days.

The existing archive renderer and archive UI are preserved.

## Test opportunity

- ID: 53315
- Deadline: 2026-08-16
- Before deadline: active
- After deadline: archived
- Retention: 30 days

## Changes

- added live active-to-archive lifecycle
- runs lifecycle immediately after provider data loads
- connects lifecycle to existing 60-second refresh

## Validation

- 1,178 opportunities: PASS
- Backend/frontend opportunity IDs: PASS
- Opportunity 53315: PASS
- Existing archive markup: PASS
- JavaScript syntax: PASS
- Lifecycle simulation: PASS
- Repair checkpoint unchanged: PASS

## Diff

```diff
diff --git a/web/app.js b/web/app.js
index d37e545..aa5f5d5 100644
--- a/web/app.js
+++ b/web/app.js
@@ -2773,6 +2773,9 @@ async function loadData() {
         ? payload.expiredData.opportunities
         : [];
 
+    moveExpiredOpportunitiesToArchive();
+    pruneExpiredArchive();
+
     calculateNewOpportunities(activeOpportunities);
 
     populateFilters();
@@ -2847,19 +2850,184 @@ document.getElementById("expired-toggle").addEventListener("click", () => {
   expiredArrow.classList.toggle("open", isHidden);
 });
 
+// ============================================================
+// LIVE OPPORTUNITY ARCHIVE LIFECYCLE
+// ============================================================
+//
+// The data provider supplies the active and expired datasets.
+// This browser-side lifecycle additionally handles an opportunity
+// whose deadline passes while the page remains open.
+//
+// Active
+//   ↓ deadline passes
+// Recently expired
+//
+// Recently expired opportunities are retained for 30 days.
+// ============================================================
+
+const ARCHIVE_RETENTION_DAYS = 30;
+
+function getArchiveDeadline(value) {
+  if (!value) {
+    return null;
+  }
+
+  const raw = String(value).trim();
+
+  if (!raw) {
+    return null;
+  }
+
+  // Keep the archive transition consistent with the current
+  // frontend's date-only interpretation: a deadline date is
+  // considered expired once that calendar date has passed.
+  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
+    const date = new Date(`${raw}T00:00:00`);
+
+    if (Number.isNaN(date.getTime())) {
+      return null;
+    }
+
+    return date;
+  }
+
+  const date = new Date(raw);
+
+  if (Number.isNaN(date.getTime())) {
+    return null;
+  }
+
+  return date;
+}
+
+function moveExpiredOpportunitiesToArchive() {
+  if (!Array.isArray(activeOpportunities)) {
+    return false;
+  }
+
+  const now = new Date();
+
+  const cutoff = new Date(now);
+  cutoff.setDate(
+    cutoff.getDate() - ARCHIVE_RETENTION_DAYS,
+  );
+
+  const stillActive = [];
+  const newlyExpired = [];
+
+  activeOpportunities.forEach((opportunity) => {
+    const deadline = getArchiveDeadline(
+      opportunity.deadline,
+    );
+
+    // No usable deadline: leave the opportunity alone.
+    if (!deadline) {
+      stillActive.push(opportunity);
+      return;
+    }
+
+    if (deadline.getTime() > now.getTime()) {
+      stillActive.push(opportunity);
+      return;
+    }
+
+    // Deadline has passed. Only retain it in the archive
+    // while it is still inside the recent-expiry window.
+    if (deadline.getTime() >= cutoff.getTime()) {
+      newlyExpired.push(opportunity);
+    }
+  });
+
+  if (!newlyExpired.length) {
+    return false;
+  }
+
+  const archivedIds = new Set(
+    expiredOpportunities.map(
+      (opportunity) => String(opportunity.id),
+    ),
+  );
+
+  newlyExpired.forEach((opportunity) => {
+    const id = String(opportunity.id);
+
+    if (!archivedIds.has(id)) {
+      expiredOpportunities.push(opportunity);
+      archivedIds.add(id);
+    }
+  });
+
+  activeOpportunities = stillActive;
+
+  // Also remove archive records that have become older than
+  // the retention window.
+  expiredOpportunities = expiredOpportunities.filter(
+    (opportunity) => {
+      const deadline = getArchiveDeadline(
+        opportunity.deadline,
+      );
+
+      if (!deadline) {
+        return true;
+      }
+
+      return (
+        deadline.getTime() >= cutoff.getTime()
+      );
+    },
+  );
+
+  return true;
+}
+
+function pruneExpiredArchive() {
+  if (!Array.isArray(expiredOpportunities)) {
+    expiredOpportunities = [];
+    return;
+  }
+
+  const now = new Date();
+
+  const cutoff = new Date(now);
+  cutoff.setDate(
+    cutoff.getDate() - ARCHIVE_RETENTION_DAYS,
+  );
+
+  expiredOpportunities =
+    expiredOpportunities.filter(
+      (opportunity) => {
+        const deadline = getArchiveDeadline(
+          opportunity.deadline,
+        );
+
+        if (!deadline) {
+          return true;
+        }
+
+        return (
+          deadline.getTime() >= cutoff.getTime()
+        );
+      },
+    );
+}
+
+function refreshOpportunityLifecycle() {
+  moveExpiredOpportunitiesToArchive();
+  pruneExpiredArchive();
+
+  renderActive();
+  renderExpired();
+}
 // ============================================================
 // COUNTDOWN REFRESH
 // ============================================================
 
 function startCountdownRefresh() {
-  // Refresh the countdown display every minute to keep it current
+  // Re-evaluate both the deadline countdown and the
+  // active → recently-expired lifecycle every minute.
   setInterval(() => {
-    // Only re-render active opportunities if they exist
-    // This updates the deadline-relative display (hourly countdown)
-    if (activeOpportunities.length > 0) {
-      renderActive();
-    }
-  }, 60000); // 60000 ms = 1 minute
+    refreshOpportunityLifecycle();
+  }, 60000);
 }
 
 // ============================================================
```
