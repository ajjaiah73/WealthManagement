import json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.config import settings
#DATA=Path(__file__).resolve().parents[1]/"data"/"knowledge.jsonl"
DATA=Path(__file__).resolve().parents[1]/"data"/"superannuation_knowledge.jsonl"
docs=[json.loads(x) for x in DATA.read_text().splitlines() if x.strip()]
print(f"Loading {len(docs)} knowledge records")
try:
 from sentence_transformers import SentenceTransformer
 from qdrant_client import QdrantClient, models
 m=SentenceTransformer(settings.embedding_model); vectors=m.encode([d['text'] for d in docs]).tolist(); q=QdrantClient(url=settings.qdrant_url)
 q.recreate_collection(settings.qdrant_collection,vectors_config=models.VectorParams(size=len(vectors[0]),distance=models.Distance.COSINE))
 q.upsert(settings.qdrant_collection,[models.PointStruct(id=i+1,vector=v,payload={"text":d["text"],"metadata":d["metadata"],"source_id":d["id"]}) for i,(d,v) in enumerate(zip(docs,vectors))])
 print("Qdrant seeded")
except Exception as e: print("Qdrant seed skipped:",e)
try:
 from neo4j import GraphDatabase
 with GraphDatabase.driver(settings.neo4j_uri,auth=(settings.neo4j_user,settings.neo4j_password)) as drv:
  drv.execute_query("MATCH (n) DETACH DELETE n")
  for d in docs:
   drv.execute_query("MERGE (k:Knowledge {id:$id}) SET k.text=$text, k.name=$name",id=d['id'],text=d['text'],name=d['metadata'].get('title',d['id']))
  drv.execute_query("MATCH (a:Knowledge),(b:Knowledge) WHERE a.id < b.id AND any(x IN split(toLower(a.text),' ') WHERE size(x)>5 AND toLower(b.text) CONTAINS x) MERGE (a)-[:RELATED_TO]->(b)")
 print("Neo4j seeded")
except Exception as e: print("Neo4j seed skipped:",e)
