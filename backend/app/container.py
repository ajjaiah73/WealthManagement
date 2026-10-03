"""Composition root. Builds the persistence layer, retrieval stack, LLM agents
and the LangGraph pipeline from settings; routes depend on `container`, not on
how services are constructed."""
import logging
from concurrent.futures import ThreadPoolExecutor

from app.config import Settings, settings
from app.core.security import DEMO_USERS, hash_password
from app.db.session import create_db_engine, init_db, seed_reference_data
from app.domain.user import Role, StoredUser
from app.graph.orchestrator import AdvisoryPipeline
from app.mock_data.clients import SEED_CLIENTS
from app.mock_data.documents import SEED_DOCUMENTS
from app.mock_data.products import SEED_PRODUCTS
from app.repositories.sql import (
    SqlAuditRepository,
    SqlCaseRepository,
    SqlClientRepository,
    SqlDocumentRepository,
    SqlProductRepository,
    SqlUserRepository,
)
from app.retrieval.hybrid import HybridRetrievalConfig, HybridRetrievalService
from app.services.advisory_service import AdvisorySynthesisService
from app.services.compliance_service import ComplianceService
from app.services.llm_service import ClaudeClient, LLMIntentExtractor, LLMNarrator, LLMSynthesisAdvisor
from app.services.report_service import ReportService
from app.services.retrieval_service import MockRetrievalService, RetrievalService

logger = logging.getLogger(__name__)


class Container:
    def __init__(self, cfg: Settings = settings) -> None:
        self.settings = cfg

        # -- persistence -----------------------------------------------------------
        self.engine = create_db_engine(cfg.database_url)
        self.session_factory = init_db(self.engine)
        seed_reference_data(self.session_factory, list(SEED_CLIENTS), list(SEED_PRODUCTS), list(SEED_DOCUMENTS))
        self.client_repository = SqlClientRepository(self.session_factory)
        self.product_repository = SqlProductRepository(self.session_factory)
        self.document_repository = SqlDocumentRepository(self.session_factory)
        self.audit_repository = SqlAuditRepository(self.session_factory)
        self.case_repository = SqlCaseRepository(self.session_factory)
        self.user_repository = SqlUserRepository(self.session_factory)
        self._seed_users()

        # -- LLM agents (server-side key only) -----------------------------------
        claude = (
            ClaudeClient(api_key=cfg.anthropic_api_key, model=cfg.llm_model)
            if cfg.use_real_llm and cfg.anthropic_api_key
            else None
        )
        self.intent_extractor = LLMIntentExtractor(claude) if claude else None
        self.narrator = LLMNarrator(api_key="", model=cfg.llm_model, client=claude) if claude else None
        self.advisory_service = AdvisorySynthesisService(
            llm=LLMSynthesisAdvisor(claude) if claude else None, demo_mode=cfg.demo_mode
        )

        # -- retrieval -------------------------------------------------------------
        self.retrieval_service: RetrievalService
        if cfg.retrieval_backend == "hybrid":
            self.retrieval_service = HybridRetrievalService(
                self.document_repository,
                self.product_repository,
                HybridRetrievalConfig(
                    models_dir=cfg.models_dir,
                    embedding_model=cfg.embedding_model,
                    reranker_model=cfg.reranker_model,
                    qdrant_url=cfg.qdrant_url,
                    qdrant_path=cfg.qdrant_path,
                    qdrant_collection=cfg.qdrant_collection,
                    neo4j_uri=cfg.neo4j_uri,
                    neo4j_user=cfg.neo4j_user,
                    neo4j_password=cfg.neo4j_password,
                ),
            )
        else:
            self.retrieval_service = MockRetrievalService(self.document_repository)

        self.compliance_service = ComplianceService()
        self.report_service = ReportService()
        self.pipeline = AdvisoryPipeline(
            retrieval_service=self.retrieval_service,
            synthesis_service=self.advisory_service,
            compliance_service=self.compliance_service,
            audit_repository=self.audit_repository,
            case_repository=self.case_repository,
            intent_extractor=self.intent_extractor,
            narrator=self.narrator,
            max_iterations=cfg.max_iterations,
        )
        # Background advisory runs (POST /api/advisory/start).
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="advisory")

    @property
    def llm_enabled(self) -> bool:
        return self.narrator is not None

    def _seed_users(self) -> None:
        cfg = self.settings
        if cfg.bootstrap_admin_username and cfg.bootstrap_admin_password:
            if self.user_repository.get(cfg.bootstrap_admin_username) is None:
                self.user_repository.add(StoredUser(
                    username=cfg.bootstrap_admin_username, display_name="Administrator", role=Role.ADMIN,
                    password_hash=hash_password(cfg.bootstrap_admin_password),
                ))
        if cfg.demo_mode:
            for username, display_name, role, password in DEMO_USERS:
                if self.user_repository.get(username) is None:
                    self.user_repository.add(StoredUser(
                        username=username, display_name=display_name, role=role,
                        password_hash=hash_password(password),
                    ))

    def persistence_backend(self) -> str:
        return self.engine.dialect.name

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)
        close = getattr(self.retrieval_service, "close", None)
        if close:
            close()
        self.engine.dispose()


container = Container()
