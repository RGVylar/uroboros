<script lang="ts">
	import { goto } from '$app/navigation';

	let step = $state(0);

	const STEPS = [
		{
			art: 'search' as const,
			title: 'Registra con un toque',
			sub: 'Busca por voz, barcode o a mano. Avena, pollo, plátano — en menos de 2 segundos.',
		},
		{
			art: 'pair' as const,
			title: 'Compartes con tu pareja',
			sub: 'Registra una comida para los dos a la vez. Vuestras cuentas sincronizadas.',
		},
		{
			art: 'streak' as const,
			title: 'Progreso, no perfección',
			sub: 'Rachas, cheat days y objetivos ajustables. Hecho para durar.',
		},
	];

	function next() {
		if (step < STEPS.length - 1) {
			step++;
		} else {
			goto('/goals?new=1');
		}
	}

	function skip() {
		goto('/goals?new=1');
	}
</script>

<div style="display:flex; flex-direction:column; min-height:85dvh; padding:1.25rem 1.25rem max(2rem, calc(env(safe-area-inset-bottom, 0px) + 2rem));">

	<!-- Progress dots + Skip -->
	<div style="display:flex; justify-content:space-between; align-items:center; padding-top:0.25rem; margin-bottom:0;">
		<div style="display:flex; gap:0.3rem;">
			{#each STEPS as _, i}
				<div style="
					height:4px; border-radius:99px;
					width:{i === step ? '22px' : '8px'};
					background:{i <= step ? 'oklch(85% 0.17 160)' : 'rgba(255,255,255,0.15)'};
					transition:all 0.3s ease;
				"></div>
			{/each}
		</div>
		<button onclick={skip} style="background:none; border:none; color:rgba(255,255,255,0.5); font-size:0.75rem; cursor:pointer; font-family:inherit; padding:0.25rem 0;">Saltar</button>
	</div>

	<!-- Content -->
	<div style="flex:1; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; padding:2.5rem 0;">

		<!-- Art illustration -->
		<div style="margin-bottom:2rem; display:flex; justify-content:center;">
			{#if STEPS[step].art === 'search'}
				<!-- Search UI art -->
				<div style="width:240px; background:rgba(255,255,255,0.05); backdrop-filter:blur(24px) saturate(160%); -webkit-backdrop-filter:blur(24px) saturate(160%); border:1px solid rgba(255,255,255,0.09); border-radius:20px; padding:1.25rem;">
					<div style="display:flex; align-items:center; gap:0.625rem; margin-bottom:0.875rem; padding:0.5rem 0.75rem; background:rgba(255,255,255,0.04); border-radius:12px;">
						<span style="font-size:0.875rem;">🔍</span>
						<span style="font-size:0.6875rem; color:rgba(255,255,255,0.6);">Avena integral</span>
					</div>
					{#each ['Avena integral · 370kcal', 'Avena bio · 362kcal', 'Barras avena · 464kcal'] as item, i}
						<div style="
							padding:0.625rem 0.75rem; border-radius:10px;
							background:{i === 0 ? 'oklch(75% 0.18 165 / 0.15)' : 'rgba(255,255,255,0.03)'};
							margin-bottom:{i < 2 ? '0.375rem' : '0'};
							font-size:0.6875rem;
							color:{i === 0 ? 'oklch(85% 0.15 160)' : 'rgba(255,255,255,0.6)'};
							font-weight:{i === 0 ? '600' : '400'};
						">{item}</div>
					{/each}
				</div>

			{:else if STEPS[step].art === 'pair'}
				<!-- Pair avatars art -->
				<div style="position:relative; width:180px; height:120px;">
					<div style="position:absolute; left:0; top:20px; width:80px; height:80px; border-radius:50%; background:linear-gradient(135deg, oklch(80% 0.18 160), oklch(60% 0.2 220)); display:flex; align-items:center; justify-content:center; font-size:2rem; font-weight:800; color:#041010;">R</div>
					<div style="position:absolute; right:0; top:20px; width:80px; height:80px; border-radius:50%; background:linear-gradient(135deg, oklch(75% 0.18 330), oklch(55% 0.2 290)); display:flex; align-items:center; justify-content:center; font-size:2rem; font-weight:800; color:#fff;">L</div>
					<div style="position:absolute; left:50%; top:45px; transform:translateX(-50%); width:42px; height:42px; border-radius:12px; background:linear-gradient(135deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); display:flex; align-items:center; justify-content:center; font-size:0.875rem; font-weight:800; color:#041010; box-shadow:0 6px 20px oklch(75% 0.2 165 / 0.5);">2×</div>
				</div>

			{:else}
				<!-- Streak bars art -->
				<div style="display:flex; gap:0.5rem; align-items:flex-end;">
					{#each [1,2,3,4,5,6,7] as d}
						<div style="
							width:26px;
							height:{d <= 5 ? '70px' : '32px'};
							border-radius:10px;
							background:{d <= 5 ? 'linear-gradient(180deg, oklch(80% 0.19 45), oklch(65% 0.2 25))' : 'rgba(255,255,255,0.06)'};
							display:flex; align-items:flex-end; justify-content:center;
							padding:0.375rem;
							font-size:0.875rem;
							transition:height 0.3s;
						">{d <= 5 ? '🔥' : ''}</div>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Title -->
		<h1 style="font-size:2.25rem; font-weight:400; letter-spacing:-0.05em; color:#fff; line-height:1.1; margin:0 0 0.875rem; font-family:'Lora','Georgia',serif;">{STEPS[step].title}</h1>

		<!-- Subtitle -->
		<p style="font-size:0.875rem; color:rgba(255,255,255,0.6); line-height:1.55; max-width:280px; margin:0 auto;">{STEPS[step].sub}</p>
	</div>

	<!-- CTA button -->
	<button onclick={next} style="
		height:54px; border-radius:18px; border:none; cursor:pointer; font-family:inherit;
		background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		color:#041010; font-weight:800; font-size:0.9375rem;
		box-shadow:0 10px 30px -8px oklch(75% 0.22 165 / 0.55), inset 0 1px 0 rgba(255,255,255,0.4);
		letter-spacing:-0.01em;
		transition:opacity 0.15s;
	">
		{step < STEPS.length - 1 ? 'Siguiente' : 'Empezar'}
	</button>
</div>
