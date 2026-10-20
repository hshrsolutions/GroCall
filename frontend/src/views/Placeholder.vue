<template>
	<div class="space-y-4">
		<h1 class="h1 hidden md:block">{{ $route.meta.title }}</h1>
		<div class="card p-8 text-center space-y-2">
			<span class="chip-accent">Arrives in Phase {{ $route.meta.phase }}</span>
			<p class="text-ink-2 max-w-md mx-auto">{{ $route.meta.blurb }}</p>
		</div>
	</div>
</template>
