<template>
	<div class="space-y-4">
		<div class="row">
			<h1 class="h1 hidden md:block">Phones</h1>
			<div class="flex gap-2 ml-auto">
				<select v-if="reps.length" v-model="pairFor" class="input !h-9 !w-auto text-sm">
					<option :value="state.boot.user">My phone</option>
					<option v-for="r in reps.filter((x) => x.name !== state.boot.user)" :key="r.name" :value="r.name">
						{{ r.full_name || r.name }}</option>
				</select>
				<button class="btn-primary btn-sm" :disabled="busy" @click="newCode">Pair a phone</button>
			</div>
		</div>

		<div v-if="code" class="card p-5 md:flex gap-6 items-center">
			<canvas ref="qr" class="mx-auto md:mx-0 rounded-xl border border-line bg-white" />
			<div class="space-y-2 mt-4 md:mt-0 text-center md:text-left">
				<div class="label">Pairing code for {{ code.name }}</div>
				<div class="text-3xl font-bold tracking-[.25em] num" data-test="pair-code">{{ code.code.slice(0, 4) }}-{{ code.code.slice(4) }}</div>
				<p class="text-sm text-ink-2">Open the GroCall app on the phone and scan this, or type the code.
					It works once and expires in <b class="num">{{ left }}</b>.</p>
				<p class="muted">On the phone: accept the notice, then pick the <b>company SIM</b>. Only calls on that SIM are
					tracked.</p>
				<button class="btn-ghost btn-sm" @click="code = null">Close</button>
			</div>
		</div>

		<div class="card overflow-hidden">
			<div v-if="!phones.length && !loading" class="p-6 text-center muted">No phones paired yet.</div>
			<div v-for="p in phones" :key="p.name" class="li-row !items-start">
				<div class="flex-1 min-w-0">
					<div class="font-semibold truncate">{{ p.brand ? cap(p.brand) + " " : "" }}{{ p.model || p.name }}
						<span v-if="!p.enabled" class="chip-bad ml-1">Unpaired</span>
						<span v-else-if="p.support_tier" :class="p.support_tier === 'A' ? 'chip-good' : 'chip-warn'" class="ml-1">
							Tier {{ p.support_tier }}</span>
					</div>
					<div class="text-sm text-ink-2 truncate">{{ p.full_name || p.user }}</div>
					<div class="muted text-xs">
						Company SIM: {{ p.sim_carrier || "?" }} ···{{ p.sim_last4 || "????" }} · Android {{ p.os_version || "?" }} ·
						app {{ p.app_version || "?" }} · last sync {{ ago(p.last_sync) }}</div>
				</div>
				<button v-if="state.perms.admin && p.enabled" class="btn-ghost btn-sm !text-bad" @click="revoke(p)">Unpair</button>
			</div>
		</div>
		<p class="muted">The phone app (Android, Flutter) is built in Phase 3. Pairing codes already work against the
			server so the app can be tested the day it is ready.</p>
	</div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue"
import QRCode from "qrcode"
import { call, notify } from "../api"
import { state } from "../store"

const phones = ref([]), reps = ref([]), loading = ref(true), busy = ref(false)
const code = ref(null), qr = ref(null), left = ref(""), pairFor = ref(state.boot.user)
let timer = null

async function load() {
	loading.value = true
	try {
		const r = await call("phones")
		phones.value = r.phones
		reps.value = r.reps
	} finally { loading.value = false }
}
async function newCode() {
	busy.value = true
	try {
		const r = await call("pairing_code", { user: pairFor.value })
		const rep = reps.value.find((x) => x.name === r.user)
		code.value = { ...r, name: rep ? rep.full_name || rep.name : state.boot.full_name }
		await nextTick()
		await QRCode.toCanvas(qr.value, r.qr, { width: 220, margin: 2 })
		tick()
	} finally { busy.value = false }
}
function tick() {
	clearInterval(timer)
	const end = new Date(code.value.expires_at.replace(" ", "T")).getTime()
	const step = () => {
		const s = Math.max(0, Math.round((end - Date.now()) / 1000))
		left.value = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`
		if (!s) { clearInterval(timer); code.value = null; notify("The pairing code expired. Make a new one.") }
	}
	step()
	timer = setInterval(step, 1000)
}
async function revoke(p) {
	if (!confirm(`Unpair ${p.model || p.name}? The phone stops syncing until it is paired again.`)) return
	await call("revoke_phone", { device: p.name })
	notify("Phone unpaired.")
	load()
}
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1)
function ago(t) {
	if (!t) return "never"
	const m = Math.round((Date.now() - new Date(t.replace(" ", "T")).getTime()) / 60000)
	return m < 1 ? "just now" : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} d ago`
}
onMounted(load)
onBeforeUnmount(() => clearInterval(timer))
</script>
