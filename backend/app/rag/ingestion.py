import os
import json
from app.core.config import settings
from app.rag.vectorstore import VectorStoreManager
from app.rag.embeddings import get_embedding_function

# Baseline QA data structure
baseline_knowledge = [
    {
        "title": "Data Structures & Algorithms - Space/Time Complexity",
        "category": "dsa",
        "content": "When evaluating DSA questions, focus on Big O analysis. Time complexity describes how runtime grows relative to input size, while Space complexity describes additional memory used. For sorting, QuickSort is O(N log N) average and O(N^2) worst case, whereas MergeSort is O(N log N) guaranteed but takes O(N) auxiliary space. Binary trees traversal (DFS, BFS) are O(N) time. Dynamic programming solves problems by caching subproblems, trading space O(N) for speed."
    },
    {
        "title": "System Design - Caching & Database Indexing",
        "category": "technical",
        "content": "For scalability, use caching (Redis/Memcached) to prevent DB overloading. Clustered indexes physically sort database table rows, so only one can exist per table. Non-clustered indexes create separate lookup structures holding pointers to the physical rows. Use Consistent Hashing for distributing cache entries across multiple nodes, ensuring that adding or removing a node shifts only a minimal number of keys."
    },
    {
        "title": "SQL - Window Functions & Joins",
        "category": "sql",
        "content": "SQL window functions compute calculations over a set of table rows related to the current row without grouping (e.g., ROW_NUMBER(), RANK(), DENSE_RANK() OVER (PARTITION BY ... ORDER BY ...)). INNER JOIN returns matching rows in both tables. LEFT JOIN returns all rows from the left table and matching rows from the right table. Indexing foreign keys accelerates join queries."
    },
    {
        "title": "AI & Machine Learning - LLM Temperature & RAG Vectors",
        "category": "ai_ml",
        "content": "Retrieval-Augmented Generation (RAG) grounds Large Language Model prompts with relevant documents retrieved from a vector database (e.g., ChromaDB, Pinecone). LLM Temperature dictates generation creativity: 0.0 is deterministic and optimal for coding/factual tasks, whereas 0.7+ introduces high randomness. Vector databases store numerical embeddings representing semantic meanings of texts and use cosine similarity to query matches."
    },
    {
        "title": "HR - Dynamic Introductions & Salary Negotiation",
        "category": "hr",
        "content": "When asked 'Tell me about yourself', follow the Present-Past-Future model: describe your current role and major achievements, transition to past experience highlights showing progression, and explain why this specific target role and company fit your future career plans. For salary, defer negotiation until you have an offer, benchmark rates using industry resources, and express collaborative excitement."
    },
    {
        "title": "Behavioral Interviews - The STAR Technique",
        "category": "behavioral",
        "content": "The STAR technique stands for Situation, Task, Action, and Result. When answering behavioral questions like 'Tell me about a conflict', specify: Situation (the background context), Task (your specific responsibility), Action (what you did, how you collaborated, tools you used), and Result (the quantifiable outcome, e.g. metrics improved, tasks finished, lessons learned). Focus action statements on 'I' rather than 'We'."
    }
]

def seed_knowledge_base():
    kb_dir = settings.KNOWLEDGE_BASE_DIR
    os.makedirs(kb_dir, exist_ok=True)
    json_path = os.path.join(kb_dir, "baseline_qa.json")
    
    # Save JSON baseline file if not exists
    if not os.path.exists(json_path):
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(baseline_knowledge, f, indent=2)
        print(f"Created baseline knowledge file at {json_path}")
    
    try:
        # Load from file
        with open(json_path, "r", encoding="utf-8") as f:
            documents = json.load(f)
            
        embedding_fn = get_embedding_function()
        client = VectorStoreManager.get_client()
        
        # Get or create collection
        collection = client.get_or_create_collection(
            name="interview_prep",
            embedding_function=embedding_fn
        )
        
        # Format elements for ChromaDB (stable IDs for idempotent seeding)
        pending_ids = []
        pending_texts = []
        pending_metadatas = []

        for idx, doc in enumerate(documents):
            doc_id = f"doc_{doc['category']}_{idx}"
            pending_ids.append(doc_id)
            pending_texts.append(doc["content"])
            pending_metadatas.append({
                "title": doc["title"],
                "category": doc["category"],
                "source": "baseline_qa.json"
            })

        # Skip documents that are already present
        existing = collection.get(ids=pending_ids)
        existing_ids = set(existing.get("ids") or [])
        new_ids = []
        new_texts = []
        new_metadatas = []

        for doc_id, text, metadata in zip(pending_ids, pending_texts, pending_metadatas):
            if doc_id in existing_ids:
                continue
            new_ids.append(doc_id)
            new_texts.append(text)
            new_metadatas.append(metadata)

        if not new_ids:
            print(
                f"Knowledge base already seeded ({len(pending_ids)} documents present in "
                f"ChromaDB collection 'interview_prep'). Skipping ingestion."
            )
            return

        collection.add(
            documents=new_texts,
            metadatas=new_metadatas,
            ids=new_ids
        )
        print(
            f"Successfully ingested {len(new_ids)} new document(s) into ChromaDB collection "
            f"'interview_prep' ({len(existing_ids)} already present)."
        )
    except Exception as e:
        print(f"Error seeding ChromaDB collection: {e}. Fallback directory is prepared.")

if __name__ == "__main__":
    seed_knowledge_base()
