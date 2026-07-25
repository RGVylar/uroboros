// Version this build reports to the server as "currently running". Bump it on
// each release so the changelog endpoint knows which notes the user already has
// and whether a newer version exists. On native (Capacitor) this is the version
// bundled in the APK, which is exactly why the server decides what to show.
export const APP_VERSION = '1.10';

const LS_KEY = 'uro_changelog_seen';

// Where the "Actualizar" nudge sends the user. On Android a reload does nothing
// (the frontend is bundled in the APK), so we point at the newest build. This
// backend endpoint lists the Nextcloud folder, finds the most recent APK and
// redirects to its download — so the URL is stable even though the filename
// changes each build. Swap for the Play Store URL once published there.
export const UPDATE_URL = 'https://comida.mugrelore.com/api/download/latest-apk';

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
