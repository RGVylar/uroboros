// Version this build reports to the server as "currently running". Bump it on
// each release so the changelog endpoint knows which notes the user already has
// and whether a newer version exists. On native (Capacitor) this is the version
// bundled in the APK, which is exactly why the server decides what to show.
export const APP_VERSION = '1.16';

const LS_KEY = 'uro_changelog_seen';

// Where the "Actualizar" nudge sends the user. On Android a reload does nothing
// (the frontend is bundled in the APK), so it has to go somewhere that can
// install a newer build — and ese sitio sólo puede ser Play.
//
// Apuntaba al APK de Nextcloud (`/api/download/latest-apk`) mientras la
// distribución era por sideload. Eso NO puede viajar en la build que se sube a
// Play: la política Device and Network Abuse prohíbe que una app distribuida por
// Play se actualice por cualquier vía que no sea Play. Ese endpoint sigue vivo
// para la landing /unete, pero la app ya no lo enlaza.
//
// La URL es válida desde ya: el `id` es el applicationId, que es irreversible.
// En Android abre la app de Play directamente.
export const UPDATE_URL = 'https://play.google.com/store/apps/details?id=com.uroboros.app';

export type ChangeType = 'nuevo' | 'mejora' | 'fix';

export interface ReleaseNoteItem {
	type: ChangeType;
	title: string;
	desc: string;
}

export interface ReleaseNote {
	version: string;
	title: string;
	importance: string; // 'minor' | 'major'
	items: ReleaseNoteItem[];
}

export interface UpdateInfo {
	version: string;
	title: string;
	teaser: string[];
	more: number;
}

export interface ChangelogResponse {
	news: ReleaseNote[];
	update: UpdateInfo | null;
}

/** '1.10' > '1.9': compara numéricamente por tramos, como `_parse` en el backend. */
export function isNewerVersion(candidate: string, current: string): boolean {
	const parse = (v: string) => v.split('.').map((p) => parseInt(p, 10) || 0);
	const a = parse(candidate), b = parse(current);
	for (let i = 0; i < Math.max(a.length, b.length); i++) {
		const d = (a[i] ?? 0) - (b[i] ?? 0);
		if (d !== 0) return d > 0;
	}
	return false;
}

/** Last version whose notes the user dismissed (empty string = never). */
export function getSeen(): string {
	if (typeof localStorage === 'undefined') return '';
	return localStorage.getItem(LS_KEY) ?? '';
}

/** Remember that the user has seen everything up to `version`. */
export function markSeen(version: string): void {
	if (typeof localStorage !== 'undefined' && version) {
		localStorage.setItem(LS_KEY, version);
	}
}
