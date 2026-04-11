<script lang="ts">
	import '../app.css';
	import { auth } from '$lib/stores/auth.svelte';
	import { pendingFriends } from '$lib/stores/friends.svelte';
	import { page } from '$app/state';

	let { children } = $props();

	// Start polling for pending friend requests once logged in
	$effect(() => {
		if (auth.isLoggedIn) {
			pendingFriends.start();
		} else {
			pendingFriends.stop();
		}
	});

	const nav = [
		{ href: '/', label: 'Diario', icon: '📋' },
		{ href: '/history', label: 'Historial', icon: '📅' },
		{ href: '/recipes', label: 'Recetas', icon: '🍳' },
		{ href: '/settings', label: 'Ajustes', icon: '⚙️' }
	];
</script>

<div class="container page">
	{@render children()}
</div>

{#if auth.isLoggedIn}
	<nav class="bottom">
		{#each nav as item}
			<a href={item.href} class:active={page.url.pathname === item.href} style="position:relative;">
				<span class="icon">{item.icon}</span>
				{item.label}
				{#if item.href === '/settings' && pendingFriends.count > 0}
					<span style="
						position:absolute; top:2px; right:2px;
						background:var(--danger); color:#fff;
						border-radius:99px; font-size:0.55rem; font-weight:800;
						padding:0.05rem 0.3rem; line-height:1.4;
						pointer-events:none;
					">{pendingFriends.count}</span>
				{/if}
			</a>
		{/each}
	</nav>
{/if}
