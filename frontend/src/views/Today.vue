<template>
	<div class="space-y-5">
		<div>
			<h1 class="h1">Hello, {{ firstName }}</h1>
			<p class="muted">Your calls, follow-ups and missed calls will show here.</p>
		</div>
		<div class="grid grid-cols-2 md:grid-cols-4 gap-3">
			<div v-for="k in kpis" :key="k" class="card p-4">
				<div class="label">{{ k }}</div>
				<div class="text-2xl font-bold num text-ink-3">—</div>
			</div>
		</div>
		<div class="card p-5 space-y-2">
			<div class="h2">Getting started</div>
			<ol class="list-decimal ml-5 text-sm text-ink-2 space-y-1">
				<li>An admin sets up teams and settings (Desk → GroCall).</li>
				<li>Each salesperson installs the GroCall phone app and pairs it with a QR code from <b>Phones</b>.</li>
				<li>They pick the <b>company SIM</b>; only calls on that SIM are tracked.</li>
				<li>Calls, recordings and follow-ups start appearing here.</li>
			</ol>
			<p class="muted pt-1">GroCall is being built in phases. This is Phase 0: the shell, roles and settings.
				Data screens arrive in the phases shown on each page.</p>
		</div>
	</div>
</template>
<script setup>
import { computed } from "vue"
import { state } from "../store"
const firstName = computed(() => (state.boot.full_name || "").split(" ")[0] || "there")
const kpis = ["Calls today", "Talk time", "Missed, not returned", "Follow-ups due"]
</script>
