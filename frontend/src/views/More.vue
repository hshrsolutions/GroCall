<template>
	<div class="card overflow-hidden">
		<router-link v-for="r in rest" :key="r.path" :to="r.path" class="li-row">
			<Icon :d="r.meta.icon" /><span class="font-semibold flex-1">{{ r.meta.title }}</span>
		</router-link>
		<a href="/?cmd=web_logout" class="li-row text-ink-3">Sign out · {{ state.boot.full_name }}</a>
	</div>
</template>
<script setup>
import { computed } from "vue"
import { routes } from "../router"
import { state } from "../store"
import Icon from "../components/Icon.vue"
const rest = computed(() => routes.filter((r) => r.meta?.nav && (!r.meta.perm || state.perms[r.meta.perm])).slice(4))
</script>
