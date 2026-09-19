# Financial Advisor Agentic RAG

Runnable M.Tech reference implementation matching the four-layer architecture:

- Streamlit advisory dashboard
- FastAPI serving layer
- LangGraph stateful orchestration and reflection loop
- Multi-agent coordinator, synthesis and compliance agents
- Hybrid retrieval: dense Qdrant, sparse BM25, Neo4j graph, RRF, optional cross-encoder reranking
- Pydantic validation and Z3 hard-constraint verification
- MySQL audit/session/compliance persistence

> Academic prototype only. It does not provide regulated financial advice. Replace sample rules and product data with jurisdiction-approved content and obtain qualified compliance review before real use.

## Quick start

1. Copy `.env.example` to `.env`.
2. Add an OpenAI-compatible API key, or keep `MOCK_LLM=true` for an offline deterministic demo.
3. Start infrastructure: `docker compose up -d mysql qdrant neo4j`
4. Create environment: `python -m venv .venv`
5. Activate it and run `pip install -r requirements.txt`.
6. Seed knowledge: `python scripts/seed_data.py`
7. Start API: `uvicorn app.main:app --reload --port 8000`
8. In another terminal: `streamlit run ui/streamlit_app.py`
9. Open Streamlit at `http://localhost:8501`. API docs are at `http://localhost:8000/docs`.

## Tests

```bash
pytest -q
```

## API example

```bash
curl -X POST http://localhost:8000/advice \
  -H 'Content-Type: application/json' \
  -d '{"client":{"client_id":"demo-1","age":35,"annual_income":1800000,"liquid_assets":500000,"risk_tolerance":"moderate","investment_horizon_years":10,"max_fee_pct":1.5},"goal":"Build a diversified long-term portfolio","question":"What allocation should I consider?"}'
```

## Architecture mapping

- `ui/`: Layer 1
- `app/workflow.py`, `app/agents/`, `app/main.py`: Layer 2
- `app/retrieval/`, `app/compliance/`: Layer 3
- MySQL, Qdrant, Neo4j adapters in `app/storage/`: Layer 4

## Notes

The code supports graceful fallback when Qdrant, Neo4j, or MySQL are unavailable, which helps laptop demos. For strict architecture tests, keep all three services running. Generated advice includes citations, compliance findings, reflection count and audit ID.
