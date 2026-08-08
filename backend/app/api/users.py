from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.models import User, Profile, record_user_activity
from app.schemas.schemas import UserOut, ProfileUpdate, ProfileOut

router = APIRouter()

@router.get("/me", response_model=UserOut)
def read_user_me(
    current_user: User = Depends(get_current_user)
):
    return current_user

@router.put("/profile", response_model=ProfileOut)
def update_profile_me(
    profile_in: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = current_user.profile
    if not profile:
        profile = Profile(user_id=current_user.id)
        db.add(profile)
        db.flush()
        
    update_data = profile_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
        
    # Record activity and update streak
    record_user_activity(db, current_user.id)
    
    db.commit()
    db.refresh(profile)
    return profile
