<template>
	<div class="min-h-screen grid place-items-center px-4">
		<div class="card p-8 max-w-sm text-center space-y-3">
			<div class="h2">No access to {{ state.brand.name }}</div>
			<p class="text-ink-2 text-sm">You are signed in as <b>{{ state.boot.user }}</b>, but this account has no
				GroCall role. Ask your administrator to give you <b>CL Sales Rep</b>.</p>
			<a class="btn-ghost btn-sm" href="/?cmd=web_logout">Sign in as someone else</a>
		</div>
	</div>
</template>
<script setup>
import { state } from "../store"
</script>
