<!--
  Bottom-nav actualizada para usar la nueva pill flotante.
  Cambios mínimos respecto al original:
    - Wrap del badge de notificación adaptado a la pill (posición ajustada).
    - Sin cambios de lógica ni de rutas.
-->
<script lang="ts">
	import '../app.css';
	import { auth } from '$lib/stores/auth.svelte';
	import { pendingFriends } from '$lib/stores/friends.svelte';
	import { page } from '$app/state';

	let { children } = $props();

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
		{ href: '/exercises', label: 'Ejercicios', icon: '💪' },
		{ href: '/settings', label: 'Ajustes', icon: '⚙️' }
	];
</script>

<div class="container page">
	{@render children()}
</div>

{#if auth.isLoggedIn}
	<nav class="bottom" aria-label="Navegación principal">
		{#each nav as item}
			<a
				href={item.href}
				class:active={page.url.pathname === item.href}
				aria-current={page.url.pathname === item.href ? 'page' : undefined}
			>
				<span class="icon" aria-hidden="true">{item.icon}</span>
				<span>{item.label}</span>
				{#if item.href === '/settings' && pendingFriends.count > 0}
					<span class="nav-badge" aria-label="{pendingFriends.count} solicitudes pendientes">
						{pendingFriends.count}
					</span>
				{/if}
			</a>
		{/each}
	</nav>
{/if}

<style>
	.nav-badge {
		position: absolute;
		top: 2px;
		right: 6px;
		background: var(--danger);
		color: #fff;
		border-radius: 99px;
		font-size: 0.55rem;
		font-weight: 800;
		padding: 0.08rem 0.35rem;
		line-height: 1.4;
		pointer-events: none;
		box-shadow: 0 2px 6px rgba(0, 0, 0, 0.4);
	}
	nav.bottom a { position: relative; }
</style>
