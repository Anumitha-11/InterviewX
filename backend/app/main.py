from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database.session import engine, Base
from app.rag.ingestion import seed_knowledge_base
from app.api import auth, users, resume, interview, progress

# Create database tables automatically
Base.metadata.create_all(bind=engine)

# Seed ChromaDB knowledge base at startup
try:
    seed_knowledge_base()
except Exception as e:
    print(f"Startup warning - knowledge base seeding skipped: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS configuration
origins = [
    settings.FRONTEND_URL,
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "*" # Fallback global access
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(resume.router, prefix=f"{settings.API_V1_STR}/resume", tags=["resume"])
app.include_router(interview.router, prefix=f"{settings.API_V1_STR}/interview", tags=["interview"])
app.include_router(progress.router, prefix=f"{settings.API_V1_STR}/progress", tags=["progress"])

@app.get("/")
def root():
    return {"message": "Welcome to InterviewX API Engine. Go to /docs for Swagger documentation."}
