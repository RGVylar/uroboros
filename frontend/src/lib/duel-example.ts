// ---------------------------------------------------------------------------
// Tipos y datos de EJEMPLO para el Duelo semanal de adherencia.
//
// El Duelo ya tiene backend (`GET /duel/{friend_id}`, desde la 0032): el perfil
// del amigo llama a la API y mapea la respuesta a `DuelData`. Lo que queda aquí
// son los tipos que consume `DuelBoard` y un generador de ejemplo para ver la UI
// aislada, sin datos reales.
// ---------------------------------------------------------------------------

// Estado de un día dentro de la semana del duelo. Cada día contado puntúa
// 0–100 (hasta 70 por calorías, hasta 30 por proteína) y el estado sale de
// los puntos:
//   perfect 🎯 90 o más
//   hit     ✓  50 o más
//   miss    ·  registrado, por debajo de 50
//   empty   ○  sin registrar (cuenta como 0) o día futuro (no cuenta)
//   joker   🍕 cheat day: comodín, sale del divisor
//   today   ◌  el día en curso, aún sin cerrar
export type DuelDay = 'perfect' | 'hit' | 'miss' | 'empty' | 'joker' | 'today';

/** Por qué un día tiene los puntos que tiene. */
export interface DuelDayDetail {
	score: number;
	kcal: number;
	kcalGoal: number;
	kcalPts: number;
	protein: number;
	proteinGoal: number;
	proteinPts: number;
}

export interface DuelSide {
	name: string;
	avatarId: string | null;
	avatarPhoto?: string | null;
	/** Media de puntos de los días contados (0–100, comodín excluido). */
	pct: number | null; // null = semana sin empezar
	/** 7 posiciones, lunes → domingo. */
	days: DuelDay[];
	/** Puntos de cada día; null donde no se puntúa (futuro, hoy, comodín). */
	scores: (number | null)[];
	/** Desglose de cada día; null cuando no hubo nada que registrar. */
	details: (DuelDayDetail | null)[];
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
 * que se vea con la persona de verdad. Coincide con el mockup: Tú 80 vs 60,
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
			days: ['perfect', 'hit', 'perfect', 'miss', 'hit', 'joker', 'today'],
			scores: [100, 82, 95, 37, 76, null, null],
			details: [
				{ score: 100, kcal: 2010, kcalGoal: 2000, kcalPts: 70, protein: 165, proteinGoal: 162, proteinPts: 30 },
				{ score: 82, kcal: 1800, kcalGoal: 2000, kcalPts: 52, protein: 170, proteinGoal: 162, proteinPts: 30 },
				{ score: 95, kcal: 2060, kcalGoal: 2000, kcalPts: 70, protein: 135, proteinGoal: 162, proteinPts: 25 },
				{ score: 37, kcal: 2430, kcalGoal: 2000, kcalPts: 12, protein: 135, proteinGoal: 162, proteinPts: 25 },
				{ score: 76, kcal: 2210, kcalGoal: 2000, kcalPts: 51, protein: 140, proteinGoal: 162, proteinPts: 25 },
				null,
				null,
			],
		},
		them: {
			name: themName,
			avatarId: themAvatar,
			pct: 60,
			days: ['hit', 'hit', 'miss', 'empty', 'perfect', 'joker', 'today'],
			scores: [88, 71, 40, 0, 100, null, null],
			details: [
				{ score: 88, kcal: 1750, kcalGoal: 1800, kcalPts: 70, protein: 78, proteinGoal: 130, proteinPts: 18 },
				{ score: 71, kcal: 1980, kcalGoal: 1800, kcalPts: 56, protein: 65, proteinGoal: 130, proteinPts: 15 },
				{ score: 40, kcal: 2180, kcalGoal: 1800, kcalPts: 21, protein: 82, proteinGoal: 130, proteinPts: 19 },
				null,
				{ score: 100, kcal: 1820, kcalGoal: 1800, kcalPts: 70, protein: 132, proteinGoal: 130, proteinPts: 30 },
				null,
				null,
			],
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
