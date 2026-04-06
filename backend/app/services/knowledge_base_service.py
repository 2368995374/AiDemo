"""Qdrant 知识库服务：负责检索增强上下文。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.core.config import settings


@dataclass
class RetrievedChunk:
    source: str
    chunk_id: str
    score: float
    content: str


@dataclass
class RetrieveResult:
    used: bool
    hits: int
    context: str
    sources: List[dict]
    error: str = ""


class KnowledgeBaseService:
    """封装 Qdrant + Embedding 的检索逻辑。"""

    def __init__(self):
        self._vectorstore = None
        self._init_error = ""

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> RetrieveResult:
        if not settings.RAG_ENABLED:
            return RetrieveResult(used=False, hits=0, context="", sources=[])

        cleaned_query = (query or "").strip()
        if not cleaned_query:
            return RetrieveResult(used=False, hits=0, context="", sources=[])

        vectorstore = self._get_vectorstore()
        if vectorstore is None:
            return RetrieveResult(
                used=False,
                hits=0,
                context="",
                sources=[],
                error=self._init_error or "知识库未初始化",
            )

        k = max(1, top_k or settings.RAG_TOP_K)
        threshold = settings.RAG_SCORE_THRESHOLD if score_threshold is None else score_threshold

        try:
            rows = vectorstore.similarity_search_with_score(cleaned_query, k=k)
        except Exception as exc:  # noqa: BLE001
            return RetrieveResult(
                used=False,
                hits=0,
                context="",
                sources=[],
                error=f"检索失败: {exc}",
            )

        chunks: List[RetrievedChunk] = []
        for doc, score in rows:
            score_value = float(score)
            # Qdrant 的分数越高越相关。阈值小于等于 0 时视为不过滤。
            if threshold > 0 and score_value < threshold:
                continue
            source = str(doc.metadata.get("source") or "unknown")
            chunk_id = str(doc.metadata.get("chunk_id") or "-")
            chunks.append(
                RetrievedChunk(
                    source=source,
                    chunk_id=chunk_id,
                    score=score_value,
                    content=doc.page_content,
                )
            )

        if not chunks:
            return RetrieveResult(used=True, hits=0, context="", sources=[])

        context_parts: List[str] = []
        sources: List[dict] = []
        for idx, chunk in enumerate(chunks, start=1):
            context_parts.append(
                f"[片段{idx}] source={chunk.source} chunk={chunk.chunk_id} score={chunk.score:.4f}\n{chunk.content}"
            )
            sources.append(
                {
                    "source": chunk.source,
                    "chunk_id": chunk.chunk_id,
                    "score": round(chunk.score, 4),
                    "preview": chunk.content[:120],
                }
            )

        return RetrieveResult(
            used=True,
            hits=len(chunks),
            context="\n\n".join(context_parts),
            sources=sources,
        )

    def _get_vectorstore(self):
        if self._vectorstore is not None:
            return self._vectorstore

        try:
            from qdrant_client import QdrantClient
            from langchain_huggingface import HuggingFaceEmbeddings
            from langchain_qdrant import QdrantVectorStore

            client = self._create_qdrant_client(QdrantClient)
            embeddings = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL_NAME,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
            self._vectorstore = QdrantVectorStore(
                client=client,
                collection_name=settings.QDRANT_COLLECTION,
                embedding=embeddings,
            )
            self._init_error = ""
            return self._vectorstore
        except Exception as exc:  # noqa: BLE001
            self._init_error = f"初始化知识库失败: {exc}"
            return None

    @staticmethod
    def _create_qdrant_client(qdrant_client_cls):
        if settings.QDRANT_LOCAL_PATH:
            return qdrant_client_cls(path=settings.QDRANT_LOCAL_PATH)
        if settings.QDRANT_API_KEY:
            return qdrant_client_cls(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
        return qdrant_client_cls(url=settings.QDRANT_URL)


knowledge_base_service = KnowledgeBaseService()
