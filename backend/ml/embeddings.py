"""
Log Embeddings + Semantic Search.
Uses sentence-transformers to find historically similar logs by meaning.
"""

import os
import logging
import numpy as np
import joblib

logger = logging.getLogger(__name__)

EMBEDDINGS_CACHE_PATH = "models/log_embeddings.pkl"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


class LogEmbeddingSearch:

    def __init__(self):
        logger.info("[EMBEDDINGS] Initializing LogEmbeddingSearch")

        self.model = None
        self.embeddings = None
        self.log_texts = None
        self.metadata = None

        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            logger.info(f"[EMBEDDINGS] Model '{EMBEDDING_MODEL_NAME}' loaded")
        except ImportError:
            logger.warning(
                "[EMBEDDINGS] sentence-transformers not installed. "
                "Semantic search disabled."
            )
            return
        except Exception as e:
            logger.error(f"[EMBEDDINGS] Failed to load model: {e}")
            return

        # Load cached embeddings if available
        self._load_cache()

    def is_available(self) -> bool:
        return self.model is not None

    def _load_cache(self):
        """Load pre-computed embeddings from cache."""
        if os.path.exists(EMBEDDINGS_CACHE_PATH):
            try:
                cache = joblib.load(EMBEDDINGS_CACHE_PATH)
                self.embeddings = cache["embeddings"]
                self.log_texts = cache["log_texts"]
                self.metadata = cache.get("metadata", [])
                logger.info(
                    f"[EMBEDDINGS] Loaded {len(self.log_texts)} cached embeddings"
                )
            except Exception as e:
                logger.warning(f"[EMBEDDINGS] Failed to load cache: {e}")
                self.embeddings = None
                self.log_texts = None
                self.metadata = None

    def build_index(self, log_texts: list, metadata: list = None):
        """
        Build embeddings index from a list of log texts.
        metadata: list of dicts with classification, severity, etc.
        """
        if not self.is_available():
            logger.warning("[EMBEDDINGS] Model not available, cannot build index")
            return {"status": "failed", "error": "Model not available"}

        logger.info(f"[EMBEDDINGS] Building index for {len(log_texts)} logs")

        try:
            self.log_texts = log_texts
            self.metadata = metadata or []
            self.embeddings = self.model.encode(
                log_texts,
                show_progress_bar=False,
                batch_size=64
            )

            # Save cache
            cache = {
                "embeddings": self.embeddings,
                "log_texts": self.log_texts,
                "metadata": self.metadata
            }
            joblib.dump(cache, EMBEDDINGS_CACHE_PATH)
            logger.info(f"[EMBEDDINGS] Index built and cached ({len(log_texts)} entries)")

            return {"status": "success", "total_indexed": len(log_texts)}

        except Exception as e:
            logger.error(f"[EMBEDDINGS] Failed to build index: {e}")
            return {"status": "failed", "error": str(e)}

    def search(self, query_log: str, top_k: int = 5) -> dict:
        """
        Find the top_k most semantically similar logs to the query.
        """
        if not self.is_available():
            return {"results": [], "error": "Embedding model not available"}

        if self.embeddings is None or len(self.embeddings) == 0:
            return {"results": [], "error": "No embeddings index built. Run /build-index first."}

        try:
            # Encode query
            query_embedding = self.model.encode([query_log])[0]

            # Cosine similarity
            similarities = np.dot(self.embeddings, query_embedding) / (
                np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
            )

            # Top K results
            top_indices = np.argsort(similarities)[::-1][:top_k]

            results = []
            for idx in top_indices:
                result = {
                    "log": self.log_texts[idx],
                    "similarity": round(float(similarities[idx]), 4)
                }
                if self.metadata and idx < len(self.metadata):
                    result.update(self.metadata[idx])
                results.append(result)

            logger.info(
                f"[EMBEDDINGS] Search complete — "
                f"top similarity: {results[0]['similarity'] if results else 'N/A'}"
            )

            return {"results": results, "query": query_log[:100]}

        except Exception as e:
            logger.error(f"[EMBEDDINGS] Search failed: {e}")
            return {"results": [], "error": str(e)}
