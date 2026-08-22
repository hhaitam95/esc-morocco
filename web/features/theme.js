const THEME_STORAGE_KEY =
  "esc_theme";

function readTheme() {
  try {
    const stored =
      localStorage.getItem(
        THEME_STORAGE_KEY,
      );

    if (
      stored === "dark" ||
      stored === "light"
    ) {
      return stored;
    }
  } catch {
    // Use system preference.
  }

  return window.matchMedia(
    "(prefers-color-scheme: dark)",
  ).matches
    ? "dark"
    : "light";
}

function applyTheme(theme) {
  document.documentElement.dataset.theme =
    theme;
}

export function updateThemeControl(
  t,
) {
  const toggle =
    document.getElementById(
      "theme-toggle",
    );

  const icon =
    document.getElementById(
      "theme-icon",
    );

  if (!toggle || !icon) {
    return;
  }

  const dark =
    document.documentElement.dataset.theme ===
    "dark";

  icon.textContent =
    dark ? "☀️" : "🌙";

  const label =
    dark
      ? t("lightMode")
      : t("darkMode");

  toggle.setAttribute(
    "aria-label",
    label,
  );

  toggle.setAttribute(
    "title",
    label,
  );
}

export function initTheme(t) {
  applyTheme(
    readTheme(),
  );

  const toggle =
    document.getElementById(
      "theme-toggle",
    );

  if (!toggle) {
    return;
  }

  if (
    toggle.dataset.themeHandlerBound ===
    "true"
  ) {
    updateThemeControl(t);
    return;
  }

  toggle.dataset.themeHandlerBound =
    "true";

  toggle.addEventListener(
    "click",
    () => {
      const next =
        document.documentElement.dataset.theme ===
        "dark"
          ? "light"
          : "dark";

      applyTheme(next);

      try {
        localStorage.setItem(
          THEME_STORAGE_KEY,
          next,
        );
      } catch {
        // Optional persistence.
      }

      updateThemeControl(t);
    },
  );

  updateThemeControl(t);
}
