from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.models import User, Progress, Resume, Interview, Roadmap, Question, record_user_activity
from app.schemas.schemas import DashboardData, RoadmapOut
from typing import List, Dict, Any
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/dashboard", response_model=DashboardData)
def get_dashboard_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Fetch Progress
    progress = current_user.progress
    if not progress:
        progress = Progress(user_id=current_user.id, daily_streak=0, overall_readiness=0.0, last_active_date=None)
        db.add(progress)
        db.commit()
        db.refresh(progress)
        
    # Check if streak is broken/expired due to inactivity
    today = datetime.utcnow().date()
    if progress.last_active_date:
        last_active_day = progress.last_active_date.date()
        if last_active_day < today - timedelta(days=1):
            progress.daily_streak = 0
            db.commit()
            
    # Fetch Resume status
    latest_resume = db.query(Resume).filter(
        Resume.user_id == current_user.id
    ).order_by(Resume.created_at.desc()).first()
    
    resume_uploaded = latest_resume is not None
    resume_filename = latest_resume.file_name if latest_resume else None
    
    # Calculate skills fit
    skills_fit = {}
    profile_skills = current_user.profile.skills if current_user.profile and current_user.profile.skills else []
    resume_skills = latest_resume.parsed_skills if latest_resume and latest_resume.parsed_skills else []
    
    # Deduplicate skills
    all_user_skills = list(set([s.strip() for s in (profile_skills + resume_skills) if s.strip()]))
    
    # Calculate completed interviews for scoring adjustments
    completed_interviews = db.query(Interview).filter(
        Interview.user_id == current_user.id,
        Interview.status == "completed"
    ).all()
    
    if all_user_skills:
        for skill in all_user_skills:
            # Adjustment based on interview evaluations
            scores = []
            for inter in completed_interviews:
                for q in inter.questions:
                    if q.answer and q.answer.evaluation:
                        if (skill.lower() in q.category.lower()) or (skill.lower() in q.text.lower()):
                            scores.append(q.answer.evaluation.overall_score)
                            
            if scores:
                avg_score = sum(scores) / len(scores)
                percentage = avg_score * 10.0
                skills_fit[skill] = round(percentage, 1)
            else:
                skills_fit[skill] = "Not assessed"

    # Fetch roadmap
    roadmap_items = db.query(Roadmap).filter(
        Roadmap.user_id == current_user.id
    ).order_by(Roadmap.created_at.desc()).all()

    # Determine weak and strong areas dynamically
    weak_areas = []
    strong_areas = []
    
    if completed_interviews:
        category_scores = {}
        for inter in completed_interviews:
            for q in inter.questions:
                if q.answer and q.answer.evaluation:
                    cat = q.category.capitalize()
                    if cat not in category_scores:
                        category_scores[cat] = []
                    category_scores[cat].append(q.answer.evaluation.overall_score)
                    
        for cat, scores in category_scores.items():
            avg_cat_score = sum(scores) / len(scores)
            if avg_cat_score < 7.5:
                weak_areas.append(cat)
            else:
                strong_areas.append(cat)
    else:
        if latest_resume:
            if latest_resume.strengths:
                strong_areas = [s.capitalize() for s in latest_resume.strengths[:3]]
            if latest_resume.weaknesses:
                weak_areas = [w.capitalize() for w in latest_resume.weaknesses[:3]]
                
    weak_areas = list(set(weak_areas))
    strong_areas = list(set(strong_areas))
    weak_areas = [w for w in weak_areas if w not in strong_areas]

    # Calculate overall readiness
if not completed_interviews:
    overall_readiness = 0.0
else:
    # 1. Interview performance = 70%
    avg_scores = [
        i.overall_score
        for i in completed_interviews
        if i.overall_score is not None
    ]

    interview_score = (
        (sum(avg_scores) / len(avg_scores)) * 10
        if avg_scores
        else 0.0
    )

    # 2. Assessed skills = 20%
    assessed_skill_scores = [
        score
        for score in skills_fit.values()
        if isinstance(score, (int, float))
    ]

    skill_score = (
        sum(assessed_skill_scores) / len(assessed_skill_scores)
        if assessed_skill_scores
        else 0.0
    )

    # 3. Profile/resume completeness = 10%
    profile_score = 0.0

    if current_user.profile:
        if current_user.profile.target_role:
            profile_score += 2.5
        if current_user.profile.target_company:
            profile_score += 2.5
        if current_user.profile.skills:
            profile_score += 2.5

    if latest_resume:
        profile_score += 2.5

    # Final readiness
    overall_readiness = round(
        interview_score * 0.70
        + skill_score * 0.20
        + profile_score,
        1
    )

    overall_readiness = min(100.0, max(0.0, overall_readiness))

    # Calculate recent activities
    recent_activity = []
    all_interviews = db.query(Interview).filter(
        Interview.user_id == current_user.id
    ).order_by(Interview.created_at.desc()).limit(5).all()
    
    for inter in all_interviews:
        recent_activity.append({
            "type": "interview",
            "title": f"Mock prep for {inter.target_role or 'Software Engineer'}",
            "description": f"Overall Score: {inter.overall_score}/10" if inter.status == "completed" else "Active session",
            "date": inter.created_at.strftime("%Y-%m-%d %H:%M")
        })
        
    if latest_resume:
        recent_activity.append({
            "type": "resume",
            "title": "Uploaded Resume",
            "description": f"Analyzed {latest_resume.file_name}",
            "date": latest_resume.created_at.strftime("%Y-%m-%d %H:%M")
        })
        
    recent_activity.sort(key=lambda x: x["date"], reverse=True)

    recommended_topics = []
    for item in roadmap_items:
        if item.status == "pending":
            recommended_topics.append({
                "topic": item.topic_name,
                "priority": item.priority,
                "reason": item.recommendations
            })

    return {
        "overall_readiness": overall_readiness,
        "daily_streak": progress.daily_streak,
        "resume_uploaded": resume_uploaded,
        "resume_filename": resume_filename,
        "target_role": current_user.profile.target_role if current_user.profile else None,
        "target_company": current_user.profile.target_company if current_user.profile else None,
        "skills_fit": skills_fit,
        "weak_areas": weak_areas,
        "strong_areas": strong_areas,
        "recent_activity": recent_activity[:5],
        "recommended_topics": recommended_topics[:3],
        "roadmap": roadmap_items
    }

@router.get("/roadmap", response_model=List[RoadmapOut])
def get_roadmap(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    roadmap_items = db.query(Roadmap).filter(
        Roadmap.user_id == current_user.id
    ).order_by(Roadmap.created_at.desc()).all()
    return roadmap_items

@router.put("/roadmap/{item_id}", response_model=RoadmapOut)
def update_roadmap_item(
    item_id: int,
    status: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    roadmap_item = db.query(Roadmap).filter(
        Roadmap.id == item_id,
        Roadmap.user_id == current_user.id
    ).first()
    if not roadmap_item:
        raise HTTPException(status_code=404, detail="Roadmap item not found")
        
    if status not in ["pending", "in_progress", "completed"]:
        raise HTTPException(status_code=400, detail="Invalid status. Must be pending, in_progress, or completed")
        
    roadmap_item.status = status
    db.commit()
    db.refresh(roadmap_item)
    return roadmap_item
