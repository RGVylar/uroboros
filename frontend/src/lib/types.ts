export interface User {
	id: number;
	email: string;
	name: string;
}

export interface TokenResponse {
	access_token: string;
	token_type: string;
	user: User;
}

export interface Product {
	id: number;
	barcode: string | null;
	name: string;
	brand: string | null;
	calories_per_100g: number;
	protein_per_100g: number;
	carbs_per_100g: number;
	fat_per_100g: number;
	source: 'openfoodfacts' | 'manual' | 'edited';
	edited_by: number | null;
	edited_at: string | null;
	created_at: string;
}

export type MealType = 'breakfast' | 'lunch' | 'dinner' | 'snack';

export const MEAL_LABELS: Record<MealType, string> = {
	breakfast: 'Desayuno',
	lunch: 'Almuerzo',
	dinner: 'Cena',
	snack: 'Snack',
};

export const MEAL_ORDER: MealType[] = ['breakfast', 'lunch', 'dinner', 'snack'];

export interface DiaryEntry {
	id: number;
	user_id: number;
	product_id: number;
	grams: number;
	calories: number;
	protein: number;
	carbs: number;
	fat: number;
	meal_type: MealType;
	consumed_at: string;
	created_at: string;
	product: Product | null;
}

export interface MealSection {
	meal_type: MealType;
	label: string;
	totals: DayTotals;
	entries: DiaryEntry[];
}

export interface DayTotals {
	calories: number;
	protein: number;
	carbs: number;
	fat: number;
}

export interface DaySummary {
	date: string;
	totals: DayTotals;
	meals: MealSection[];
	entries: DiaryEntry[];
}

export interface Goals {
	user_id: number;
	kcal: number;
	protein: number;
	carbs: number;
	fat: number;
	water_ml: number;
}

export interface WaterDay {
	total_ml: number;
	goal_ml: number;
}

export interface WeightLog {
	id: number;
	user_id: number;
	weight: number;
	logged_at: string;
}

export interface RecipeIngredient {
	id: number;
	product_id: number;
	grams: number;
}

export interface Recipe {
	id: number;
	name: string;
	owner_id: number;
	ingredients: RecipeIngredient[];
}

export interface RecommendedProduct {
	product: Product;
	suggested_grams: number;
	estimated_calories: number;
	reason: string;
}

export interface FrequentProduct {
	product: Product;
	count: number;
}

export type FriendshipStatus = 'pending' | 'accepted' | 'rejected';

export interface UserMinimal {
	id: number;
	name: string;
	email: string;
}

export interface Friendship {
	id: number;
	requester: UserMinimal;
	receiver: UserMinimal;
	status: FriendshipStatus;
	can_add_food: boolean;
	created_at: string;
}
