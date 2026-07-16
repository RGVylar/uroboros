// ---------------------------------------------------------------------------
// Datos de EJEMPLO para el Duelo semanal de adherencia.
//
// El Duelo aún no tiene backend: esta es la única fuente de datos y sirve para
// ver la UI en su sitio real. Cuando exista el endpoint, se sustituye
// `makeExampleDuel(...)` por una llamada a la API que devuelva un `DuelData`
// con la misma forma; los componentes (`DuelBoard`) no cambian.
// ---------------------------------------------------------------------------

// Estado de un día dentro de la semana del duelo.
//   hit   ✓  registrado y dentro del objetivo (|kcal - objetivo efectivo| < 250)
//   miss  ·  registrado pero fuera de rango
//   empty ○  sin registrar
//   joker 🍕 cheat day: comodín, sale del divisor (ni acierto ni fallo)
//   today ◌  el día en curso, aún sin cerrar
export type DuelDay = 'hit' | 'miss' | 'empty' | 'joker' | 'today';

export interface DuelSide {
	name: string;
	avatarId: string | null;
	/** % de adherencia de la semana (aciertos / días contados, comodín excluido). */
	pct: number | null; // null = semana sin empezar
	/** 7 posiciones, lunes → domingo. */
	days: DuelDay[];
}

export type SeasonWinner = 'me' | 'them' | 'tie' | 'current';

export interface DuelBadge {
	icon: string;
	label: string;
	desc: string;
	unlocked: boolean;
}

export interface DuelData {
	week: number;
	/** Etiqueta del estado de la temporada: 'Último día', 'Empieza', 'Cerrada'. */
	phase: string;
	me: DuelSide;
	them: DuelSide;
	seasonsWon: { me: number; them: number };
	history: { week: number; winner: SeasonWinner }[];
	/** Semanas ganadas seguidas por 'me' (0 = sin racha). */
	streakWeeks: number;
	badges: DuelBadge[];
}

/**
 * Duelo de ejemplo con estadísticas fijas pero nombres/avatares reales, para
 * que se vea con la persona de verdad. Coincide con el mockup: Tú 80% vs 60%,
 * semana 28, sábado de comodín, domingo en curso.
 */
export function makeExampleDuel(
	meName: string,
	meAvatar: string | null,
	themName: string,
	themAvatar: string | null,
): DuelData {
	return {
		week: 28,
		phase: 'Último día',
		me: {
			name: meName,
			avatarId: meAvatar,
			pct: 80,
			days: ['hit', 'hit', 'hit', 'miss', 'hit', 'joker', 'today'],
		},
		them: {
			name: themName,
			avatarId: themAvatar,
			pct: 60,
			days: ['hit', 'hit', 'miss', 'miss', 'hit', 'joker', 'today'],
		},
		seasonsWon: { me: 4, them: 3 },
		history: [
			{ week: 23, winner: 'them' },
			{ week: 24, winner: 'me' },
			{ week: 25, winner: 'them' },
			{ week: 26, winner: 'me' },
			{ week: 27, winner: 'me' },
			{ week: 28, winner: 'current' },
		],
		streakWeeks: 2,
		badges: [
			{ icon: '🧹', label: 'Barrido',     desc: '7 de 7 días',        unlocked: true },
			{ icon: '🎢', label: 'Remontada',   desc: 'Perdías el viernes', unlocked: false },
			{ icon: '📸', label: 'Photo finish', desc: 'Ganar por <5 pts',  unlocked: true },
		],
	};
}
