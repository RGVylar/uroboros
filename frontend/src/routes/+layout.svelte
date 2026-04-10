<script lang="ts">
	import '../app.css';
	import { auth } from '$lib/stores/auth.svelte';
	import { page } from '$app/state';

	let { children } = $props();

	const nav = [
		{ href: '/', label: 'Diario', icon: '📋' },
		{ href: '/add', label: 'Añadir', icon: '➕' },
		{ href: '/weight', label: 'Peso', icon: '⚖️' },
		{ href: '/goals', label: 'Metas', icon: '🎯' },
		{ href: '/settings', label: 'Config', icon: '⚙️' }
	];
</script>

<div class="container page">
	{@render children()}
</div>

{#if auth.isLoggedIn}
	<nav class="bottom">
		{#each nav as item}
			<a href={item.href} class:active={page.url.pathname === item.href}>
				<span class="icon">{item.icon}</span>
				{item.label}
			</a>
		{/each}
	</nav>
{/if}
