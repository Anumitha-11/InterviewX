from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.models import User, Interview, Question, Answer, Evaluation, record_user_activity
from app.schemas.schemas import InterviewStart, InterviewOut, AnswerSubmit, InterviewReport
from app.agents.interviewer_agent import InterviewEngine
from typing import List, Dict, Any

router = APIRouter()

@router.post("/start", response_model=InterviewOut)
def start_interview(
    session_in: InterviewStart,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Record activity and update streak
        record_user_activity(db, current_user.id)
        
        db_interview = InterviewEngine.start_interview_session(
            db=db,
            user_id=current_user.id,
            target_role=session_in.target_role,
            target_company=session_in.target_company
        )
        return db_interview
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start interview session: {str(e)}"
        )

@router.post("/{interview_id}/answer")
def submit_answer(
    interview_id: int,
    answer_in: AnswerSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify interview ownership
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.user_id == current_user.id
    ).first()
    if not interview:
        raise HTTPException(
            status_code=404,
            detail="Interview session not found."
        )
        
    if interview.status == "completed":
        raise HTTPException(
            status_code=400,
            detail="This interview session is already completed."
        )
        
    result = InterviewEngine.submit_answer(
        db=db,
        interview_id=interview_id,
        answer_text=answer_in.text
    )
    
    if "error" in result:
        raise HTTPException(
            status_code=400,
            detail=result["error"]
        )
        
    # Record activity and update streak
    record_user_activity(db, current_user.id)
    
    return result

@router.get("/history", response_model=List[InterviewOut])
def get_interview_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    interviews = db.query(Interview).filter(
        Interview.user_id == current_user.id
    ).order_by(Interview.created_at.desc()).all()
    return interviews

@router.get("/{interview_id}/report", response_model=InterviewReport)
def get_interview_report(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.user_id == current_user.id
    ).first()
    if not interview:
        raise HTTPException(
            status_code=404,
            detail="Interview session not found."
        )
        
    if interview.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Report is only available for completed interview sessions."
        )
        
    # Gather all questions, evaluations, strengths, weaknesses
    questions = db.query(Question).filter(Question.interview_id == interview.id).all()
    
    all_strengths = []
    all_weaknesses = []
    
    for q in questions:
        if q.answer and q.answer.evaluation:
            all_strengths.extend(q.answer.evaluation.strengths or [])
            all_weaknesses.extend(q.answer.evaluation.weaknesses or [])
            
    # Clean duplicates
    all_strengths = list(set(all_strengths))
    all_weaknesses = list(set(all_weaknesses))
    
    feedback_summary = (
        f"You successfully completed your preparation run for {interview.target_role} at {interview.target_company}. "
        f"Your technical responses showed clear capability, scoring an overall average of {interview.overall_score}/10. "
        "Review the target topics inside your dashboard study roadmap to patch up critical conceptual gaps."
    )
    
    return {
        "id": interview.id,
        "overall_score": interview.overall_score,
        "created_at": interview.created_at,
        "finished_at": interview.finished_at,
        "questions": questions,
        "strengths": all_strengths,
        "weaknesses": all_weaknesses,
        "general_feedback": feedback_summary
    }
