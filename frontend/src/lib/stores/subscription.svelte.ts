import { api } from '$lib/api';

export type SubscriptionStatus = 'trial' | 'free' | 'premium';

interface SubscriptionState {
	status: SubscriptionStatus;
	trial_days_left: number | null;
	is_premium: boolean;
	loaded: boolean;
}

function createSubscriptionStore() {
	let status: SubscriptionStatus = $state('free');
	let trial_days_left: number | null = $state(null);
	let is_premium: boolean = $state(false);
	let loaded: boolean = $state(false);

	async function load() {
		try {
			const data = await api.get<SubscriptionState>('/users/me/subscription');
			status = data.status;
			trial_days_left = data.trial_days_left;
			is_premium = data.is_premium;
		} catch {
			// silently fail — defaults to free
		} finally {
			loaded = true;
		}
	}

	return {
		get status() { return status; },
		get trial_days_left() { return trial_days_left; },
		get is_premium() { return is_premium; },
		get loaded() { return loaded; },
		load,
	};
}

export const subscription = createSubscriptionStore();
