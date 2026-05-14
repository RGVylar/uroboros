// Connectivity store — tracks whether the backend is reachable.
// Updated by api.ts on every request. The layout reads it to show a banner.

let _offline = $state(false);
let _since: number | null = null;       // timestamp when we went offline
let _failCount = 0;                     // consecutive failures
const FAIL_THRESHOLD = 2;              // show banner after N consecutive failures

export const connectivity = {
	get isOffline() { return _offline; },

	/** Call on every successful API response */
	recordSuccess() {
		_failCount = 0;
		if (_offline) {
			_offline = false;
			_since = null;
		}
	},

	/** Call on every network-level error (not 4xx/5xx — those are server responses) */
	recordFailure() {
		_failCount++;
		if (!_offline && _failCount >= FAIL_THRESHOLD) {
			_offline = true;
			_since = Date.now();
		}
	},

	get offlineSince(): number | null { return _since; },
};
