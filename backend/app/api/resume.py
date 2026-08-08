import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import fitz  # PyMuPDF
from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.models import User, Resume, Profile, record_user_activity
from app.schemas.schemas import ResumeOut
from app.agents.resume_agent import ResumeAgent
from app.core.config import settings

router = APIRouter()

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not parse PDF file: {str(e)}"
        )

@router.post("/upload", response_model=ResumeOut)
def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported for resume upload."
        )
        
    try:
        # Read file bytes
        file_bytes = file.file.read()
        
        # Save to uploads folder
        save_path = os.path.join(settings.UPLOAD_DIR, f"{current_user.id}_{file.filename}")
        with open(save_path, "wb") as f:
            f.write(file_bytes)
            
        # Extract text
        raw_text = extract_text_from_pdf(file_bytes)
        
        # Parse resume via Agent
        parsed_data = ResumeAgent.parse(raw_text)
        
        # Create Resume database object
        db_resume = Resume(
            user_id=current_user.id,
            file_name=file.filename,
            raw_text=raw_text,
            parsed_skills=parsed_data.skills,
            parsed_projects=parsed_data.projects,
            strengths=parsed_data.strengths,
            weaknesses=parsed_data.weaknesses
        )
        db.add(db_resume)
        
        # Update current user profile skills
        profile = current_user.profile
        if profile:
            # Combine current skills and new parsed skills, remove duplicates
            current_skills = profile.skills or []
            new_skills = parsed_data.skills or []
            combined_skills = list(set(current_skills + new_skills))
            profile.skills = combined_skills
            
            # If the resume highlights a core role, we can set target_role as well
            if len(new_skills) > 0 and not profile.target_role:
                profile.target_role = "Senior Fullstack Developer"
                
        # Record activity and update streak
        record_user_activity(db, current_user.id)
        
        db.commit()
        db.refresh(db_resume)
        
        return db_resume
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Internal error processing resume: {str(e)}"
        )
