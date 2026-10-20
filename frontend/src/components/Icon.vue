<template>
	<svg class="w-5 h-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
		stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="d" /></svg>
</template>
<script setup>
defineProps({ d: { type: String, required: true } })
</script>
