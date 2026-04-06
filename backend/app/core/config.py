"""应用配置，从 .env 读取"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env（后端根目录: backend/.env）
# config.py 在 backend/app/core/ 下，需要往上三级才能到 backend/
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)


class Settings:
    # 服务
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

    # 模型
    MODEL_PATH: str = os.getenv("MODEL_PATH", "")
    MODEL_DTYPE: str = os.getenv("MODEL_DTYPE", "float16")
    MODEL_DEVICE_MAP: str = os.getenv("MODEL_DEVICE_MAP", "auto")
    MODEL_OFFLINE: bool = os.getenv("MODEL_OFFLINE", "true").lower() in ("true", "1")
    DEFAULT_SYSTEM_PROMPT: str = os.getenv(
        "DEFAULT_SYSTEM_PROMPT",
        "You are Qwen, a helpful coding assistant running fully offline.",
    )
    DEFAULT_MAX_NEW_TOKENS: int = int(os.getenv("DEFAULT_MAX_NEW_TOKENS", "256"))
    DEFAULT_TEMPERATURE: float = float(os.getenv("DEFAULT_TEMPERATURE", "0.2"))
    DEFAULT_TOP_P: float = float(os.getenv("DEFAULT_TOP_P", "0.9"))

    # LangChain 编排
    LANGCHAIN_ENABLED: bool = os.getenv("LANGCHAIN_ENABLED", "true").lower() in ("true", "1", "yes")
    LANGCHAIN_ENABLE_TOOLS: bool = os.getenv("LANGCHAIN_ENABLE_TOOLS", "true").lower() in ("true", "1", "yes")
    LANGCHAIN_MAX_HISTORY_ROUNDS: int = int(os.getenv("LANGCHAIN_MAX_HISTORY_ROUNDS", "10"))
    LANGCHAIN_DEFAULT_TIMEZONE: str = os.getenv("LANGCHAIN_DEFAULT_TIMEZONE", "Asia/Shanghai")
    RAG_ENABLED: bool = os.getenv("RAG_ENABLED", "true").lower() in ("true", "1", "yes")
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "4"))
    RAG_SCORE_THRESHOLD: float = float(os.getenv("RAG_SCORE_THRESHOLD", "0.2"))
    EMBEDDING_MODEL_NAME: str = os.getenv(
        "EMBEDDING_MODEL_NAME",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )

    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "project_kb")
    QDRANT_LOCAL_PATH: str = os.getenv("QDRANT_LOCAL_PATH", "")

    # RemoteSAM
    REMOTESAM_REPO_PATH: str = os.getenv("REMOTESAM_REPO_PATH", "")
    REMOTESAM_CHECKPOINT: str = os.getenv("REMOTESAM_CHECKPOINT", "")
    REMOTESAM_DEVICE: str = os.getenv("REMOTESAM_DEVICE", "cuda:0")
    REMOTESAM_USE_EPOC: bool = os.getenv("REMOTESAM_USE_EPOC", "false").lower() in ("true", "1", "yes")
    REMOTESAM_AUTO_LOAD: bool = os.getenv("REMOTESAM_AUTO_LOAD", "false").lower() in ("true", "1", "yes")

    # MySQL
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "AiDemo")

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            "?charset=utf8mb4"
        )


settings = Settings()
