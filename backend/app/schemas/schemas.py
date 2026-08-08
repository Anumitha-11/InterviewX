from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr


# =========================
# Auth Schemas
# =========================

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: Optional[str] = None


# =========================
# Profile Schemas
# =========================

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    target_role: Optional[str] = None
    experience_level: Optional[str] = None
    target_company: Optional[str] = None
    preferred_type: Optional[str] = None
    skills: Optional[List[str]] = None


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    target_role: Optional[str] = None
    experience_level: Optional[str] = None
    target_company: Optional[str] = None
    preferred_type: Optional[str] = None
    skills: Optional[List[str]] = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime
    profile: Optional[ProfileOut] = None


# =========================
# Resume Schemas
# =========================

class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    parsed_skills: Optional[List[str]] = None
    parsed_projects: Optional[List[Dict[str, Any]]] = None
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    created_at: datetime


# =========================
# Evaluation Schema
# =========================

class EvaluationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    technical_score: Optional[float] = None
    communication_score: Optional[float] = None
    relevance_score: Optional[float] = None
    overall_score: float
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    suggestions: Optional[List[str]] = None


# =========================
# Answer Schemas
# =========================

class AnswerSubmit(BaseModel):
    text: str


class AnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    text: str
    evaluation: Optional[EvaluationOut] = None


# =========================
# Question Schemas
# =========================

class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    category: str
    difficulty: str
    answer: Optional[AnswerOut] = None


# =========================
# Interview Schemas
# =========================

class InterviewStart(BaseModel):
    target_role: Optional[str] = None
    target_company: Optional[str] = None


class InterviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    overall_score: Optional[float] = None
    target_role: Optional[str] = None
    target_company: Optional[str] = None
    created_at: datetime
    finished_at: Optional[datetime] = None
    questions: List[QuestionOut] = []


class InterviewReport(BaseModel):
    id: int
    overall_score: Optional[float] = None
    created_at: datetime
    finished_at: Optional[datetime] = None
    questions: List[QuestionOut] = []
    strengths: List[str] = []
    weaknesses: List[str] = []
    general_feedback: str


# =========================
# Roadmap Schema
# =========================

class RoadmapOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_name: str
    status: str
    priority: str
    recommendations: Optional[str] = None


# =========================
# Dashboard Schema
# =========================

class DashboardData(BaseModel):
    overall_readiness: float
    daily_streak: int
    resume_uploaded: bool
    resume_filename: Optional[str] = None
    target_role: Optional[str] = None
    target_company: Optional[str] = None
    skills_fit: Dict[str, Any]
    weak_areas: List[str]
    strong_areas: List[str]
    recent_activity: List[Dict[str, Any]]
    recommended_topics: List[Dict[str, Any]]
    roadmap: List[RoadmapOut]