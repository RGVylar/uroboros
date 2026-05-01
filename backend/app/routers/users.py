from fastapi import APIRouter, Depends, Response
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.models.body_measurement import BodyMeasurement
from app.models.cheat_day import CheatDay
from app.models.creatine import Creatine
from app.models.diary import DiaryEntry
from app.models.exercise import ExerciseSession
from app.models.friendship import Friendship
from app.models.friendship import FriendshipStatus
from app.models.goals import Goals
from app.models.inventory import InventoryItem
from app.models.password_reset import PasswordResetToken
from app.models.supplement import Supplement
from app.models.water import WaterEntry
from app.models.weight import WeightEntry
from app.schemas.auth import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[User]:
    """Users available for the 'also log for' picker (self + allowed friends)."""
    # Case 1: I am requester, receiver gave me permission (can_add_food)
    as_requester = (
        select(Friendship.receiver_id)
        .where(
            Friendship.requester_id == user.id,
            Friendship.status == FriendshipStatus.accepted,
            Friendship.can_add_food.is_(True),
        )
    )
    # Case 2: I am receiver, requester gave me permission (can_add_food_requester)
    as_receiver = (
        select(Friendship.requester_id)
        .where(
            Friendship.receiver_id == user.id,
            Friendship.status == FriendshipStatus.accepted,
            Friendship.can_add_food_requester.is_(True),
        )
    )

    stmt = (
        select(User)
        .where(or_(User.id == user.id, User.id.in_(as_requester), User.id.in_(as_receiver)))
        .order_by(User.name)
    )
    return list(db.scalars(stmt))


@router.delete("/me", status_code=204)
def delete_account(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    """Permanently delete the current user and all their data."""
    uid = user.id

    # Importaciones adicionales necesarias aquí
    from app.models.inventory import ShoppingListItem, SharedInventoryItem, SharedShoppingListItem
    from app.models.exercise import ExerciseSessionEntry
    from app.models.supplement import UserSupplement, SupplementLog
    from app.models.recipe import Recipe, RecipeIngredient

    # Borrar en orden para respetar FKs
    db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == uid))
    db.execute(delete(WaterEntry).where(WaterEntry.user_id == uid))
    db.execute(delete(CheatDay).where(CheatDay.user_id == uid))
    db.execute(delete(Creatine).where(Creatine.user_id == uid))
    db.execute(delete(BodyMeasurement).where(BodyMeasurement.user_id == uid))
    db.execute(delete(WeightEntry).where(WeightEntry.user_id == uid))
    db.execute(delete(DiaryEntry).where(DiaryEntry.user_id == uid))
    db.execute(delete(SupplementLog).where(SupplementLog.user_id == uid))
    db.execute(delete(UserSupplement).where(UserSupplement.user_id == uid))
    db.execute(delete(SharedInventoryItem).where(SharedInventoryItem.user_id == uid))
    db.execute(delete(SharedShoppingListItem).where(SharedShoppingListItem.user_id == uid))
    db.execute(delete(ShoppingListItem).where(ShoppingListItem.user_id == uid))
    db.execute(delete(InventoryItem).where(InventoryItem.user_id == uid))

    # Sesiones de ejercicio (entradas primero)
    session_ids = db.scalars(
        select(ExerciseSession.id).where(ExerciseSession.user_id == uid)
    ).all()
    if session_ids:
        db.execute(delete(ExerciseSessionEntry).where(ExerciseSessionEntry.session_id.in_(session_ids)))
    db.execute(delete(ExerciseSession).where(ExerciseSession.user_id == uid))

    # Recetas
    recipe_ids = db.scalars(select(Recipe.id).where(Recipe.user_id == uid)).all()
    if recipe_ids:
        db.execute(delete(RecipeIngredient).where(RecipeIngredient.recipe_id.in_(recipe_ids)))
    db.execute(delete(Recipe).where(Recipe.user_id == uid))

    # Amistades (como requester o receiver)
    db.execute(delete(Friendship).where(
        (Friendship.requester_id == uid) | (Friendship.receiver_id == uid)
    ))

    db.execute(delete(Goals).where(Goals.user_id == uid))
    db.execute(delete(User).where(User.id == uid))
    db.commit()

    return Response(status_code=204)
