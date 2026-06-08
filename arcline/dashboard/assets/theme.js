/*
 * arcline dashboard - clientside theme bootstrap
 * ----------------------------------------------
 * Runs before Dash renders so the very first paint already has
 * the user's preferred theme. Persists the choice in localStorage
 * under `arc-theme` and exposes a `window.arcSetTheme(name)` helper
 * for the navbar toggle button.
 */
(function () {
    "use strict";

    var KEY = "arc-theme";
    var DEFAULT = "dark";

    function apply(name) {
        var theme = (name === "light") ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", theme);
        try { localStorage.setItem(KEY, theme); } catch (e) { /* ignore */ }
        // notify listeners (e.g. visualize page can re-read theme)
        document.dispatchEvent(new CustomEvent("arc-theme-change", {
            detail: { theme: theme }
        }));
    }

    function resolveInitial() {
        try {
            var stored = localStorage.getItem(KEY);
            if (stored === "dark" || stored === "light") return stored;
        } catch (e) { /* ignore */ }
        if (window.matchMedia &&
            window.matchMedia("(prefers-color-scheme: light)").matches) {
            return "light";
        }
        return DEFAULT;
    }

    apply(resolveInitial());
    window.arcSetTheme = apply;
    window.arcToggleTheme = function () {
        var current = document.documentElement.getAttribute("data-theme");
        apply(current === "light" ? "dark" : "light");
    };
})();
