import json
import random
from datetime import datetime
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session
from app.core.config import settings
from app.rag.retriever import RAGRetriever
from app.models.models import User, Profile, Resume, Interview, Question, Answer, Evaluation, Roadmap, Progress

# 1. State Definition
class InterviewState(TypedDict):
    user_id: int
    interview_id: int
    target_role: str
    target_company: str
    experience_level: str
    skills: List[str]
    rag_context: str
    questions_asked: List[Dict[str, Any]]
    answers_submitted: List[Dict[str, Any]]
    current_question: Optional[Dict[str, Any]]
    current_answer: Optional[str]
    current_evaluation: Optional[Dict[str, Any]]
    cumulative_score: float
    weak_areas: List[str]
    strong_areas: List[str]
    roadmap_recommendations: List[str]
    next_action: str # "ask_question", "finish_interview"
    agent_logs: List[str]

# 2. Node Functions

def load_profile_node(state: InterviewState) -> InterviewState:
    logs = list(state.get("agent_logs", []))
    logs.append("✓ Profile loaded")
    
    # We fetch profile/skills inside the service but we record the log here
    return {**state, "agent_logs": logs}

def retrieve_context_node(state: InterviewState) -> InterviewState:
    logs = list(state.get("agent_logs", []))
    logs.append("✓ Relevant knowledge retrieved")
    
    # Query RAG retriever based on target role and skills
    query = f"{state['target_role']} " + " ".join(state['skills'][:3])
    contexts = RAGRetriever.retrieve(query, limit=1)
    context_text = contexts[0]["content"] if contexts else "Standard tech preparation guidelines."
    
    return {**state, "rag_context": context_text, "agent_logs": logs}

# Question Agent Node
def question_agent_node(state: InterviewState) -> InterviewState:
    logs = list(state.get("agent_logs", []))
    logs.append("✓ Question generated")
    
    target_role = state["target_role"]
    skills = state["skills"]
    asked_texts = [q["text"] for q in state["questions_asked"]]
    
    question_text = ""
    category = "technical"
    difficulty = "medium"
    
    if settings.LLM_MODE == "mock":
        # Predefined list of mock questions tailored to categories
        mock_question_pool = [
            {
                "text": "What is the primary difference between a process and a thread in Python? How does the Global Interpreter Lock (GIL) impact concurrency?",
                "category": "technical",
                "difficulty": "medium",
                "keywords": ["gil", "thread", "process", "concurrency", "lock"]
            },
            {
                "text": "How would you design a rate limiting system for a distributed REST API? Which algorithms or database structures (e.g. Redis) would you apply?",
                "category": "technical",
                "difficulty": "hard",
                "keywords": ["rate limiter", "redis", "token bucket", "leaky bucket", "scaling"]
            },
            {
                "text": "Explain the difference between a clustered and a non-clustered index in SQL database engines. When would you prefer one over the other?",
                "category": "sql",
                "difficulty": "medium",
                "keywords": ["index", "clustered", "non-clustered", "b-tree", "sorting"]
            },
            {
                "text": "Describe a scenario where you faced a technical conflict or disagreement with a teammate. How did you structure your communication and resolve it?",
                "category": "behavioral",
                "difficulty": "easy",
                "keywords": ["conflict", "communication", "compromise", "collaboration", "star"]
            },
            {
                "text": "What is overfitting in deep learning models? Explain two regularization techniques you can use to mitigate it during training.",
                "category": "ai_ml",
                "difficulty": "medium",
                "keywords": ["overfitting", "dropout", "regularization", "validation", "weights"]
            }
        ]
        
        # Filter out questions already asked
        available_questions = [q for q in mock_question_pool if q["text"] not in asked_texts]
        if not available_questions:
            # Fallback
            selected = mock_question_pool[0]
        else:
            # Pick one that matches the user's skills if possible
            selected = random.choice(available_questions)
            
        question_text = selected["text"]
        category = selected["category"]
        difficulty = selected["difficulty"]
    else:
        # OpenAI Real Mode
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import JsonOutputParser
            from pydantic import BaseModel, Field
            
            class QuestionSchema(BaseModel):
                text: str = Field(description="The interview question text.")
                category: str = Field(description="One of: technical, behavioral, hr, coding, sql, ai_ml.")
                difficulty: str = Field(description="One of: easy, medium, hard.")
                
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, openai_api_key=settings.OPENAI_API_KEY)
            structured_llm = llm.with_structured_output(QuestionSchema)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an Interviewer Agent. Generate a highly personalized interview question based on the user's profile: Target Role: {role}, Company: {company}, Experience: {exp}, Skills: {skills}. Background knowledge base context: {context}. Avoid asking any of these previously asked questions: {asked}."),
                ("user", "Generate the next question.")
            ])
            
            chain = prompt | structured_llm
            res = chain.invoke({
                "role": target_role,
                "company": state["target_company"],
                "exp": state["experience_level"],
                "skills": ", ".join(skills),
                "context": state["rag_context"],
                "asked": json.dumps(asked_texts)
            })
            question_text = res.text
            category = res.category
            difficulty = res.difficulty
        except Exception as e:
            print(f"Error calling OpenAI for QuestionAgent: {e}. Falling back to mock pool.")
            # Fallback mock pickup
            question_text = "Explain the difference between a clustered and non-clustered index in SQL."
            category = "sql"
            difficulty = "medium"

    current_q = {
        "text": question_text,
        "category": category,
        "difficulty": difficulty
    }
    
    return {
        **state,
        "current_question": current_q,
        "agent_logs": logs
    }

# Evaluation & Feedback Node
def evaluation_agent_node(state: InterviewState) -> InterviewState:
    logs = list(state.get("agent_logs", []))
    logs.append("● Evaluating answer")
    logs.append("○ Updating roadmap")
    
    question = state["current_question"]
    answer = state["current_answer"]
    
    tech_score = 7.0
    comm_score = 7.0
    rel_score = 7.0
    overall_score = 7.0
    strengths = []
    weaknesses = []
    suggestions = []
    
    if settings.LLM_MODE == "mock":
        # Parse answer text for basic score validation
        ans_lower = answer.lower()
        
        # Determine keywords related to current question
        keywords = []
        if "gil" in question["text"].lower():
            keywords = ["lock", "thread", "process", "concurrency", "interpreter"]
            topic_area = "Python Concurrency"
        elif "rate" in question["text"].lower():
            keywords = ["redis", "token", "bucket", "leaky", "limit"]
            topic_area = "System Design Rate Limiting"
        elif "index" in question["text"].lower():
            keywords = ["clustered", "non-clustered", "physically", "b-tree"]
            topic_area = "Database Indexing"
        elif "conflict" in question["text"].lower():
            keywords = ["communication", "resolve", "compromise", "team", "star"]
            topic_area = "Behavioral STAR Model"
        else:
            keywords = ["model", "overfitting", "dropout", "regularization"]
            topic_area = "AI/ML Regularization"

        matches = sum(1 for kw in keywords if kw in ans_lower)
        score_base = 5.0 + (matches / len(keywords)) * 4.5 if keywords else 7.5
        
        tech_score = min(10.0, score_base)
        comm_score = min(10.0, score_base + 0.5)
        rel_score = min(10.0, score_base + 1.0)
        overall_score = round((tech_score + comm_score + rel_score) / 3.0, 1)
        
        if matches >= 3:
            strengths.append(f"Properly identified core concepts of {topic_area}.")
            strengths.append("Structured technical definitions correctly.")
            suggestions.append("To score even higher, quantify past deployment experiences.")
        else:
            weaknesses.append(f"Missed key conceptual associations for {topic_area}.")
            weaknesses.append("Answer lacks implementation depth.")
            suggestions.append(f"Review core documentation for {topic_area} (e.g. keywords: {', '.join(keywords)}).")
            
    else:
        # OpenAI Real Mode
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.prompts import ChatPromptTemplate
            from pydantic import BaseModel, Field
            
            class EvaluationSchema(BaseModel):
                technical_score: float = Field(description="Score for technical correctness (1 to 10).")
                communication_score: float = Field(description="Score for communication and clarity (1 to 10).")
                relevance_score: float = Field(description="Score for relevance to the prompt (1 to 10).")
                overall_score: float = Field(description="Weighted overall score (1 to 10).")
                strengths: List[str] = Field(description="List of candidate's answer strengths.")
                weaknesses: List[str] = Field(description="List of weaknesses or gaps in the answer.")
                suggestions: List[str] = Field(description="Actionable improvement suggestions.")
                
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0, openai_api_key=settings.OPENAI_API_KEY)
            structured_llm = llm.with_structured_output(EvaluationSchema)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an AI Grading Agent. Evaluate the candidate's response to the following question. Compare against RAG guidelines: {context}. Give structured feedback and scores."),
                ("user", "Question: {question}\nCandidate Answer: {answer}")
            ])
            
            chain = prompt | structured_llm
            res = chain.invoke({
                "question": question["text"],
                "answer": answer,
                "context": state["rag_context"]
            })
            
            tech_score = res.technical_score
            comm_score = res.communication_score
            rel_score = res.relevance_score
            overall_score = res.overall_score
            strengths = res.strengths
            weaknesses = res.weaknesses
            suggestions = res.suggestions
        except Exception as e:
            print(f"Error calling OpenAI for EvaluationAgent: {e}. Falling back to default scores.")
            
    eval_res = {
        "technical_score": tech_score,
        "communication_score": comm_score,
        "relevance_score": rel_score,
        "overall_score": overall_score,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "suggestions": suggestions
    }
    
    # Update weak/strong areas based on evaluation
    weak = list(state.get("weak_areas", []))
    strong = list(state.get("strong_areas", []))
    roadmap_recs = list(state.get("roadmap_recommendations", []))
    
    category_name = question["category"].capitalize()
    if overall_score < 7.5:
        if category_name not in weak:
            weak.append(category_name)
        if suggestions and suggestions[0] not in roadmap_recs:
            roadmap_recs.append(f"{category_name}: {suggestions[0]}")
    else:
        if category_name not in strong:
            strong.append(category_name)
            
    # Remove from weak if now strong
    if overall_score >= 8.5 and category_name in weak:
        weak.remove(category_name)
        
    next_act = "ask_question"
    if len(state["questions_asked"]) + 1 >= 3: # Let's say a mock session is 3 questions
        next_act = "finish_interview"
        
    return {
        **state,
        "current_evaluation": eval_res,
        "weak_areas": weak,
        "strong_areas": strong,
        "roadmap_recommendations": roadmap_recs,
        "next_action": next_act,
        "agent_logs": logs
    }

# 3. Build LangGraph workflows (separate graphs for each entry point)

def _build_question_generation_graph():
    """START INTERVIEW: load_profile -> retrieve_context -> generate_question"""
    graph = StateGraph(InterviewState)
    graph.add_node("load_profile", load_profile_node)
    graph.add_node("retrieve_context", retrieve_context_node)
    graph.add_node("generate_question", question_agent_node)
    graph.set_entry_point("load_profile")
    graph.add_edge("load_profile", "retrieve_context")
    graph.add_edge("retrieve_context", "generate_question")
    graph.add_edge("generate_question", END)
    return graph.compile()


def _build_evaluation_graph():
    """ANSWER SUBMISSION: evaluate_answer -> feedback + next_action decision"""
    graph = StateGraph(InterviewState)
    graph.add_node("evaluate_answer", evaluation_agent_node)
    graph.set_entry_point("evaluate_answer")
    graph.add_edge("evaluate_answer", END)
    return graph.compile()


question_generation_graph = _build_question_generation_graph()
evaluation_graph = _build_evaluation_graph()

# 4. Engine Manager
class InterviewEngine:
    @staticmethod
    def start_interview_session(db: Session, user_id: int, target_role: str = None, target_company: str = None) -> Interview:
        user = db.query(User).filter(User.id == user_id).first()
        profile = user.profile
        
        role = target_role or (profile.target_role if profile else "Software Engineer")
        company = target_company or (profile.target_company if profile else "General")
        
        # Create Interview Session record
        interview = Interview(
            user_id=user_id,
            status="active",
            target_role=role,
            target_company=company
        )
        db.add(interview)
        db.commit()
        db.refresh(interview)
        
        # Initialize LangGraph State
        initial_state = {
            "user_id": user_id,
            "interview_id": interview.id,
            "target_role": role,
            "target_company": company,
            "experience_level": profile.experience_level if profile else "Mid Level",
            "skills": profile.skills if profile else ["Python", "SQL"],
            "rag_context": "",
            "questions_asked": [],
            "answers_submitted": [],
            "current_question": None,
            "current_answer": None,
            "current_evaluation": None,
            "cumulative_score": 0.0,
            "weak_areas": [],
            "strong_areas": [],
            "roadmap_recommendations": [],
            "next_action": "ask_question",
            "agent_logs": []
        }
        
        # Run question-generation workflow for the first question
        final_state = question_generation_graph.invoke(initial_state)
        
        # Store generated question in DB
        db_question = Question(
            interview_id=interview.id,
            text=final_state["current_question"]["text"],
            category=final_state["current_question"]["category"],
            difficulty=final_state["current_question"]["difficulty"]
        )
        db.add(db_question)
        db.commit()
        
        return interview

    @staticmethod
    def submit_answer(db: Session, interview_id: int, answer_text: str) -> Dict[str, Any]:
        interview = db.query(Interview).filter(Interview.id == interview_id).first()
        if not interview:
            return {"error": "Interview session not found"}
            
        user = interview.user
        profile = user.profile
        
        # Gather history
        questions = db.query(Question).filter(Question.interview_id == interview.id).all()
        
        questions_asked_state = []
        answers_submitted_state = []
        evaluations_state = []
        
        current_db_question = None
        
        for q in questions:
            q_dict = {"text": q.text, "category": q.category, "difficulty": q.difficulty}
            questions_asked_state.append(q_dict)
            
            if q.answer:
                answers_submitted_state.append({"question_id": q.id, "text": q.answer.text})
                if q.answer.evaluation:
                    evaluations_state.append({
                        "technical_score": q.answer.evaluation.technical_score,
                        "overall_score": q.answer.evaluation.overall_score
                    })
            else:
                # This is the question currently being answered
                current_db_question = q
                
        if not current_db_question:
            return {"error": "No pending active question found to answer"}
            
        # Reconstruct LangGraph State
        state = {
            "user_id": interview.user_id,
            "interview_id": interview.id,
            "target_role": interview.target_role or "Software Engineer",
            "target_company": interview.target_company or "General",
            "experience_level": profile.experience_level if profile else "Mid Level",
            "skills": profile.skills if profile else ["Python"],
            "rag_context": "",
            "questions_asked": questions_asked_state[:-1], # excluding active one, node adds logs
            "answers_submitted": answers_submitted_state,
            "current_question": {
                "text": current_db_question.text,
                "category": current_db_question.category,
                "difficulty": current_db_question.difficulty
            },
            "current_answer": answer_text,
            "current_evaluation": None,
            "cumulative_score": sum([e["overall_score"] for e in evaluations_state]),
            "weak_areas": [],
            "strong_areas": [],
            "roadmap_recommendations": [],
            "next_action": "ask_question",
            "agent_logs": []
        }
        
        # Save submitted answer
        db_answer = Answer(
            question_id=current_db_question.id,
            text=answer_text
        )
        db.add(db_answer)
        db.flush() # Get db_answer.id
        
        # Step 1: Run evaluation workflow (feedback + next_action decision)
        eval_state = evaluation_graph.invoke(state)
        
        # Save evaluation to DB
        eval_data = eval_state["current_evaluation"]
        db_eval = Evaluation(
            answer_id=db_answer.id,
            technical_score=eval_data["technical_score"],
            communication_score=eval_data["communication_score"],
            relevance_score=eval_data["relevance_score"],
            overall_score=eval_data["overall_score"],
            strengths=eval_data["strengths"],
            weaknesses=eval_data["weaknesses"],
            suggestions=eval_data["suggestions"]
        )
        db.add(db_eval)
        
        # Step 2: Determine next step or end session
        next_action = eval_state["next_action"]
        next_question_dict = None
        
        if next_action == "ask_question":
            # Re-initialize state logs for next question generation
            next_state_setup = {
                **eval_state,
                "questions_asked": questions_asked_state, # now includes previous question
                "answers_submitted": answers_submitted_state + [{"question_id": current_db_question.id, "text": answer_text}],
                "agent_logs": []
            }
            # Run question-generation workflow for the next question
            next_state = question_generation_graph.invoke(next_state_setup)
            next_question_dict = next_state["current_question"]
            
            # Save next question in DB
            db_next_q = Question(
                interview_id=interview.id,
                text=next_question_dict["text"],
                category=next_question_dict["category"],
                difficulty=next_question_dict["difficulty"]
            )
            db.add(db_next_q)
            
            # Update agent logs
            agent_logs = next_state["agent_logs"]
        else:
            # End interview, calculate final scores
            interview.status = "completed"
            interview.finished_at = datetime.utcnow()
            
            # Flush changes to make the latest evaluation queryable
            db.flush()
            
            # Calculate final overall score from all evaluations in DB
            scores = [
                row[0] for row in db.query(Evaluation.overall_score)
                .join(Answer, Evaluation.answer_id == Answer.id)
                .join(Question, Answer.question_id == Question.id)
                .filter(Question.interview_id == interview.id)
                .all()
            ]
            
            final_overall_score = round(sum(scores) / len(scores), 1) if scores else 7.0
            interview.overall_score = final_overall_score
            
            # Update user metrics/roadmap
            from app.models.models import record_user_activity
            record_user_activity(db, interview.user_id)
                
            # Add new roadmap recommendations
            for rec in eval_state["roadmap_recommendations"]:
                topic_name, rec_desc = rec.split(":", 1) if ":" in rec else (rec, "Review recommended technical questions.")
                # check if topic already exists
                existing = db.query(Roadmap).filter(
                    Roadmap.user_id == interview.user_id,
                    Roadmap.topic_name == topic_name.strip()
                ).first()
                if not existing:
                    db_road = Roadmap(
                        user_id=interview.user_id,
                        topic_name=topic_name.strip(),
                        priority="high",
                        status="pending",
                        recommendations=rec_desc.strip()
                    )
                    db.add(db_road)
                    
            agent_logs = eval_state["agent_logs"] + ["🎉 Interview completed! Report generated"]
            
        db.commit()
        
        return {
            "evaluation": eval_data,
            "next_action": next_action,
            "next_question": next_question_dict,
            "agent_logs": agent_logs
        }
