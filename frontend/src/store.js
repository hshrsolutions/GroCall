import { reactive } from "vue"

const boot = (window.frappe && window.frappe.boot) || {}
export const state = reactive({
	boot,
	perms: boot.perms || { rep: false, manager: false, admin: false },
	brand: boot.brand || { name: "GroCall", accent: "#0f766e" },
})

/** Per-site accent: hex from CL Settings → the --accent CSS variable (r g b). */
export function applyBrand() {
	const hex = (state.brand.accent || "").replace("#", "")
	if (/^[0-9a-f]{6}$/i.test(hex)) {
		const rgb = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16)).join(" ")
		document.documentElement.style.setProperty("--accent", rgb)
	}
}
