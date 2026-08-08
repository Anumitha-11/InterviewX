from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.database.session import get_db
from app.models.models import User, Profile, Progress, Roadmap
from app.schemas.schemas import UserCreate, UserLogin, Token, UserOut


router = APIRouter()


@router.post("/register", response_model=UserOut)
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db),
):
    # Check if user already exists
    existing_user = (
        db.query(User)
        .filter(User.email == user_in.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="A user with this email already exists.",
        )

    # Hash password
    hashed_password = security.get_password_hash(
        user_in.password
    )

    # Create user
    user = User(
        email=user_in.email,
        hashed_password=hashed_password,
    )

    db.add(user)
    db.flush()  # Get user.id before committing

    # Initialize user profile
    profile = Profile(
        user_id=user.id,
        name=user_in.name,
        target_role="",
        experience_level="Mid Level",
        target_company="",
        preferred_type="Mix",
        skills=[],
    )

    db.add(profile)

    # Initialize progress
    progress = Progress(
        user_id=user.id,
        daily_streak=0,
        overall_readiness=0.0,
        last_active_date=None,
    )

    db.add(progress)

    # Initialize default roadmap
    topics = [
        (
            "System Design & Architecture",
            "high",
            "Focus on consistently hashing algorithms, distributed caching layers, and load balancing.",
        ),
        (
            "Behavioral Questions (STAR)",
            "medium",
            "Practice structuring responses using Situation, Task, Action, and Result.",
        ),
        (
            "Data Structures & Algorithms",
            "medium",
            "Solve binary trees traversal, subset tracking, and depth first search recursion.",
        ),
    ]

    for topic, priority, recommendations in topics:
        roadmap_item = Roadmap(
            user_id=user.id,
            topic_name=topic,
            status="pending",
            priority=priority,
            recommendations=recommendations,
        )

        db.add(roadmap_item)

    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=Token)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.email == credentials.email)
        .first()
    )

    if not user or not security.verify_password(
        credentials.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=400,
            detail="Incorrect email or password",
        )

    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    access_token = security.create_access_token(
        subject=user.id,
        expires_delta=access_token_expires,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }