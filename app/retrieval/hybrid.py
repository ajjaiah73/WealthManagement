from __future__ import annotations
import json, math
from pathlib import Path
from rank_bm25 import BM25Okapi
from app.config import settings

DATA=Path(__file__).resolve().parents[2]/"data"/"knowledge.jsonl"

def _docs():
    if not DATA.exists(): return []
    return [json.loads(x) for x in DATA.read_text().splitlines() if x.strip()]

def rrf(result_lists, k=60):
    scores={}; items={}
    for results in result_lists:
        for rank,item in enumerate(results,1):
            key=item["id"]; items[key]=item; scores[key]=scores.get(key,0)+1/(k+rank)
    return [{**items[i],"rrf_score":s} for i,s in sorted(scores.items(), key=lambda x:x[1], reverse=True)]

def sparse_search(query, limit=8):
    docs=_docs()
    if not docs: return []
    corpus=[d["text"].lower().split() for d in docs]
    scores=BM25Okapi(corpus).get_scores(query.lower().split())
    order=sorted(range(len(docs)), key=lambda i:scores[i], reverse=True)[:limit]
    return [{**docs[i],"score":float(scores[i]),"channel":"sparse"} for i in order]

def dense_search(query, limit=8):
    try:
        from sentence_transformers import SentenceTransformer
        from qdrant_client import QdrantClient
        model=SentenceTransformer(settings.embedding_model)
        vec=model.encode(query).tolist()
        client=QdrantClient(url=settings.qdrant_url)
        hits=client.query_points(collection_name=settings.qdrant_collection, query=vec, limit=limit).points
        return [{"id":str(h.id),"text":h.payload.get("text",""),"metadata":h.payload.get("metadata",{}),"score":float(h.score),"channel":"dense"} for h in hits]
    except Exception:
        return []

def graph_search(query, limit=8):
    tokens=[t.lower() for t in query.split() if len(t)>3][:10]
    try:
        from neo4j import GraphDatabase
        with GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user,settings.neo4j_password)) as drv:
            rows=drv.execute_query("MATCH (n:Knowledge) WHERE any(t IN $tokens WHERE toLower(n.text) CONTAINS t) OPTIONAL MATCH (n)-[r]-(m) RETURN n.id AS id,n.text AS text,collect({relation:type(r),target:m.name})[0..3] AS links LIMIT $limit", tokens=tokens, limit=limit).records
            return [{"id":r["id"],"text":r["text"],"metadata":{"links":r["links"]},"score":1.0,"channel":"graph"} for r in rows]
    except Exception:
        return []

def hybrid_search(query, limit=None):
    limit=limit or settings.top_k
    fused=rrf([dense_search(query),sparse_search(query),graph_search(query)])
    return fused[:limit]
