from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Float,
    Text,
    JSON,
)
from sqlalchemy.orm import relationship

from app.database.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship(
        "Profile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    resumes = relationship(
        "Resume",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    interviews = relationship(
        "Interview",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    progress = relationship(
        "Progress",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    roadmap_items = relationship(
        "Roadmap",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
    )

    name = Column(String, nullable=False)
    target_role = Column(String, nullable=True)
    experience_level = Column(String, nullable=True)
    target_company = Column(String, nullable=True)
    preferred_type = Column(String, nullable=True)
    skills = Column(JSON, nullable=True)

    user = relationship("User", back_populates="profile")


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    file_name = Column(String, nullable=False)
    raw_text = Column(Text, nullable=True)
    parsed_skills = Column(JSON, nullable=True)
    parsed_projects = Column(JSON, nullable=True)
    strengths = Column(JSON, nullable=True)
    weaknesses = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="resumes")


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    status = Column(String, default="active")
    overall_score = Column(Float, nullable=True)
    target_role = Column(String, nullable=True)
    target_company = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="interviews")

    questions = relationship(
        "Question",
        back_populates="interview",
        cascade="all, delete-orphan",
    )


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(
        Integer,
        ForeignKey("interviews.id"),
        nullable=False,
    )

    text = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    difficulty = Column(String, default="medium")
    created_at = Column(DateTime, default=datetime.utcnow)

    interview = relationship(
        "Interview",
        back_populates="questions",
    )

    answer = relationship(
        "Answer",
        back_populates="question",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)

    question_id = Column(
        Integer,
        ForeignKey("questions.id"),
        unique=True,
        nullable=False,
    )

    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    question = relationship(
        "Question",
        back_populates="answer",
    )

    evaluation = relationship(
        "Evaluation",
        back_populates="answer",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)

    answer_id = Column(
        Integer,
        ForeignKey("answers.id"),
        unique=True,
        nullable=False,
    )

    technical_score = Column(Float, nullable=True)
    communication_score = Column(Float, nullable=True)
    relevance_score = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=False)

    strengths = Column(JSON, nullable=True)
    weaknesses = Column(JSON, nullable=True)
    suggestions = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    answer = relationship(
        "Answer",
        back_populates="evaluation",
    )


class Progress(Base):
    __tablename__ = "progress"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
    )

    daily_streak = Column(Integer, default=0)
    overall_readiness = Column(Float, default=0.0)
    last_active_date = Column(
        DateTime,
        default=datetime.utcnow,
    )

    user = relationship(
        "User",
        back_populates="progress",
    )


class Roadmap(Base):
    __tablename__ = "roadmap"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    topic_name = Column(String, nullable=False)
    status = Column(String, default="pending")
    priority = Column(String, default="medium")
    recommendations = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship(
        "User",
        back_populates="roadmap_items",
    )

from datetime import timedelta

def record_user_activity(db, user_id: int):
    progress = db.query(Progress).filter(Progress.user_id == user_id).first()
    if not progress:
        progress = Progress(user_id=user_id, daily_streak=0, overall_readiness=0.0, last_active_date=None)
        db.add(progress)
        db.flush()
        
    today = datetime.utcnow().date()
    if progress.daily_streak == 0:
        progress.daily_streak = 1
    elif progress.last_active_date:
        last_active_day = progress.last_active_date.date()
        if last_active_day == today:
            pass
        elif last_active_day == today - timedelta(days=1):
            progress.daily_streak += 1
        else:
            progress.daily_streak = 1
    else:
        progress.daily_streak = 1
        
    progress.last_active_date = datetime.utcnow()
    db.commit()