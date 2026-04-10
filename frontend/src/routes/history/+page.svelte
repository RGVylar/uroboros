<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { DaySummary } from '$lib/types';

	if (!auth.isLoggedIn) goto('/login');

	// Calendar state
	const now = new Date();
	let viewYear = $state(now.getFullYear());
	let viewMonth = $state(now.getMonth()); // 0-indexed
	let selectedDay: string | null = $state(null);
	let selectedSummary: DaySummary | null = $state(null);
	let loadingDay = $state(false);

	// Cache of daily calorie totals for the current month
	let monthData: Record<string, number> = $state({});
	let loadingMonth = $state(false);

	const MONTH_NAMES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
	const DAY_NAMES = ['L','M','X','J','V','S','D'];

	function getDaysInMonth(year: number, month: number) {
		return new Date(year, month + 1, 0).getDate();
	}

	function getFirstDayOfWeek(year: number, month: number) {
		// Monday=0, Sunday=6
		let d = new Date(year, month, 1).getDay();
		return (d + 6) % 7;
	}

	function formatDay(year: number, month: number, day: number): string {
		const m = String(month + 1).padStart(2, '0');
		const d = String(day).padStart(2, '0');
		return `${year}-${m}-${d}`;
	}

	async function loadMonthData() {
		loadingMonth = true;
		monthData = {};
		const days = getDaysInMonth(viewYear, viewMonth);
		// Batch fetch all days in the month
		const promises = Array.from({ length: days }, (_, i) => {
			const date = formatDay(viewYear, viewMonth, i + 1);
			return api.get<DaySummary>(`/diary/day?day=${date}`)
				.then(s => ({ date, calories: s.totals.calories }))
				.catch(() => ({ date, calories: 0 }));
		});
		const results = await Promise.all(promises);
		const newData: Record<string, number> = {};
		for (const r of results) {
			if (r.calories > 0) newData[r.date] = r.calories;
		}
		monthData = newData;
		loadingMonth = false;
	}

	async function selectDay(date: string) {
		if (selectedDay === date) {
			selectedDay = null;
			selectedSummary = null;
			return;
		}
		selectedDay = date;
		loadingDay = true;
		try {
			selectedSummary = await api.get<DaySummary>(`/diary/day?day=${date}`);
		} catch {
			selectedSummary = null;
		} finally {
			loadingDay = false;
		}
	}

	function prevMonth() {
		if (viewMonth === 0) { viewMonth = 11; viewYear--; }
		else viewMonth--;
		selectedDay = null;
		selectedSummary = null;
		loadMonthData();
	}

	function nextMonth() {
		const today = new Date();
		if (viewYear === today.getFullYear() && viewMonth === today.getMonth()) return;
		if (viewMonth === 11) { viewMonth = 0; viewYear++; }
		else viewMonth++;
		selectedDay = null;
		selectedSummary = null;
		loadMonthData();
	}

	function isToday(date: string) {
		return date === new Date().toISOString().slice(0, 10);
	}

	function isFuture(year: number, month: number, day: number) {
		const d = new Date(year, month, day);
		const t = new Date(); t.setHours(0,0,0,0);
		return d > t;
	}

	function calColor(kcal: number): string {
		if (kcal <= 0) return 'transparent';
		if (kcal < 1200) return 'rgba(79,255,153,0.25)';
		if (kcal < 1800) return 'rgba(79,255,153,0.45)';
		if (kcal < 2400) return 'rgba(79,255,153,0.65)';
		return 'rgba(79,255,153,0.85)';
	}

	function fmtTime(iso: string) {
		return new Date(iso).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' });
	}

	// Load on mount and month change
	$effect(() => { viewMonth; viewYear; loadMonthData(); });

	// Calendar grid
	let calendarDays = $derived.by(() => {
		const days = getDaysInMonth(viewYear, viewMonth);
		const firstDow = getFirstDayOfWeek(viewYear, viewMonth);
		const cells: Array<{ day: number | null; date: string | null }> = [];
		for (let i = 0; i < firstDow; i++) cells.push({ day: null, date: null });
		for (let d = 1; d <= days; d++) {
			cells.push({ day: d, date: formatDay(viewYear, viewMonth, d) });
		}
		// Pad to full weeks
		while (cells.length % 7 !== 0) cells.push({ day: null, date: null });
		return cells;
	});

	let isCurrentMonth = $derived(
		viewYear === now.getFullYear() && viewMonth === now.getMonth()
	);
</script>

<h1>Historial</h1>

<!-- Month navigation -->
<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:1rem;">
	<button class="btn-secondary" onclick={prevMonth} style="padding:0.4rem 0.8rem;">◀</button>
	<span style="font-weight:700; font-size:1rem;">{MONTH_NAMES[viewMonth]} {viewYear}</span>
	<button class="btn-secondary" onclick={nextMonth} style="padding:0.4rem 0.8rem;" disabled={isCurrentMonth}>▶</button>
</div>

<!-- Day headers -->
<div style="display:grid; grid-template-columns:repeat(7,1fr); gap:2px; margin-bottom:4px;">
	{#each DAY_NAMES as name}
		<div style="text-align:center; font-size:0.7rem; color:var(--text-muted); font-weight:600; padding:0.25rem 0;">{name}</div>
	{/each}
</div>

<!-- Calendar grid -->
<div class="card" style="padding:0.5rem;">
	{#if loadingMonth}
		<p style="text-align:center; color:var(--text-muted); padding:2rem 0; font-size:0.85rem;">Cargando...</p>
	{:else}
		<div style="display:grid; grid-template-columns:repeat(7,1fr); gap:3px;">
			{#each calendarDays as cell}
				{#if cell.day === null}
					<div></div>
				{:else if isFuture(viewYear, viewMonth, cell.day)}
					<div style="
						aspect-ratio:1;
						display:flex;
						flex-direction:column;
						align-items:center;
						justify-content:center;
						border-radius:6px;
						opacity:0.2;
						font-size:0.8rem;
					">{cell.day}</div>
				{:else}
					{@const hasData = cell.date && monthData[cell.date] > 0}
					{@const isSelected = cell.date === selectedDay}
					{@const isTodayCell = cell.date ? isToday(cell.date) : false}
					<button
						onclick={() => cell.date && selectDay(cell.date)}
						style="
							aspect-ratio:1;
							display:flex;
							flex-direction:column;
							align-items:center;
							justify-content:center;
							border-radius:6px;
							border: {isSelected ? '2px solid var(--primary)' : isTodayCell ? '1px solid var(--primary)' : '1px solid transparent'};
							background: {isSelected ? 'rgba(79,255,153,0.15)' : hasData && cell.date ? calColor(monthData[cell.date]) : 'var(--surface2)'};
							cursor:pointer;
							padding:0;
							font-size:0.8rem;
							font-weight: {isTodayCell ? '700' : '400'};
							color: {isTodayCell ? 'var(--primary)' : 'var(--text)'};
							transition: border-color 0.15s;
						">
						<span>{cell.day}</span>
						{#if hasData && cell.date}
							<span style="font-size:0.6rem; color:var(--text-muted); line-height:1;">{Math.round(monthData[cell.date])}k</span>
						{/if}
					</button>
				{/if}
			{/each}
		</div>
	{/if}
</div>

<!-- Legend -->
<div style="display:flex; gap:0.75rem; align-items:center; margin:0.75rem 0; font-size:0.72rem; color:var(--text-muted);">
	<span>Intensidad:</span>
	{#each ['<1200','1200-1800','1800-2400','>2400'] as label, i}
		<span style="display:flex; align-items:center; gap:3px;">
			<span style="width:12px; height:12px; border-radius:3px; background:{['rgba(79,255,153,0.25)','rgba(79,255,153,0.45)','rgba(79,255,153,0.65)','rgba(79,255,153,0.85)'][i]}; display:inline-block;"></span>
			{label}
		</span>
	{/each}
</div>

<!-- Day detail -->
{#if selectedDay}
	<div style="margin-top:0.5rem;">
		<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
			<h2 style="margin:0;">{new Date(selectedDay + 'T12:00').toLocaleDateString('es', { weekday:'long', day:'numeric', month:'long' })}</h2>
			<a href="/" onclick={() => { localStorage.setItem('diaryDate', selectedDay ?? ''); }} style="font-size:0.8rem;">Ver diario →</a>
		</div>

		{#if loadingDay}
			<p style="color:var(--text-muted); font-size:0.85rem;">Cargando...</p>
		{:else if selectedSummary && selectedSummary.entries.length > 0}
			<!-- Totals -->
			<div class="card" style="margin-bottom:0.75rem;">
				<div class="macro-grid">
					<div>
						<div class="label">Kcal</div>
						<div class="value" style="color:var(--cal);">{Math.round(selectedSummary.totals.calories)}</div>
					</div>
					<div>
						<div class="label">Prot</div>
						<div class="value" style="color:var(--prot);">{Math.round(selectedSummary.totals.protein)}g</div>
					</div>
					<div>
						<div class="label">Carb</div>
						<div class="value" style="color:var(--carb);">{Math.round(selectedSummary.totals.carbs)}g</div>
					</div>
					<div>
						<div class="label">Grasa</div>
						<div class="value" style="color:var(--fat);">{Math.round(selectedSummary.totals.fat)}g</div>
					</div>
				</div>
			</div>

			<!-- Entries by meal -->
			{#each selectedSummary.meals as meal (meal.meal_type)}
				<div style="margin-bottom:0.75rem;">
					<div style="display:flex; justify-content:space-between; margin-bottom:0.3rem; padding:0 0.25rem;">
						<span style="font-weight:700; font-size:0.85rem;">{meal.label}</span>
						<span style="font-size:0.8rem; color:var(--cal);">{Math.round(meal.totals.calories)} kcal</span>
					</div>
					{#each meal.entries as entry (entry.id)}
						<div class="card" style="margin-bottom:0.3rem; padding:0.6rem; display:flex; justify-content:space-between; align-items:center;">
							<div>
								<div style="font-size:0.85rem; font-weight:600;">{entry.product?.name ?? `Producto #${entry.product_id}`}</div>
								<div style="font-size:0.75rem; color:var(--text-muted);">{entry.grams}g · {fmtTime(entry.consumed_at)}</div>
							</div>
							<div style="text-align:right;">
								<div style="font-size:0.82rem; color:var(--cal);">{Math.round(entry.calories)} kcal</div>
								<div style="font-size:0.7rem; color:var(--text-muted);">P{Math.round(entry.protein)} C{Math.round(entry.carbs)} G{Math.round(entry.fat)}</div>
							</div>
						</div>
					{/each}
				</div>
			{/each}
		{:else}
			<p style="text-align:center; color:var(--text-muted); padding:1rem 0; font-size:0.85rem;">Sin registros este día.</p>
		{/if}
	</div>
{/if}
