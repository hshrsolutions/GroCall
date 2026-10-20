<template>
	<router-view v-if="$route.meta.bare" />
	<div v-else class="min-h-screen md:flex">
		<!-- desktop sidebar -->
		<aside class="hidden md:flex md:w-60 shrink-0 flex-col border-r border-line bg-card min-h-screen sticky top-0">
			<div class="px-5 py-5 flex items-center gap-2.5">
				<span class="w-9 h-9 rounded-xl bg-accent text-accent-ink grid place-items-center">
					<Icon :d="phoneIcon" />
				</span>
				<div>
					<div class="font-bold leading-tight">{{ state.brand.name }}</div>
					<div class="text-xs text-ink-3">v{{ state.boot.version }}</div>
				</div>
			</div>
			<nav class="px-3 flex-1 space-y-0.5">
				<router-link v-for="r in nav" :key="r.path" :to="r.path"
					class="flex items-center gap-3 px-3 h-10 rounded-lg text-sm font-semibold text-ink-2 hover:bg-soft"
					active-class="!bg-accent-soft !text-accent">
					<Icon :d="r.meta.icon" />{{ r.meta.title }}
				</router-link>
			</nav>
			<div class="p-4 border-t border-line text-sm">
				<div class="font-semibold truncate">{{ state.boot.full_name }}</div>
				<div class="text-xs text-ink-3">{{ roleLabel }}</div>
				<a href="/app/grocall" v-if="state.perms.manager" class="text-xs text-accent font-semibold">Desk</a>
				<span v-if="state.perms.manager" class="text-ink-3 text-xs"> · </span>
				<a href="/?cmd=web_logout" class="text-xs text-ink-3">Sign out</a>
			</div>
		</aside>

		<div class="flex-1 min-w-0 pb-20 md:pb-0">
			<header class="md:hidden sticky top-0 z-10 bg-card/95 backdrop-blur border-b border-line px-4 h-14 flex items-center gap-2.5">
				<span class="w-8 h-8 rounded-lg bg-accent text-accent-ink grid place-items-center"><Icon :d="phoneIcon" /></span>
				<span class="font-bold">{{ $route.meta.title }}</span>
			</header>
			<main class="max-w-5xl mx-auto px-4 md:px-8 py-5 md:py-8">
				<router-view />
			</main>
		</div>

		<div class="fixed top-3 inset-x-0 z-50 flex flex-col items-center gap-2 pointer-events-none px-4">
			<div v-for="t in toasts" :key="t.id" class="card px-4 py-2.5 text-sm font-semibold shadow-card"
				:class="t.kind === 'error' ? '!border-bad text-bad' : ''">{{ t.message }}</div>
		</div>

		<!-- phone bottom bar: the first five allowed screens -->
		<nav class="md:hidden fixed bottom-0 inset-x-0 z-10 bg-card border-t border-line safe-bottom grid"
			:style="{ gridTemplateColumns: `repeat(${mobileNav.length}, minmax(0,1fr))` }">
			<router-link v-for="r in mobileNav" :key="r.path" :to="r.path"
				class="flex flex-col items-center justify-center gap-0.5 h-16 text-[11px] font-semibold text-ink-3"
				active-class="!text-accent">
				<Icon :d="r.meta.icon" />{{ r.meta.title }}
			</router-link>
		</nav>
	</div>
</template>

<script setup>
import { computed } from "vue"
import { routes } from "./router"
import { state } from "./store"
import { toasts } from "./api"
import Icon from "./components/Icon.vue"

const phoneIcon = "M3 5a2 2 0 012-2h3l2 5-2.5 1.5a11 11 0 005 5L14 12l5 2v3a2 2 0 01-2 2A16 16 0 013 5z"
const nav = computed(() => routes.filter((r) => r.meta?.nav && (!r.meta.perm || state.perms[r.meta.perm])))
const more = routes.find((r) => r.path === "/calls/more")
// phone bar holds five: past that, the fifth slot becomes "More" (the rest of the screens)
const mobileNav = computed(() => (nav.value.length > 5 ? [...nav.value.slice(0, 4), more] : nav.value))
const roleLabel = computed(() => (state.perms.admin ? "Admin" : state.perms.manager ? "Sales manager" : "Sales rep"))
</script>
