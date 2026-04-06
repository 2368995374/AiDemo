"""FastAPI 应用入口"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import router
from app.services.inference_service import inference_service
from app.services.remotesam_service import remotesam_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时加载模型
    logger.info("应用启动，开始加载模型…")
    try:
        inference_service.load_model()
    except Exception as e:
        logger.error(f"模型加载失败: {e}")
    if settings.REMOTESAM_AUTO_LOAD:
        try:
            remotesam_service.load_model()
        except Exception as e:
            logger.error(f"RemoteSAM 加载失败: {e}")
    yield
    logger.info("应用关闭")


app = FastAPI(
    title="AI 编码助手 API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS（开发阶段允许前端 dev server 跨域）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )
