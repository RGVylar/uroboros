from fastapi import APIRouter, Depends, Response
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.models.allergy import UserAllergy
from app.models.body_measurement import BodyMeasurementLog
from app.models.cheat_day import CheatDayLog
from app.models.creatine import CreatineLog
from app.models.diary import DiaryEntry
from app.models.exercise import ExerciseSession, ExerciseSessionEntry
from app.models.friendship import Friendship, FriendshipStatus
from app.models.goals import UserGoals
from app.models.inventory import InventoryItem, ShoppingListItem
from app.models.password_reset import PasswordResetToken
from app.models.recipe import Recipe, RecipeIngredient
from app.models.supplement import UserSupplement, SupplementLog
from app.models.water import WaterLog
from app.models.weight import WeightLog
from app.schemas.auth import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[User]:
    """Users available for the 'also log for' picker (self + allowed friends)."""
    as_requester = (
        select(Friendship.receiver_id)
        .where(
            Friendship.requester_id == user.id,
            Friendship.status == FriendshipStatus.accepted,
            Friendship.can_add_food.is_(True),
        )
    )
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


@router.get("/{user_id}/profile")
def get_friend_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return public profile data for a friend."""
    from datetime import date, timedelta
    from sqlalchemy import func, cast, Date
    from app.models.diary import DiaryEntry
    from app.models.recipe import Recipe
    from app.services.streak_service import calculate_streak

    # Must be a friend
    is_friend = db.scalar(
        select(Friendship).where(
            or_(
                (Friendship.requester_id == current_user.id) & (Friendship.receiver_id == user_id),
                (Friendship.requester_id == user_id) & (Friendship.receiver_id == current_user.id),
            ),
            Friendship.status == FriendshipStatus.accepted,
        )
    )
    if not is_friend and user_id != current_user.id:
        from fastapi import HTTPException, status as http_status
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Not a friend")

    target = db.scalar(select(User).where(User.id == user_id))
    if not target:
        from fastapi import HTTPException, status as http_status
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="User not found")

    streak = calculate_streak(db, user_id)
    since = date.today() - timedelta(days=29)
    active_days = db.scalar(
        select(func.count(func.distinct(cast(DiaryEntry.consumed_at, Date)))).where(
            DiaryEntry.user_id == user_id,
            cast(DiaryEntry.consumed_at, Date) >= since,
        )
    ) or 0
    recipe_count = db.scalar(
        select(func.count()).select_from(Recipe).where(Recipe.user_id == user_id)
    ) or 0

    return {
        "id": target.id,
        "name": target.name,
        "streak": streak,
        "active_days": active_days,
        "recipe_count": recipe_count,
    }


@router.delete("/me", status_code=204)
def delete_account(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    """Permanently delete the current user and all their data."""
    uid = user.id

    db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == uid))
    db.execute(delete(UserAllergy).where(UserAllergy.user_id == uid))
    db.execute(delete(WaterLog).where(WaterLog.user_id == uid))
    db.execute(delete(CheatDayLog).where(CheatDayLog.user_id == uid))
    db.execute(delete(CreatineLog).where(CreatineLog.user_id == uid))
    db.execute(delete(BodyMeasurementLog).where(BodyMeasurementLog.user_id == uid))
    db.execute(delete(WeightLog).where(WeightLog.user_id == uid))
    db.execute(delete(DiaryEntry).where(DiaryEntry.user_id == uid))
    db.execute(delete(SupplementLog).where(SupplementLog.user_id == uid))
    db.execute(delete(UserSupplement).where(UserSupplement.user_id == uid))
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

    # Amistades
    db.execute(delete(Friendship).where(
        (Friendship.requester_id == uid) | (Friendship.receiver_id == uid)
    ))

    db.execute(delete(UserGoals).where(UserGoals.user_id == uid))
    db.execute(delete(User).where(User.id == uid))
    db.commit()

    return Response(status_code=204)
