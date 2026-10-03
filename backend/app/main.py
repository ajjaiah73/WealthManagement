import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import advisory, audit, auth, clients, compliance, documents, fact_find, products, reports
from app.config import settings
from app.container import container
from app.core.logging import configure_logging
from app.core.rate_limit import rate_limiter
from app.core.security import get_current_user
from app.core.telemetry import configure_telemetry

configure_logging()
configure_telemetry()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    warmup = getattr(container.retrieval_service, "warmup", None)
    if warmup is not None:
        # Load embedding/reranker models and build the vector index + knowledge graph
        # before serving, so the first advisory run isn't penalised.
        try:
            await asyncio.to_thread(warmup)
        except Exception:  # noqa: BLE001 - retrieval retries lazily on first use
            logger.exception("Retrieval warmup failed")
    yield
    container.shutdown()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Every business endpoint requires an authenticated user; write endpoints add
# role checks (require_advisor) on top. /api/health and /api/auth/login are public.
_protected = [Depends(get_current_user), Depends(rate_limiter)]
app.include_router(auth.router)
for module in (clients, fact_find, advisory, compliance, audit, products, documents, reports):
    app.include_router(module.router, dependencies=_protected)


@app.get("/api/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "demo_mode": settings.demo_mode,
        "llm_enabled": container.llm_enabled,
        "llm_model": settings.llm_model if container.llm_enabled else None,
        "llm_agents": (
            ["intent_extraction", "advisory_synthesis", "rationale_narrative"] if container.llm_enabled else []
        ),
        "auth_enabled": settings.auth_enabled,
        "orchestrator": "langgraph",
        "max_iterations": settings.max_iterations,
        "persistence": container.persistence_backend(),
        "retrieval": container.retrieval_service.status(),
        "rate_limit_enabled": settings.rate_limit_enabled,
    }
