import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from langgraph.graph import StateGraph, START, END

from config.settings import settings
from services.database import init_postgres, close_postgres
from services.elasticsearch_client import init_elasticsearch, close_elasticsearch
from services.redis_client import init_redis, close_redis
from services.gemini_client import init_llm
from agents.watcher import watcher_agent
from agents.analyzer import analyzer_agent
from agents.pattern import pattern_agent
from agents.alerter import alerter_agent, set_websocket_manager
from agents.blocker import blocker_agent
from models.scam import AgentState
from api.routes import router, set_workflow
from api.websocket import websocket_manager, websocket_endpoint

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("scamshield")


def create_scam_detection_workflow() -> StateGraph:
    workflow = StateGraph(AgentState)
    workflow.add_node("watcher", watcher_agent)
    workflow.add_node("analyzer", analyzer_agent)
    workflow.add_node("pattern", pattern_agent)
    workflow.add_node("alerter", alerter_agent)
    workflow.add_node("blocker", blocker_agent)
    workflow.add_edge(START, "watcher")
    workflow.add_edge("watcher", "analyzer")
    workflow.add_edge("analyzer", "pattern")
    workflow.add_edge("pattern", "alerter")
    workflow.add_edge("alerter", "blocker")
    workflow.add_edge("blocker", END)
    return workflow.compile()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ScamShield API...")
    await init_postgres()
    await init_elasticsearch()
    await init_redis()
    init_llm()
    scam_workflow = create_scam_detection_workflow()
    set_workflow(scam_workflow)
    set_websocket_manager(websocket_manager)
    logger.info("All systems initialized")
    logger.info(f"API Docs: http://localhost:8000/docs")
    yield
    logger.info("Shutting down ScamShield API...")
    await close_postgres()
    await close_elasticsearch()
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    description="Multi-Agent AI Scam Detection System",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.websocket("/ws/{user_id}")
async def ws_endpoint(websocket: WebSocket, user_id: str):
    await websocket_endpoint(websocket, user_id)


try:
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")
except Exception:
    pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_modular:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
