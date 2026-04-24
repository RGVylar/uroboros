<!--
  DayNav.svelte
  Navegador de día con flechas + fecha grande + streak badge.
  Para Diario e Historial.

  Uso:
    <DayNav
      bind:date={today}
      streak={streak}
      showStreakOnToday
    />
-->
<script lang="ts">
	interface Props {
		date: string;
		streak?: number;
		showStreakOnToday?: boolean;
		onChange?: (newDate: string) => void;
	}
	let {
		date = $bindable(),
		streak = 0,
		showStreakOnToday = true,
		onChange,
	}: Props = $props();

	let isToday = $derived(date === new Date().toISOString().slice(0, 10));

	function change(delta: number) {
		const d = new Date(date + 'T12:00');
		d.setDate(d.getDate() + delta);
		const next = d.toISOString().slice(0, 10);
		date = next;
		onChange?.(next);
	}

	function fmt(iso: string): string {
		if (iso === new Date().toISOString().slice(0, 10)) return 'Hoy';
		return new Date(iso + 'T12:00').toLocaleDateString('es', {
			weekday: 'short',
			day: 'numeric',
			month: 'short',
		});
	}
</script>

<nav class="day-nav" aria-label="Navegación de día">
	<button class="arrow" aria-label="Día anterior" onclick={() => change(-1)}>◀</button>
	<div class="center">
		<div class="date">{fmt(date)}</div>
		{#if isToday && showStreakOnToday && streak > 0}
			<div class="streak">🔥 {streak} {streak === 1 ? 'día' : 'días'}</div>
		{/if}
	</div>
	<button
		class="arrow"
		class:ghost={isToday}
		aria-label="Día siguiente"
		onclick={() => change(1)}
		disabled={isToday}
	>▶</button>
</nav>

<style>
	.day-nav {
		display: grid;
		grid-template-columns: auto 1fr auto;
		align-items: center;
		gap: 0.5rem;
		padding: 0.25rem 0 0.9rem;
	}
	.arrow {
		background: var(--surface);
		border: 1px solid var(--border);
		color: var(--text-muted);
		box-shadow: none;
		padding: 0.55rem 0.8rem;
		border-radius: 999px;
		font-weight: 700;
		font-size: 0.85rem;
		backdrop-filter: var(--blur-s);
		-webkit-backdrop-filter: var(--blur-s);
	}
	.arrow:hover { background: var(--surface-hover); color: var(--text); filter: none; box-shadow: none; }
	.arrow:disabled, .arrow.ghost {
		opacity: 0.35;
		cursor: default;
	}
	.center { text-align: center; }
	.date {
		font-size: 1.1rem;
		font-weight: 800;
		letter-spacing: -0.01em;
		text-transform: capitalize;
	}
	.streak {
		font-size: 0.72rem;
		color: var(--primary);
		margin-top: 0.15rem;
		font-weight: 700;
		letter-spacing: 0.02em;
	}
</style>
