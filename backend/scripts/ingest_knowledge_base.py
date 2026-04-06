"""将 Markdown 文档切分并写入 Qdrant，作为 RAG 知识库。"""
# pyright: reportMissingImports=false

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from app.core.config import settings


def _create_client() -> Any:
    qdrant_client_cls, _ = _import_qdrant_modules()
    if settings.QDRANT_LOCAL_PATH:
        return qdrant_client_cls(path=settings.QDRANT_LOCAL_PATH)
    if settings.QDRANT_API_KEY:
        return qdrant_client_cls(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
    return qdrant_client_cls(url=settings.QDRANT_URL)


def _ensure_collection(client: Any, embeddings: Any, recreate: bool) -> None:
    _, qdrant_models = _import_qdrant_modules()
    collection = settings.QDRANT_COLLECTION
    if recreate:
        try:
            client.delete_collection(collection_name=collection)
        except Exception:
            pass

    exists = True
    try:
        client.get_collection(collection_name=collection)
    except Exception:
        exists = False

    if exists:
        return

    vector_size = len(embeddings.embed_query("knowledge base bootstrap"))
    client.create_collection(
        collection_name=collection,
        vectors_config=qdrant_models.VectorParams(
            size=vector_size,
            distance=qdrant_models.Distance.COSINE,
        ),
    )


def ingest_markdown(markdown_path: Path, recreate: bool, chunk_size: int, chunk_overlap: int) -> None:
    TextLoader, RecursiveCharacterTextSplitter = _import_loader_modules()
    HuggingFaceEmbeddings, QdrantVectorStore = _import_langchain_modules()

    if not markdown_path.exists():
        raise FileNotFoundError(f"文件不存在: {markdown_path}")

    loader = TextLoader(str(markdown_path), encoding="utf-8")
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
    )
    split_docs = splitter.split_documents(docs)

    source_name = markdown_path.as_posix()
    for idx, doc in enumerate(split_docs):
        doc.metadata["source"] = source_name
        doc.metadata["chunk_id"] = str(idx)

    embeddings = HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    client = _create_client()
    _ensure_collection(client, embeddings, recreate=recreate)

    vectorstore = QdrantVectorStore(
        client=client,
        collection_name=settings.QDRANT_COLLECTION,
        embedding=embeddings,
    )

    if recreate:
        # 集合已重建，这里只做新增。
        vectorstore.add_documents(split_docs)
    else:
        vectorstore.add_documents(split_docs)

    print("=== 入库完成 ===")
    print(f"文档: {source_name}")
    print(f"切片数: {len(split_docs)}")
    print(f"集合: {settings.QDRANT_COLLECTION}")
    if settings.QDRANT_LOCAL_PATH:
        print(f"Qdrant(local): {settings.QDRANT_LOCAL_PATH}")
    else:
        print(f"Qdrant(url): {settings.QDRANT_URL}")


def _import_qdrant_modules():
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.http import models as qdrant_models
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "缺少 qdrant 依赖，请先执行: pip install -r backend/requirements.txt"
        ) from exc
    return QdrantClient, qdrant_models


def _import_langchain_modules():
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_qdrant import QdrantVectorStore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "缺少 LangChain 向量库依赖，请先执行: pip install -r backend/requirements.txt"
        ) from exc
    return HuggingFaceEmbeddings, QdrantVectorStore


def _import_loader_modules():
    try:
        from langchain_community.document_loaders import TextLoader
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "缺少文档加载/切分依赖，请先执行: pip install -r backend/requirements.txt"
        ) from exc
    return TextLoader, RecursiveCharacterTextSplitter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将 Markdown 文档写入 Qdrant 知识库")
    default_doc = Path(__file__).resolve().parent.parent / "docs" / "LANGCHAIN_INTEGRATION_GUIDE.md"
    parser.add_argument("--file", type=Path, default=default_doc, help="要入库的 Markdown 文件路径")
    parser.add_argument("--recreate", action="store_true", help="重建集合后再入库")
    parser.add_argument("--chunk-size", type=int, default=600)
    parser.add_argument("--chunk-overlap", type=int, default=120)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ingest_markdown(
        markdown_path=args.file,
        recreate=args.recreate,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )


if __name__ == "__main__":
    main()
