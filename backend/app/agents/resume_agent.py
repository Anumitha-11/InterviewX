import json
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from app.core.config import settings

class ParsedResumeSchema(BaseModel):
    skills: List[str] = Field(description="List of technical skills, languages, frameworks, databases, etc.")
    projects: List[Dict[str, Any]] = Field(description="Key projects listed, with title, technologies, and short description.")
    strengths: List[str] = Field(description="Top professional strengths or core competencies.")
    weaknesses: List[str] = Field(description="Potential areas of improvement or skills that could be stronger.")

def parse_resume_mock(raw_text: str) -> ParsedResumeSchema:
    # Scan the text for common keywords to provide mock personalization
    tech_keywords = [
        "Python", "JavaScript", "TypeScript", "React", "Node", "FastAPI", "Django", "Flask", 
        "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis", "Docker", "Kubernetes", "AWS", 
        "GCP", "Azure", "Git", "LangChain", "PyTorch", "TensorFlow", "HTML", "CSS"
    ]
    found_skills = []
    text_lower = raw_text.lower()
    for kw in tech_keywords:
        if kw.lower() in text_lower:
            found_skills.append(kw)
            
    if len(found_skills) < 3:
        # Defaults if text is very short or doesn't match
        found_skills.extend(["Python", "JavaScript", "SQL", "API Design", "Docker"])
        
    found_skills = list(set(found_skills))
    
    mock_projects = [
        {
            "title": "Agentic AI Analytics Hub",
            "technologies": ["Python", "LangChain", "FastAPI", "React"],
            "description": "Developed a real-time data parsing service orchestrating multi-agent state machines to automate document auditing."
        },
        {
            "title": "Scalable Vector Database Interface",
            "technologies": ["PostgreSQL", "ChromaDB", "Docker"],
            "description": "Engineered a high-performance vector retrieval API that indexed unstructured training data for low-latency queries."
        }
    ]
    
    # Filter projects based on found skills
    for proj in mock_projects:
        proj["technologies"] = [tech for tech in proj["technologies"] if tech in found_skills]
        if not proj["technologies"]:
            proj["technologies"] = ["Python", "API Design"]

    return ParsedResumeSchema(
        skills=found_skills,
        projects=mock_projects,
        strengths=[
            "Strong foundation in software engineering and API development",
            "Experience building modular services and integrating databases",
            "Fast learner eager to apply Agentic AI and multi-agent systems"
        ],
        weaknesses=[
            "Relatively fresh to deploying large scale Kubernetes clusters",
            "Needs deeper experience with advanced deep learning frameworks",
            "Could improve structural performance tuning on heavy SQL databases"
        ]
    )

def parse_resume_real(raw_text: str) -> ParsedResumeSchema:
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate
        
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0,
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        structured_llm = llm.with_structured_output(ParsedResumeSchema)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert AI Resume Parsing Agent. Parse the candidate's resume text and extract skills, key projects (with title, technologies, and description), professional strengths, and potential engineering weaknesses/gaps relative to modern high-performing roles."),
            ("user", "Parse the following resume:\n\n{resume_text}")
        ])
        
        chain = prompt | structured_llm
        result = chain.invoke({"resume_text": raw_text})
        return result
    except Exception as e:
        print(f"Error parsing resume via OpenAI: {e}. Falling back to mock parser.")
        return parse_resume_mock(raw_text)

class ResumeAgent:
    @staticmethod
    def parse(raw_text: str) -> ParsedResumeSchema:
        if settings.LLM_MODE == "mock":
            return parse_resume_mock(raw_text)
        else:
            return parse_resume_real(raw_text)
