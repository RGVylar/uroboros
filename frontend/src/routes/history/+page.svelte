<script lang="ts">
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte';
	import { api } from '$lib/api';
	import type { DaySummary, Goals } from '$lib/types';
	import { MealHeader } from '$lib/components';

	function exportCSV(month?: boolean) {
		const token = auth.token;
		let url = '/api/diary/export.csv';
		if (month) {
			const from = `${viewYear}-${String(viewMonth + 1).padStart(2, '0')}-01`;
			const lastDay = new Date(viewYear, viewMonth + 1, 0).getDate();
			const to = `${viewYear}-${String(viewMonth + 1).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`;
			url += `?date_from=${from}&date_to=${to}`;
		}
		fetch(url, { headers: { Authorization: `Bearer ${token}` } })
			.then(r => r.blob())
			.then(blob => {
				const a = document.createElement('a');
				a.href = URL.createObjectURL(blob);
				a.download = month
					? `uroboros_${viewYear}-${String(viewMonth + 1).padStart(2, '0')}.csv`
					: 'uroboros_historial.csv';
				a.click();
				URL.revokeObjectURL(a.href);
			});
	}

	if (!auth.isLoggedIn) goto('/login');

	// Calendar state
	const now = new Date();
	let viewYear = $state(now.getFullYear());
	let viewMonth = $state(now.getMonth());
	let selectedDay: string | null = $state(null);
	let selectedSummary: DaySummary | null = $state(null);
	let loadingDay = $state(false);

	// Calendar data
	let monthData: Record<string, number> = $state({});
	let loadingMonth = $state(false);
	let creatineDates: Set<string> = $state(new Set());
	let exerciseDates: Set<string> = $state(new Set());
	let trackCreatine = $state(false);

	// Goals (for reference line)
	let goals: Goals | null = $state(null);

	// Trend chart state
	type TrendEntry = { date: string; calories: number; protein: number; carbs: number; fat: number };
	type TrendMacro = 'calories' | 'protein' | 'carbs' | 'fat';
	let trendDays: 7 | 30 = $state(7);
	let trendMacro: TrendMacro = $state('calories');
	let trendData: TrendEntry[] = $state([]);
	let loadingTrend = $state(false);

	const MACRO_CONFIG: Record<TrendMacro, { label: string; color: string; unit: string }> = {
		calories: { label: 'Calorías', color: 'var(--cal)',  unit: 'kcal' },
		protein:  { label: 'Proteína', color: 'var(--prot)', unit: 'g' },
		carbs:    { label: 'Carbos',   color: 'var(--carb)', unit: 'g' },
		fat:      { label: 'Grasa',    color: 'var(--fat)',  unit: 'g' },
	};

	const MONTH_NAMES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
	const DAY_NAMES = ['L','M','X','J','V','S','D'];

	function getDaysInMonth(year: number, month: number) {
		return new Date(year, month + 1, 0).getDate();
	}
	function getFirstDayOfWeek(year: number, month: number) {
		let d = new Date(year, month, 1).getDay();
		return (d + 6) % 7;
	}
	function formatDay(year: number, month: number, day: number): string {
		const m = String(month + 1).padStart(2, '0');
		const d = String(day).padStart(2, '0');
		return `${year}-${m}-${d}`;
	}

	async function loadTrendData() {
		loadingTrend = true;
		const today = new Date();
		const dates: string[] = [];
		for (let i = trendDays - 1; i >= 0; i--) {
			const d = new Date(today);
			d.setDate(d.getDate() - i);
			dates.push(d.toISOString().slice(0, 10));
		}
		trendData = await Promise.all(
			dates.map(date =>
				api.get<DaySummary>(`/diary/day?day=${date}`)
					.then(s => ({
						date,
						calories: s.totals.calories,
						protein:  s.totals.protein,
						carbs:    s.totals.carbs,
						fat:      s.totals.fat,
					}))
					.catch(() => ({ date, calories: 0, protein: 0, carbs: 0, fat: 0 }))
			)
		);
		loadingTrend = false;
	}

	async function loadMonthData() {
		loadingMonth = true;
		monthData = {};
		const days = getDaysInMonth(viewYear, viewMonth);
		const diaryPromises = Array.from({ length: days }, (_, i) => {
			const date = formatDay(viewYear, viewMonth, i + 1);
			return api.get<DaySummary>(`/diary/day?day=${date}`)
				.then(s => ({ date, calories: s.totals.calories, has_exercise: s.has_exercise }))
				.catch(() => ({ date, calories: 0, has_exercise: false }));
		});
		const creatinePromise = trackCreatine
			? api.get<string[]>(`/creatine/month?year=${viewYear}&month=${viewMonth + 1}`).catch(() => [])
			: Promise.resolve([]);
		const [results, creatineDatesArr] = await Promise.all([
			Promise.all(diaryPromises),
			creatinePromise,
		]);
		const newData: Record<string, number> = {};
		const newExerciseDates = new Set<string>();
		for (const r of results) {
			if (r.calories > 0) newData[r.date] = r.calories;
			if (r.has_exercise) newExerciseDates.add(r.date);
		}
		monthData = newData;
		creatineDates = new Set(creatineDatesArr);
		exerciseDates = newExerciseDates;
		loadingMonth = false;
	}

	async function selectDay(date: string) {
		if (selectedDay === date) { selectedDay = null; selectedSummary = null; return; }
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
		selectedDay = null; selectedSummary = null;
		loadMonthData();
	}
	function nextMonth() {
		const today = new Date();
		if (viewYear === today.getFullYear() && viewMonth === today.getMonth()) return;
		if (viewMonth === 11) { viewMonth = 0; viewYear++; }
		else viewMonth++;
		selectedDay = null; selectedSummary = null;
		loadMonthData();
	}

	function isToday(date: string) { return date === now.toISOString().slice(0, 10); }
	function isFuture(year: number, month: number, day: number) {
		const d = new Date(year, month, day);
		const t = new Date(); t.setHours(0, 0, 0, 0);
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

	// SVG chart helpers
	const CHART_W = 300;
	const CHART_BAR_H = 80;   // coordinate units for bar area
	const CHART_LABEL_H = 18; // coordinate units for bottom labels
	const CHART_TOTAL_H = CHART_BAR_H + CHART_LABEL_H;

	function chartSlotW(n: number) { return CHART_W / n; }
	function chartBarW(n: number) { return n <= 7 ? chartSlotW(n) * 0.65 : chartSlotW(n) * 0.7; }

	function barH(val: number, maxVal: number): number {
		if (maxVal === 0) return 0;
		return (val / maxVal) * CHART_BAR_H * 0.9;
	}

	function chartGoalVal(): number | null {
		if (trendMacro === 'calories' && goals?.kcal) return goals.kcal;
		if (trendMacro === 'protein' && goals?.protein) return goals.protein;
		if (trendMacro === 'carbs' && goals?.carbs) return goals.carbs;
		if (trendMacro === 'fat' && goals?.fat) return goals.fat;
		return null;
	}

	let trendValues = $derived(trendData.map(d => d[trendMacro]));
	let trendMax = $derived.by(() => {
		const dataMax = Math.max(...trendValues, 1);
		const goalVal = chartGoalVal();
		return goalVal ? Math.max(dataMax, goalVal * 1.05) : dataMax;
	});
	let trendNonZero = $derived(trendValues.filter(v => v > 0));
	let trendAvg = $derived(trendNonZero.length ? Math.round(trendNonZero.reduce((a, b) => a + b, 0) / trendNonZero.length) : 0);
	let trendPeak = $derived(Math.round(Math.max(...trendValues, 0)));

	function showDateLabel(i: number, n: number): string {
		const date = trendData[i]?.date;
		if (!date) return '';
		const day = parseInt(date.slice(8));
		if (n <= 7) return String(day);                   // show every day
		if (i === 0 || i === n - 1 || day % 7 === 0) return String(day); // show periodically
		return '';
	}

	// Effects
	$effect(() => {
		api.get<Goals>('/goals')
			.then(g => { goals = g; trackCreatine = g.track_creatine ?? false; })
			.catch(() => {});
	});
	$effect(() => { viewMonth; viewYear; trackCreatine; loadMonthData(); });
	$effect(() => { trendDays; loadTrendData(); });

	let calendarDays = $derived.by(() => {
		const days = getDaysInMonth(viewYear, viewMonth);
		const firstDow = getFirstDayOfWeek(viewYear, viewMonth);
		const cells: Array<{ day: number | null; date: string | null }> = [];
		for (let i = 0; i < firstDow; i++) cells.push({ day: null, date: null });
		for (let d = 1; d <= days; d++) cells.push({ day: d, date: formatDay(viewYear, viewMonth, d) });
		while (cells.length % 7 !== 0) cells.push({ day: null, date: null });
		return cells;
	});
	let isCurrentMonth = $derived(viewYear === now.getFullYear() && viewMonth === now.getMonth());
	let adherenceDays = $derived(trendData.filter(d => goals?.kcal ? Math.abs(d.calories - goals.kcal) < 250 : false).length);
</script>

<!-- ── Header ── -->
<div style="display:flex; align-items:center; gap:0.75rem; padding:0.25rem 0 1rem;">
	<button onclick={() => goto('/')} style="width:36px; height:36px; border-radius:50%; background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.1); display:flex; align-items:center; justify-content:center; color:#fff; cursor:pointer; padding:0; font-family:inherit; flex-shrink:0; font-size:1rem;">←</button>
	<div style="flex:1; min-width:0;">
		<h1 style="font-size:1.875rem; font-weight:400; letter-spacing:-0.05em; color:#fff; line-height:1; margin:0; font-family:'Lora','Georgia',serif;">Historial</h1>
		<div style="font-size:0.6875rem; color:rgba(255,255,255,0.5); margin-top:0.25rem;">Últimos 7 días</div>
	</div>
	<div style="display:flex; gap:0.3rem;">
		<button class="csv-btn" onclick={() => exportCSV(true)}>CSV mes</button>
		<button class="csv-btn" onclick={() => exportCSV(false)}>CSV todo</button>
	</div>
</div>

{#if loadingTrend}
	<p style="text-align:center; color:rgba(255,255,255,0.4); padding:3rem 0; font-size:0.85rem;">Cargando...</p>
{:else}

<!-- ── Summary stats ── -->
<div style="display:grid; grid-template-columns:1fr 1fr; gap:0.625rem; margin-bottom:0.625rem;">
	<!-- Media kcal -->
	<div class="glass-card">
		<div class="stat-eyebrow">Media kcal</div>
		<div style="display:flex; align-items:baseline; gap:0.25rem; margin-top:0.5rem;">
			<div style="font-size:1.75rem; font-weight:700; color:#fff; letter-spacing:-0.05em;">{trendAvg.toLocaleString('es-ES')}</div>
			<div style="font-size:0.625rem; color:rgba(255,255,255,0.4);">kcal</div>
		</div>
		{#if goals?.kcal}
			<div style="font-size:0.625rem; color:oklch(85% 0.17 160); font-weight:700; margin-top:0.25rem;">
				{trendAvg < goals.kcal ? '↓' : '↑'} {Math.abs(trendAvg - goals.kcal)} vs objetivo
			</div>
		{/if}
	</div>
	<!-- Adherencia -->
	<div class="glass-card">
		<div class="stat-eyebrow">Adherencia</div>
		<div style="display:flex; align-items:baseline; gap:0.25rem; margin-top:0.5rem;">
			<div style="font-size:1.75rem; font-weight:700; color:#fff; letter-spacing:-0.05em;">{trendData.length > 0 ? Math.round(adherenceDays / trendData.length * 100) : 0}</div>
			<div style="font-size:0.625rem; color:rgba(255,255,255,0.4);">%</div>
		</div>
		<div style="font-size:0.625rem; color:rgba(255,255,255,0.55); margin-top:0.25rem;">
			{adherenceDays} de {trendData.length} días en rango
		</div>
	</div>
</div>

<!-- ── Bar chart ── -->
<div class="glass-card" style="margin-bottom:0.625rem;">
	<div style="font-size:0.75rem; color:rgba(255,255,255,0.7); font-weight:600; margin-bottom:0.875rem;">Calorías por día</div>
	{#if trendData.length > 0}
		{@const goalKcal = goals?.kcal ?? 0}
		{@const maxCal = Math.max(...trendData.map(d => d.calories), goalKcal, 1)}
		{@const BAR_MAX_PX = 90}
		<div style="display:flex; align-items:flex-end; gap:0.375rem;">
			{#each trendData as d, i}
				{@const pct = Math.min(100, (d.calories / maxCal) * 100)}
				{@const barPx = Math.max(d.calories > 0 ? 4 : 2, Math.round((pct / 100) * BAR_MAX_PX))}
				{@const over = goalKcal > 0 && d.calories > goalKcal + 100}
				{@const under = goalKcal > 0 && d.calories > 0 && d.calories < goalKcal - 350}
				{@const dayLabel = (() => { const dt = new Date(d.date + 'T12:00'); const names = ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb']; return names[dt.getDay()].slice(0,3); })()}
				<div style="flex:1; display:flex; flex-direction:column; align-items:center; gap:0.25rem;">
					<div style="font-size:0.5rem; color:{d.calories > 0 ? 'rgba(255,255,255,0.4)' : 'transparent'}; line-height:1; min-height:0.625rem;">{d.calories > 0 ? Math.round(d.calories) : '·'}</div>
					<div style="width:100%; border-radius:6px; height:{barPx}px; background:{d.calories === 0 ? 'rgba(255,255,255,0.06)' : over ? 'linear-gradient(180deg, oklch(75% 0.18 30), oklch(55% 0.2 20))' : under ? 'linear-gradient(180deg, oklch(75% 0.13 270), oklch(55% 0.15 270))' : 'linear-gradient(180deg, oklch(85% 0.18 160), oklch(65% 0.2 180))'}; box-shadow:{d.calories > 0 ? 'inset 0 1px 0 rgba(255,255,255,0.25)' : 'none'}; transition:height 0.3s ease;"></div>
					<div style="font-size:0.625rem; color:rgba(255,255,255,0.55); font-weight:600;">{dayLabel}</div>
				</div>
			{/each}
		</div>
		<!-- Legend -->
		<div style="display:flex; gap:0.75rem; margin-top:0.875rem; font-size:0.625rem; color:rgba(255,255,255,0.45);">
			<div style="display:flex; align-items:center; gap:0.3rem;"><div style="width:8px; height:8px; border-radius:2px; background:oklch(75% 0.18 180);"></div> En rango</div>
			<div style="display:flex; align-items:center; gap:0.3rem;"><div style="width:8px; height:8px; border-radius:2px; background:oklch(65% 0.18 30);"></div> Exceso</div>
			<div style="display:flex; align-items:center; gap:0.3rem;"><div style="width:8px; height:8px; border-radius:2px; background:oklch(65% 0.14 270);"></div> Déficit</div>
		</div>
	{/if}
</div>

<!-- ── Day list ── -->
<div style="font-size:0.6875rem; letter-spacing:0.08em; text-transform:uppercase; color:rgba(255,255,255,0.45); font-weight:700; margin:1.25rem 0.25rem 0.625rem;">Días</div>
<div class="glass-card" style="padding:0.375rem;">
	{#each [...trendData].reverse() as d, i}
		{@const goalKcal2 = goals?.kcal ?? 0}
		{@const over2 = goalKcal2 > 0 && d.calories > goalKcal2 + 100}
		{@const under2 = goalKcal2 > 0 && d.calories > 0 && d.calories < goalKcal2 - 350}
		{@const statusColor = over2 ? 'oklch(75% 0.18 30)' : under2 ? 'oklch(75% 0.13 270)' : 'oklch(85% 0.17 160)'}
		{@const isSelected = selectedDay === d.date}
		<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
		<div
			onclick={() => selectDay(d.date)}
			style="display:flex; align-items:center; gap:0.75rem; padding:0.75rem 0.875rem; border-bottom:{i < trendData.length-1 ? '1px solid rgba(255,255,255,0.05)' : 'none'}; cursor:pointer; border-radius:12px; background:{isSelected ? 'rgba(255,255,255,0.05)' : 'transparent'};"
		>
			<!-- Date box -->
			<div style="width:42px; height:42px; border-radius:12px; background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); display:flex; flex-direction:column; align-items:center; justify-content:center; flex-shrink:0;">
				<div style="font-size:0.5625rem; color:rgba(255,255,255,0.4); line-height:1;">{d.date.slice(5,7)}</div>
				<div style="font-size:0.875rem; font-weight:700; color:#fff; line-height:1;">{d.date.slice(8,10)}</div>
			</div>
			<div style="flex:1; min-width:0;">
				<div style="font-size:0.8125rem; font-weight:600; display:flex; align-items:center; gap:0.375rem;">
					{isToday(d.date) ? 'Hoy' : new Date(d.date + 'T12:00').toLocaleDateString('es', { weekday:'short' })}
					<div style="width:6px; height:6px; border-radius:99px; background:{d.calories > 0 ? statusColor : 'rgba(255,255,255,0.2)'};"></div>
				</div>
				<div style="font-size:0.625rem; color:rgba(255,255,255,0.4); margin-top:0.125rem;">
					{d.calories > 0 ? `${Math.round(d.calories)} kcal · P ${Math.round(d.protein)}g · C ${Math.round(d.carbs)}g · G ${Math.round(d.fat)}g` : 'Sin registros'}
				</div>
			</div>
			<div style="font-size:0.625rem; color:rgba(255,255,255,0.3);">›</div>
		</div>
	{/each}
</div>

<!-- ── Day detail ── -->
{#if selectedDay}
	<div style="margin-top:1rem;">
		<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
			<div style="font-size:0.9375rem; font-weight:700; color:#fff;">
				{new Date(selectedDay + 'T12:00').toLocaleDateString('es', { weekday:'long', day:'numeric', month:'long' })}
			</div>
			<a href="/" onclick={() => { localStorage.setItem('diaryDate', selectedDay ?? ''); }} style="font-size:0.75rem; color:oklch(85% 0.17 160);">Ver diario →</a>
		</div>
		{#if loadingDay}
			<p style="color:rgba(255,255,255,0.45); font-size:0.85rem; text-align:center; padding:1rem 0;">Cargando...</p>
		{:else if selectedSummary && selectedSummary.entries.length > 0}
			<div class="glass-card" style="margin-bottom:0.75rem;">
				<div style="display:grid; grid-template-columns:repeat(4,1fr); gap:0.5rem;">
					<div style="text-align:center;">
						<div class="stat-eyebrow">Kcal</div>
						<div style="font-size:1.125rem; font-weight:800; margin-top:0.25rem; color:oklch(85% 0.17 55);">{Math.round(selectedSummary.totals.calories)}</div>
					</div>
					<div style="text-align:center;">
						<div class="stat-eyebrow">Prot</div>
						<div style="font-size:1.125rem; font-weight:800; margin-top:0.25rem; color:oklch(78% 0.14 220);">{Math.round(selectedSummary.totals.protein)}g</div>
					</div>
					<div style="text-align:center;">
						<div class="stat-eyebrow">Carb</div>
						<div style="font-size:1.125rem; font-weight:800; margin-top:0.25rem; color:oklch(78% 0.16 275);">{Math.round(selectedSummary.totals.carbs)}g</div>
					</div>
					<div style="text-align:center;">
						<div class="stat-eyebrow">Grasa</div>
						<div style="font-size:1.125rem; font-weight:800; margin-top:0.25rem; color:oklch(75% 0.17 25);">{Math.round(selectedSummary.totals.fat)}g</div>
					</div>
				</div>
			</div>
			{#each selectedSummary.meals as meal (meal.meal_type)}
				<div style="margin-bottom:0.75rem;">
					<MealHeader label={meal.label} kcal={meal.totals.calories} protein={meal.totals.protein} hasEntries={meal.entries.length > 0} />
					{#each meal.entries as entry (entry.id)}
						<div class="glass-card" style="margin-bottom:0.3rem; padding:0.625rem; display:flex; justify-content:space-between; align-items:center; border-radius:14px;">
							<div>
								<div style="font-size:0.8125rem; font-weight:600;">{entry.product?.name ?? `Producto #${entry.product_id}`}</div>
								<div style="font-size:0.6875rem; color:rgba(255,255,255,0.45); margin-top:0.125rem;">{entry.grams}g · {fmtTime(entry.consumed_at)}</div>
							</div>
							<div style="text-align:right; flex-shrink:0; margin-left:0.75rem;">
								<div style="font-size:0.8rem; color:oklch(85% 0.17 55); font-weight:700;">{Math.round(entry.calories)} kcal</div>
								<div style="font-size:0.68rem; margin-top:0.125rem;">
									<span style="color:oklch(78% 0.14 220);">P{Math.round(entry.protein)}</span>
									<span style="color:oklch(78% 0.16 275);"> C{Math.round(entry.carbs)}</span>
									<span style="color:oklch(75% 0.17 25);"> G{Math.round(entry.fat)}</span>
								</div>
							</div>
						</div>
					{/each}
				</div>
			{/each}
		{:else}
			<div style="text-align:center; padding:2rem 0; color:rgba(255,255,255,0.4); font-size:0.85rem;">
				<div style="font-size:2rem; margin-bottom:0.5rem;">📅</div>
				Sin registros este día
			</div>
		{/if}
	</div>
{/if}

<!-- ── Calendar section ── -->
<div style="margin-top:1.5rem;">
	<div style="font-size:0.6875rem; letter-spacing:0.08em; text-transform:uppercase; color:rgba(255,255,255,0.45); font-weight:700; margin-bottom:0.75rem;">Calendario</div>

	<!-- Month navigation -->
	<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.75rem;">
		<button class="nav-btn" onclick={prevMonth}>◀</button>
		<span style="font-weight:700; font-size:0.9375rem;">{MONTH_NAMES[viewMonth]} {viewYear}</span>
		<button class="nav-btn" onclick={nextMonth} disabled={isCurrentMonth}>▶</button>
	</div>

	<!-- Day headers -->
	<div style="display:grid; grid-template-columns:repeat(7,1fr); gap:2px; margin-bottom:4px;">
		{#each DAY_NAMES as name}
			<div style="text-align:center; font-size:0.6875rem; color:rgba(255,255,255,0.4); font-weight:600; padding:0.25rem 0;">{name}</div>
		{/each}
	</div>

	<!-- Calendar grid -->
	<div class="glass-card" style="padding:0.5rem;">
		{#if loadingMonth}
			<p style="text-align:center; color:rgba(255,255,255,0.4); padding:2rem 0; font-size:0.85rem;">Cargando...</p>
		{:else}
			<div style="display:grid; grid-template-columns:repeat(7,1fr); gap:3px;">
				{#each calendarDays as cell}
					{#if cell.day === null}
						<div></div>
					{:else if isFuture(viewYear, viewMonth, cell.day)}
						<div style="aspect-ratio:1; display:flex; flex-direction:column; align-items:center; justify-content:center; border-radius:6px; opacity:0.2; font-size:0.8rem;">{cell.day}</div>
					{:else}
						{@const hasData = cell.date && monthData[cell.date] > 0}
						{@const isCalSelected = cell.date === selectedDay}
						{@const isTodayCell = cell.date ? isToday(cell.date) : false}
						{@const tookCreatine = trackCreatine && cell.date ? creatineDates.has(cell.date) : false}
						{@const didExercise = cell.date ? exerciseDates.has(cell.date) : false}
						<button
							onclick={() => cell.date && selectDay(cell.date)}
							style="aspect-ratio:1; display:flex; flex-direction:column; align-items:center; justify-content:center; border-radius:6px; cursor:pointer; padding:0; font-size:0.8rem; position:relative; border:{isCalSelected ? '2px solid var(--primary)' : isTodayCell ? '1px solid var(--primary)' : '1px solid transparent'}; background:{isCalSelected ? 'rgba(79,255,153,0.15)' : hasData && cell.date ? calColor(monthData[cell.date]) : 'var(--surface2)'}; font-weight:{isTodayCell ? '700' : '400'}; color:{isTodayCell ? 'var(--primary)' : 'var(--text)'}; transition:border-color 0.15s;">
							<span>{cell.day}</span>
							{#if hasData && cell.date}
								<span style="font-size:0.6rem; color:var(--text-muted); line-height:1;">{Math.round(monthData[cell.date])}k</span>
							{/if}
							{#if tookCreatine}
								<span style="position:absolute; top:1px; right:2px; font-size:0.55rem; line-height:1;">💊</span>
							{/if}
							{#if didExercise}
								<span style="position:absolute; top:1px; left:2px; font-size:0.55rem; line-height:1;">💪</span>
							{/if}
						</button>
					{/if}
				{/each}
			</div>
		{/if}
	</div>

	<!-- Legend -->
	<div style="display:flex; gap:0.75rem; align-items:center; flex-wrap:wrap; margin:0.75rem 0; font-size:0.72rem; color:var(--text-muted);">
		{#each ['<1200','1200-1800','1800-2400','>2400'] as lbl, i}
			<span style="display:flex; align-items:center; gap:3px;">
				<span style="width:12px; height:12px; border-radius:3px; background:{['rgba(79,255,153,0.25)','rgba(79,255,153,0.45)','rgba(79,255,153,0.65)','rgba(79,255,153,0.85)'][i]}; display:inline-block;"></span>
				{lbl}
			</span>
		{/each}
		{#if trackCreatine}<span>💊 Creatina</span>{/if}
		<span>💪 Ejercicio</span>
	</div>
</div>

{/if}

<!-- Bottom spacing -->
<div style="height:6rem;"></div>

<style>
	.glass-card {
		background: rgba(255,255,255,0.05);
		backdrop-filter: blur(24px) saturate(160%);
		-webkit-backdrop-filter: blur(24px) saturate(160%);
		border: 1px solid rgba(255,255,255,0.09);
		border-radius: 20px;
		padding: 1rem;
	}
	.stat-eyebrow {
		font-size: 0.625rem;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: rgba(255,255,255,0.5);
		font-weight: 700;
	}
	.csv-btn {
		padding: 0.25rem 0.5rem;
		border-radius: 8px;
		background: rgba(255,255,255,0.07);
		border: 1px solid rgba(255,255,255,0.1);
		color: rgba(255,255,255,0.65);
		font-size: 0.6875rem;
		font-weight: 600;
		font-family: inherit;
		cursor: pointer;
	}
	.nav-btn {
		padding: 0.375rem 0.75rem;
		border-radius: 10px;
		background: rgba(255,255,255,0.06);
		border: 1px solid rgba(255,255,255,0.1);
		color: rgba(255,255,255,0.8);
		font-size: 0.75rem;
		cursor: pointer;
		font-family: inherit;
	}
	.nav-btn:disabled { opacity: 0.3; cursor: not-allowed; }
</style>
