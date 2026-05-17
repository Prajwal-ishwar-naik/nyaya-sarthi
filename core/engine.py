import numpy as np
import json
import os
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any
from sklearn.cluster import AgglomerativeClustering
from app.config import settings

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

class MockEmbedding:
    def encode(self, texts):
        return np.zeros((len(texts), 384)) # Standard dimension for all-MiniLM-L6-v2

class EngineRoom:
    def __init__(self):
        if HAS_SENTENCE_TRANSFORMERS:
            try:
                self.embed_model = SentenceTransformer(settings.EMBEDDING_MODEL)
            except Exception as e:
                print(f"Embedding Model Load Failed: {e}. Using Mock.")
                self.embed_model = MockEmbedding()
        else:
            print("Sentence Transformers not found. Using Mock.")
            self.embed_model = MockEmbedding()
        
        # Initialize ChromaDB
        self.chroma_path = settings.CHROMA_DB_PATH
        os.makedirs(self.chroma_path, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=self.chroma_path)
        self.collection = self.client.get_or_create_collection(
            name="judicial_cases",
            metadata={"hnsw:space": "cosine"}
        )

    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        if not texts: return np.array([])
        return self.embed_model.encode(texts)

    def cluster_cases(self, embeddings: np.ndarray, ids: List[int]) -> Dict[int, List[int]]:
        """Group cases using semantic similarity. Uses Agglomerative for better control on small sets."""
        if len(embeddings) < 2: return {0: ids}
        
        # Determine number of clusters dynamically or use a distance threshold
        # n_clusters=None + distance_threshold=0.5 for semantic similarity grouping
        model = AgglomerativeClustering(
            n_clusters=None, 
            distance_threshold=0.6, 
            metric='cosine', 
            linkage='average'
        )
        labels = model.fit_predict(embeddings)
        
        clusters = {}
        for idx, label in enumerate(labels):
            l = int(label)
            if l not in clusters: clusters[l] = []
            clusters[l].append(ids[idx])
        return clusters

    def add_to_vector_store(self, case_id: int, text: str, metadata: Dict[str, Any]):
        embedding = self.get_embeddings([text]).tolist()
        
        # Flatten metadata for ChromaDB (no nested dicts allowed)
        flat_metadata = {}
        for k, v in metadata.items():
            if isinstance(v, (dict, list)):
                flat_metadata[k] = json.dumps(v)
            else:
                flat_metadata[k] = v

        self.collection.add(
            ids=[str(case_id)],
            embeddings=embedding,
            metadatas=[flat_metadata],
            documents=[text]
        )

    def search_similar(self, query: str, limit: int = 5):
        embedding = self.get_embeddings([query]).tolist()
        results = self.collection.query(
            query_embeddings=embedding,
            n_results=limit
        )
        return results

engine_room = EngineRoom()

