import { createRouter, createWebHistory } from "vue-router"
import { state } from "./store"

const V = (n) => () => import(`./views/${n}.vue`)
// `phase` = the grocall-prd.md §10 phase that fills the screen in; until then it shows a plain placeholder.
export const routes = [
	{ path: "/calls", redirect: () => (state.boot.has_access ? "/calls/today" : "/calls/no-access") },
	{ path: "/calls/no-access", component: V("NoAccess"), meta: { title: "No access", bare: true } },
	{ path: "/calls/today", component: V("Today"), meta: { title: "Today", icon: "M3 12l9-9 9 9M5 10v10h14V10", nav: true } },
	{ path: "/calls/log", component: V("Placeholder"), meta: { title: "Calls", phase: 4, nav: true,
		icon: "M3 5a2 2 0 012-2h3l2 5-2.5 1.5a11 11 0 005 5L14 12l5 2v3a2 2 0 01-2 2A16 16 0 013 5z",
		blurb: "Every company-SIM call — in, out, missed — with the matched lead, outcome and recording player." } },
	{ path: "/calls/leads", component: V("Placeholder"), meta: { title: "Leads", phase: 4, nav: true,
		icon: "M16 7a4 4 0 11-8 0 4 4 0 018 0zM4 21a8 8 0 0116 0",
		blurb: "Your leads with their call timeline, notes, stage and next step." } },
	{ path: "/calls/follow-ups", component: V("Placeholder"), meta: { title: "Follow-ups", phase: 5, nav: true,
		icon: "M8 7V3m8 4V3M4 11h16M5 5h14a1 1 0 011 1v14a1 1 0 01-1 1H5a1 1 0 01-1-1V6a1 1 0 011-1z",
		blurb: "Follow-ups due today and overdue, and missed calls waiting for a call back." } },
	{ path: "/calls/team", component: V("Placeholder"), meta: { title: "Team", phase: 6, nav: true, perm: "manager",
		icon: "M17 20h5v-2a4 4 0 00-5-4M9 20H2v-2a4 4 0 015-4m6-4a4 4 0 11-8 0 4 4 0 018 0z",
		blurb: "Today's KPIs, leaderboard, overdue follow-ups and open missed calls for your team." } },
	{ path: "/calls/reports", component: V("Placeholder"), meta: { title: "Reports", phase: 6, nav: true, perm: "manager",
		icon: "M9 17V9m4 8V5m4 12v-6M4 21h16",
		blurb: "Rep activity, missed-call response, follow-up discipline, lead coverage and AI insights." } },
	{ path: "/calls/phones", component: V("Phones"), meta: { title: "Phones", nav: true, perm: "rep",
		icon: "M8 2h8a2 2 0 012 2v16a2 2 0 01-2 2H8a2 2 0 01-2-2V4a2 2 0 012-2zm4 16h.01",
	} },
	{ path: "/calls/settings", component: V("Settings"), meta: { title: "Settings", nav: true, perm: "admin",
		icon: "M12 15a3 3 0 100-6 3 3 0 000 6zm7.4-3a7.4 7.4 0 00-.1-1.2l2-1.6-2-3.4-2.4 1a7 7 0 00-2-1.2L14.5 3h-5l-.4 2.6a7 7 0 00-2 1.2l-2.4-1-2 3.4 2 1.6a7.4 7.4 0 000 2.4l-2 1.6 2 3.4 2.4-1a7 7 0 002 1.2l.4 2.6h5l.4-2.6a7 7 0 002-1.2l2.4 1 2-3.4-2-1.6c.1-.4.1-.8.1-1.2z" } },
	{ path: "/calls/more", component: V("More"), meta: { title: "More", icon: "M4 6h16M4 12h16M4 18h16" } },
	{ path: "/calls/:p(.*)*", redirect: "/calls" },
]
const router = createRouter({ history: createWebHistory(), routes, scrollBehavior: () => ({ top: 0 }) })
router.beforeEach((to) => {
	if (!state.boot.has_access && to.path !== "/calls/no-access") return "/calls/no-access"
	if (to.meta.perm && !state.perms[to.meta.perm]) return "/calls/today"
})
router.afterEach((to) => { document.title = `${to.meta.title || ""} · ${state.brand.name}` })
export default router
