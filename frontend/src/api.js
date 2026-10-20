import { reactive } from "vue"

/** One funnel for every server call. The backend answers {ok, ...} or
 * {ok:false, message}; either way staff see one plain sentence, never a traceback. */
export const toasts = reactive([])
let seq = 0
export function notify(message, kind = "info") {
	const id = ++seq
	toasts.push({ id, message, kind })
	setTimeout(() => {
		const i = toasts.findIndex((t) => t.id === id)
		if (i >= 0) toasts.splice(i, 1)
	}, kind === "error" ? 6500 : 3000)
}

export async function call(method, args = {}, { quiet = false } = {}) {
	const url = `/api/method/${method.includes(".") ? method : "grocall.api.app." + method}`
	let res
	try {
		res = await fetch(url, {
			method: "POST",
			headers: { "Content-Type": "application/json", Accept: "application/json", "X-Frappe-CSRF-Token": window.csrf_token },
			body: JSON.stringify(args),
		})
	} catch (e) {
		if (!quiet) notify("No connection. Check the internet and try again.", "error")
		throw e
	}
	let body = {}
	try { body = await res.json() } catch (e) { /* non-JSON error page */ }
	if (res.status === 403 && /login|session/i.test(JSON.stringify(body))) {
		window.location.href = "/login?redirect-to=" + encodeURIComponent(location.pathname)
		throw new Error("Session expired")
	}
	const msg = body.message
	if (!res.ok || !msg) {
		const text = serverMessage(body) || "Something went wrong. Please try again."
		if (!quiet) notify(text, "error")
		throw new Error(text)
	}
	if (msg.ok === false) {
		if (!quiet) notify(msg.message || "That did not work.", "error")
		throw new Error(msg.message)
	}
	return msg
}

function serverMessage(body) {
	try {
		const list = JSON.parse(body._server_messages || "[]")
		const first = typeof list[0] === "string" ? JSON.parse(list[0]) : list[0]
		if (first && first.message) return strip(first.message)
	} catch (e) { /* ignore */ }
	return body.exception ? strip(String(body.exception).split(":").slice(1).join(":")) : ""
}
function strip(s) {
	const d = document.createElement("div")
	d.innerHTML = s
	return (d.textContent || "").trim()
}

/** Frappe has no /logout page: end the session through the API, then go to login. */
export async function logout() {
	try {
		await fetch("/api/method/logout", { method: "POST", headers: { "X-Frappe-CSRF-Token": window.csrf_token, Accept: "application/json" } })
	} catch (e) { /* offline: still leave the app */ }
	try { sessionStorage.clear() } catch (e) { /* private mode */ }
	window.location.replace("/login")
}
