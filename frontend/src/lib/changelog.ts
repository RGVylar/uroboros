export const CHANGELOG_VERSION = '1.4';
const LS_KEY = 'uro_changelog_seen';

export function changelogShouldShow(): boolean {
	if (typeof localStorage === 'undefined') return false;
	return localStorage.getItem(LS_KEY) !== CHANGELOG_VERSION;
}

export function changelogMarkSeen(): void {
	if (typeof localStorage !== 'undefined') {
		localStorage.setItem(LS_KEY, CHANGELOG_VERSION);
	}
}
