import os
import json
from app.rag.vectorstore import VectorStoreManager
from app.rag.embeddings import get_embedding_function
from app.core.config import settings

class RAGRetriever:
    @staticmethod
    def retrieve(query: str, category: str = None, limit: int = 2) -> list:
        results = []
        try:
            # Try loading from ChromaDB collection
            embedding_fn = get_embedding_function()
            client = VectorStoreManager.get_client()
            
            # Retrieve collection
            collection = client.get_collection(
                name="interview_prep",
                embedding_function=embedding_fn
            )
            
            # Build filters if category provided
            where_filter = {}
            if category:
                where_filter["category"] = category
                
            query_results = collection.query(
                query_texts=[query],
                n_results=limit,
                where=where_filter if where_filter else None
            )
            
            if query_results and 'documents' in query_results and len(query_results['documents'][0]) > 0:
                for idx, doc in enumerate(query_results['documents'][0]):
                    metadata = query_results['metadatas'][0][idx] if 'metadatas' in query_results else {}
                    results.append({
                        "content": doc,
                        "metadata": metadata,
                        "source": metadata.get("source", "ChromaDB")
                    })
        except Exception as e:
            print(f"ChromaDB retrieval warning: {e}. Falling back to directory search.")

        # Fallback keyword matching over local knowledge_base directory
        if not results:
            results = RAGRetriever._fallback_search(query, category, limit)
            
        return results

    @staticmethod
    def _fallback_search(query: str, category: str = None, limit: int = 2) -> list:
        matched = []
        kb_path = settings.KNOWLEDGE_BASE_DIR
        
        if not os.path.exists(kb_path):
            return matched
            
        query_words = set(query.lower().split())
        
        # Scan through knowledge base files
        for filename in os.listdir(kb_path):
            if not filename.endswith(".json") and not filename.endswith(".txt"):
                continue
                
            file_path = os.path.join(kb_path, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    if filename.endswith(".json"):
                        data = json.load(f)
                        # Expecting list of items {"title": ..., "content": ..., "category": ...}
                        items = data if isinstance(data, list) else [data]
                        for item in items:
                            if category and item.get("category", "").lower() != category.lower():
                                continue
                            text = (item.get("title", "") + " " + item.get("content", "")).lower()
                            score = sum(1 for w in query_words if w in text)
                            if score > 0:
                                matched.append((score, {
                                    "content": item.get("content"),
                                    "metadata": {"title": item.get("title"), "category": item.get("category"), "source": filename}
                                }))
                    else:
                        content = f.read()
                        text_lower = content.lower()
                        score = sum(1 for w in query_words if w in text_lower)
                        if score > 0:
                            matched.append((score, {
                                "content": content[:1000], # return snippet
                                "metadata": {"title": filename.replace(".txt", ""), "category": category, "source": filename}
                            }))
            except Exception as ex:
                print(f"Error reading RAG fallback file {filename}: {ex}")
                
        # Sort by match score and retrieve top items
        matched.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in matched[:limit]]
