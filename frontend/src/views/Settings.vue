<template>
	<div class="space-y-4">
		<h1 class="h1 hidden md:block">Settings</h1>
		<div class="card p-5 space-y-3">
			<p class="text-ink-2 text-sm">Site settings (company-SIM sync, missed-call time limit, working hours,
				retention, AI keys) and sales teams are kept in Desk.</p>
			<div class="flex flex-wrap gap-2">
				<a class="btn-primary btn-sm" href="/app/cl-settings">Open settings</a>
				<a class="btn-ghost btn-sm" href="/app/cl-team">Sales teams</a>
				<a class="btn-ghost btn-sm" href="/app/cl-playback-log">Playback log</a>
			</div>
			<p class="muted">AI keys are stored encrypted on the server and are never sent to the phone app.</p>
		</div>
		<div class="card p-5 space-y-2">
			<div class="h2">Recordings stored</div>
			<div class="text-2xl font-bold num">{{ usage ? usage.human : "…" }}</div>
			<div class="muted">{{ usage ? usage.files + " recordings" : "" }} · deleted automatically after the retention period</div>
		</div>
		<div class="card p-5 space-y-3">
			<div class="h2">Erase one person's recordings</div>
			<p class="text-sm text-ink-2">When a customer asks for their data to be removed: every recording of calls with
				this number is deleted. The call entries stay, marked "Purged". This cannot be undone.</p>
			<div class="flex gap-2">
				<input v-model="erasePhone" class="input !h-9 max-w-xs" placeholder="Phone number" />
				<button class="btn-danger btn-sm" :disabled="!erasePhone" @click="erase">Erase</button>
			</div>
		</div>
	</div>
</template>
<script setup>
import { onMounted, ref } from "vue"
import { call, notify } from "../api"
const usage = ref(null), erasePhone = ref("")
onMounted(async () => { usage.value = await call("storage_usage") })
async function erase() {
	if (!confirm(`Delete every recording of calls with ${erasePhone.value}? This cannot be undone.`)) return
	const r = await call("erase_number", { phone: erasePhone.value })
	notify(`${r.erased} recording(s) erased.`)
	erasePhone.value = ""
	usage.value = await call("storage_usage")
}
</script>
