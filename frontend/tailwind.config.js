/** Colours come from CSS variables in src/main.css so the per-site accent and
 * dark mode change in one place. */
export default {
	content: ["./index.html", "./src/**/*.{vue,js}"],
	darkMode: ["class", '[data-theme="dark"]'],
	theme: {
		extend: {
			fontFamily: { sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"] },
			colors: {
				page: "rgb(var(--page) / <alpha-value>)",
				card: "rgb(var(--card) / <alpha-value>)",
				soft: "rgb(var(--soft) / <alpha-value>)",
				line: "rgb(var(--line) / <alpha-value>)",
				ink: { DEFAULT: "rgb(var(--ink) / <alpha-value>)", 2: "rgb(var(--ink-2) / <alpha-value>)", 3: "rgb(var(--ink-3) / <alpha-value>)" },
				accent: { DEFAULT: "rgb(var(--accent) / <alpha-value>)", ink: "rgb(var(--accent-ink) / <alpha-value>)", soft: "rgb(var(--accent-soft) / <alpha-value>)" },
				good: "rgb(var(--good) / <alpha-value>)",
				warn: "rgb(var(--warn) / <alpha-value>)",
				bad: "rgb(var(--bad) / <alpha-value>)",
			},
			borderRadius: { card: "14px" },
			boxShadow: { card: "0 1px 2px rgba(20,16,8,.06), 0 2px 8px rgba(20,16,8,.04)" },
		},
	},
	plugins: [],
}
