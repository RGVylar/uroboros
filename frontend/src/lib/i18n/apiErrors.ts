// El backend se queda en español/inglés técnico: traducir aquí, en el cliente,
// evita tener que pasarle el idioma del usuario en cada petición.
// Los literales de la izquierda son los `detail` reales de HTTPException —
// si cambias uno en el backend, cámbialo también aquí.
import { t, type TKey } from './index.svelte';

const EXACT: Record<string, TKey> = {
	// auth
	'Unauthorized': 'errors.session',
	'Invalid token': 'errors.session',
	'Invalid credentials': 'errors.invalidCredentials',
	'Email already registered': 'errors.emailRegistered',
	'User not found': 'errors.userNotFound',
	'Usuario no encontrado': 'errors.userNotFound',
	'No existe ningún usuario con ese email': 'errors.noUserWithEmail',
	'La contraseña debe tener al menos 8 caracteres': 'errors.passwordTooShort',
	'Enlace inválido o ya utilizado': 'errors.linkInvalid',
	'El enlace ha expirado. Solicita uno nuevo': 'errors.linkExpired',
	'Not allowed': 'errors.notAllowed',
	'Not found': 'errors.notFound',

	// amigos y pareja
	'Not a friend': 'errors.notFriend',
	'No sois amigos': 'errors.notFriend',
	'Friendship not found': 'errors.friendshipNotFound',
	'Other user not found': 'errors.otherUserNotFound',
	'No puedes añadirte a ti mismo': 'errors.cannotAddSelf',
	'Ya sois amigos': 'errors.alreadyFriends',
	'Ya existe una solicitud pendiente': 'errors.requestPending',
	'Esa persona ya tiene pareja': 'errors.alreadyPartnered',
	'La amistad debe estar aceptada': 'errors.friendshipNotAccepted',
	'Solo el receptor puede aceptar o rechazar': 'errors.onlyReceiverDecides',
	'Solo el receptor controla este permiso': 'errors.onlyReceiverPermission',
	'Solo el receptor puede cambiar su flag': 'errors.onlyReceiverFlag',
	'Solo el solicitante controla este permiso': 'errors.onlyRequesterPermission',
	'Solo el solicitante puede cambiar su flag': 'errors.onlyRequesterFlag',
	'Solo tu pareja puede añadir a tu diario': 'errors.onlyPartnerCanAdd',
	'No tienes permiso para registrar en el diario de este usuario': 'errors.noDiaryPermission',

	// diario, productos, recetas
	'Entry not found': 'errors.entryNotFound',
	'Product not found': 'errors.productNotFound',
	'Barcode already exists': 'errors.barcodeExists',
	'Recipe not found': 'errors.recipeNotFound',
	'Recipe not accessible': 'errors.recipeNotAccessible',
	'Not your recipe': 'errors.notYourRecipe',
	'Ingredient cannot be empty': 'errors.emptyIngredient',
	'Meal type inválido': 'errors.invalidMealType',
	'Goals not set': 'errors.goalsNotSet',
	'Item not found': 'errors.itemNotFound',

	// salud
	'Allergy already exists': 'errors.allergyExists',
	'Allergy not found': 'errors.allergyNotFound',
	'Not your allergy': 'errors.notYourAllergy',
	"No permission to view this user's allergies": 'errors.noAllergyPermission',
	'Supplement not found': 'errors.supplementNotFound',
	'Exercise not found': 'errors.exerciseNotFound',
	'Cannot edit predefined exercise': 'errors.cannotEditPredefined',
	'Cannot delete predefined exercise': 'errors.cannotDeletePredefined',

	// perfil y suscripción
	'Unknown avatar': 'errors.unknownAvatar',
	'Unknown colour': 'errors.unknownColour',
	'premium_required': 'errors.premiumRequired',
	'No hay suscripciones activas para este usuario': 'errors.noActiveSubscription',
};

const PREFIX: Array<[string, TKey]> = [
	// Lleva el número de envíos interpolado, así que no puede ir en EXACT.
	['Límite de', 'errors.testNotifLimit'],
];

export function translateApiError(detail: string): string {
	const key = EXACT[detail] ?? PREFIX.find(([p]) => detail.startsWith(p))?.[1];
	return key ? t(key) : detail;
}
