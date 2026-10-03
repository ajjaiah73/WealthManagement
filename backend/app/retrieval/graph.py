"""Regulatory knowledge graph retrieval.

Graph schema (identical in both backends):

    (:Topic)-[:GOVERNED_BY]->(:Document)          e.g. concessional_cap -> DOC-014
    (:ProductType)-[:SUBJECT_TO]->(:Topic)        e.g. TTR -> preservation
    (:Product)-[:IS_TYPE]->(:ProductType)
    (:Product)-[:DESCRIBED_BY]->(:Document)       product PDS

A query starts from the topics implied by the client's facts and the request,
plus the product types under consideration, and walks to the documents that
govern or describe them. Documents reached by more (and more direct) paths
score higher. Neo4j is used when NEO4J_URI is set; otherwise an in-process
networkx graph with the same nodes and edges.
"""
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Protocol

import networkx as nx

from app.domain.client import ClientProfile, RiskTolerance
from app.domain.document import DocumentRecord
from app.domain.product import Product, ProductType

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Topic:
    key: str
    label: str
    document_ids: tuple[str, ...]
    keywords: tuple[str, ...]


TOPICS: tuple[Topic, ...] = (
    Topic("concessional_cap", "Concessional contributions cap", ("DOC-014", "DOC-020"),
          ("concessional", "salary sacrifice", "contribution", "contribute", "cap")),
    Topic("non_concessional_cap", "Non-concessional contributions cap", ("DOC-015",),
          ("non-concessional", "after-tax", "bring-forward", "contribution")),
    Topic("preservation", "Preservation age and transition to retirement", ("DOC-016",),
          ("preservation", "ttr", "transition to retirement", "retire", "pension", "access")),
    Topic("allocation_over_55", "Asset allocation for members over 55", ("DOC-017",),
          ("allocation", "defensive", "growth", "risk", "pre-retire")),
    Topic("fees", "Fee benchmarks", ("DOC-018",), ("fee", "fees", "cost", "cheap", "expensive")),
    Topic("disclosure", "Advice disclosure obligations", ("DOC-019",), ("disclosure", "pds", "general advice")),
    Topic("division_293", "Division 293 tax", ("DOC-020",), ("division 293", "high income", "div 293")),
)

PRODUCT_TYPE_TOPICS: dict[ProductType, tuple[str, ...]] = {
    ProductType.MY_SUPER: ("fees", "disclosure"),
    ProductType.CHOICE: ("fees", "disclosure", "allocation_over_55"),
    ProductType.SMSF: ("fees", "disclosure"),
    ProductType.TTR: ("preservation", "fees", "disclosure"),
    ProductType.DEFINED_BENEFIT: ("disclosure",),
}

_TOPIC_BY_KEY = {t.key: t for t in TOPICS}


@dataclass(frozen=True)
class GraphHit:
    document_id: str
    score: float
    paths: tuple[str, ...]


def derive_topics(profile: ClientProfile, query: str) -> dict[str, str]:
    """Topic key -> human-readable reason, from structured facts and request keywords."""
    reasons: dict[str, str] = {}
    if profile.concessional_contributions_ytd > 0:
        ytd = profile.concessional_contributions_ytd
        reasons["concessional_cap"] = f"concessional contributions YTD ${ytd:,.0f}"
    if profile.non_concessional_contributions_ytd > 0:
        reasons["non_concessional_cap"] = (
            f"non-concessional contributions YTD ${profile.non_concessional_contributions_ytd:,.0f}"
        )
    if profile.ttr_intent:
        reasons["preservation"] = "client intends a transition-to-retirement strategy"
    if profile.age is not None and profile.age > 55:
        reasons["allocation_over_55"] = f"client is {profile.age} (over 55)"
        reasons.setdefault("preservation", f"client is {profile.age}, approaching preservation age")
    if profile.salary is not None and profile.salary >= 250_000:
        reasons["division_293"] = f"salary ${profile.salary:,.0f} at or above the Division 293 threshold"
    lowered = query.lower()
    for topic in TOPICS:
        if topic.key not in reasons and any(k in lowered for k in topic.keywords):
            reasons[topic.key] = "mentioned in the request"
    reasons.setdefault("fees", "fee benchmarking applies to every recommendation")
    reasons.setdefault("disclosure", "disclosure obligations apply to every recommendation")
    return reasons


def candidate_product_types(profile: ClientProfile, query: str) -> list[ProductType]:
    types: list[ProductType] = []
    lowered = query.lower()
    if profile.ttr_intent or "ttr" in lowered or "transition to retirement" in lowered:
        types.append(ProductType.TTR)
    if "smsf" in lowered or "self-managed" in lowered or "self managed" in lowered:
        types.append(ProductType.SMSF)
    if profile.risk_tolerance in (RiskTolerance.GROWTH, RiskTolerance.HIGH_GROWTH):
        types.append(ProductType.CHOICE)
    types.append(ProductType.MY_SUPER)
    return list(dict.fromkeys(types))


class GraphStore(Protocol):
    backend: str

    def build(self, products: list[Product], documents: list[DocumentRecord]) -> None: ...

    def related_documents(self, topic_keys: list[str], product_types: list[ProductType]) -> list[GraphHit]: ...

    def close(self) -> None: ...


# Direct topic governance outranks reaching a PDS via product type.
_TOPIC_WEIGHT = 1.0
_TYPE_TOPIC_WEIGHT = 0.5
_TYPE_PRODUCT_WEIGHT = 0.35


class NetworkxGraphStore:
    backend = "networkx"

    def __init__(self) -> None:
        self._g: nx.DiGraph = nx.DiGraph()

    def build(self, products: list[Product], documents: list[DocumentRecord]) -> None:
        g = nx.DiGraph()
        known_docs = {d.document_id for d in documents}
        for d in documents:
            g.add_node(("Document", d.document_id), title=d.title)
        for t in TOPICS:
            g.add_node(("Topic", t.key), label=t.label)
            for doc_id in t.document_ids:
                if doc_id in known_docs:
                    g.add_edge(("Topic", t.key), ("Document", doc_id), rel="GOVERNED_BY")
        for ptype, topic_keys in PRODUCT_TYPE_TOPICS.items():
            g.add_node(("ProductType", ptype.value))
            for key in topic_keys:
                g.add_edge(("ProductType", ptype.value), ("Topic", key), rel="SUBJECT_TO")
        for p in products:
            g.add_node(("Product", p.product_id), name=p.product_name)
            g.add_edge(("Product", p.product_id), ("ProductType", p.product_type.value), rel="IS_TYPE")
            if p.source_document_id in known_docs:
                g.add_edge(("Product", p.product_id), ("Document", p.source_document_id), rel="DESCRIBED_BY")
        self._g = g

    def related_documents(self, topic_keys: list[str], product_types: list[ProductType]) -> list[GraphHit]:
        g = self._g
        scores: dict[str, float] = defaultdict(float)
        paths: dict[str, list[str]] = defaultdict(list)

        for key in topic_keys:
            for _, doc in g.out_edges(("Topic", key)):
                scores[doc[1]] += _TOPIC_WEIGHT
                paths[doc[1]].append(f"Topic:{key} -GOVERNED_BY-> {doc[1]}")
        for ptype in product_types:
            type_node = ("ProductType", ptype.value)
            if type_node not in g:
                continue
            for _, topic in g.out_edges(type_node):
                for _, doc in g.out_edges(topic):
                    scores[doc[1]] += _TYPE_TOPIC_WEIGHT
                    paths[doc[1]].append(f"ProductType:{ptype.value} -SUBJECT_TO-> Topic:{topic[1]} -> {doc[1]}")
            for product, _ in g.in_edges(type_node):
                for _, doc in g.out_edges(product):
                    if doc[0] == "Document":
                        scores[doc[1]] += _TYPE_PRODUCT_WEIGHT
                        paths[doc[1]].append(
                            f"ProductType:{ptype.value} <-IS_TYPE- Product:{product[1]} -DESCRIBED_BY-> {doc[1]}"
                        )
        return _rank(scores, paths)

    def close(self) -> None:
        pass


class Neo4jGraphStore:
    backend = "neo4j"

    def __init__(self, uri: str, user: str, password: str | None) -> None:
        from neo4j import GraphDatabase

        self._driver = GraphDatabase.driver(uri, auth=(user, password or ""))
        self._driver.verify_connectivity()

    def build(self, products: list[Product], documents: list[DocumentRecord]) -> None:
        known_docs = {d.document_id for d in documents}
        with self._driver.session() as session:
            session.run("CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.document_id IS UNIQUE")
            session.run("CREATE CONSTRAINT topic_key IF NOT EXISTS FOR (t:Topic) REQUIRE t.key IS UNIQUE")
            session.run(
                "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.product_id IS UNIQUE"
            )
            session.run("CREATE CONSTRAINT ptype IF NOT EXISTS FOR (t:ProductType) REQUIRE t.name IS UNIQUE")
            session.run(
                "UNWIND $docs AS d MERGE (n:Document {document_id: d.id}) SET n.title = d.title",
                docs=[{"id": d.document_id, "title": d.title} for d in documents],
            )
            session.run(
                "UNWIND $topics AS t MERGE (n:Topic {key: t.key}) SET n.label = t.label "
                "WITH n, t UNWIND t.docs AS doc_id MATCH (d:Document {document_id: doc_id}) "
                "MERGE (n)-[:GOVERNED_BY]->(d)",
                topics=[
                    {"key": t.key, "label": t.label, "docs": [d for d in t.document_ids if d in known_docs]}
                    for t in TOPICS
                ],
            )
            session.run(
                "UNWIND $types AS pt MERGE (n:ProductType {name: pt.name}) "
                "WITH n, pt UNWIND pt.topics AS key MATCH (t:Topic {key: key}) MERGE (n)-[:SUBJECT_TO]->(t)",
                types=[{"name": k.value, "topics": list(v)} for k, v in PRODUCT_TYPE_TOPICS.items()],
            )
            session.run(
                "UNWIND $products AS p MERGE (n:Product {product_id: p.id}) SET n.name = p.name "
                "WITH n, p MATCH (pt:ProductType {name: p.type}) MERGE (n)-[:IS_TYPE]->(pt) "
                "WITH n, p MATCH (d:Document {document_id: p.doc}) MERGE (n)-[:DESCRIBED_BY]->(d)",
                products=[
                    {"id": p.product_id, "name": p.product_name, "type": p.product_type.value,
                     "doc": p.source_document_id or ""}
                    for p in products
                ],
            )

    def related_documents(self, topic_keys: list[str], product_types: list[ProductType]) -> list[GraphHit]:
        type_names = [t.value for t in product_types]
        query = """
            CALL {
              MATCH (t:Topic)-[:GOVERNED_BY]->(d:Document) WHERE t.key IN $topics
              RETURN d.document_id AS doc, $w_topic AS w,
                     'Topic:' + t.key + ' -GOVERNED_BY-> ' + d.document_id AS path
              UNION ALL
              MATCH (pt:ProductType)-[:SUBJECT_TO]->(t:Topic)-[:GOVERNED_BY]->(d:Document) WHERE pt.name IN $types
              RETURN d.document_id AS doc, $w_type_topic AS w,
                     'ProductType:' + pt.name + ' -SUBJECT_TO-> Topic:' + t.key + ' -> ' + d.document_id AS path
              UNION ALL
              MATCH (pt:ProductType)<-[:IS_TYPE]-(p:Product)-[:DESCRIBED_BY]->(d:Document) WHERE pt.name IN $types
              RETURN d.document_id AS doc, $w_type_product AS w,
                     'ProductType:' + pt.name + ' <-IS_TYPE- Product:' + p.product_id
                       + ' -DESCRIBED_BY-> ' + d.document_id AS path
            }
            RETURN doc, sum(w) AS score, collect(path) AS paths
        """
        scores: dict[str, float] = {}
        paths: dict[str, list[str]] = {}
        with self._driver.session() as session:
            result = session.run(
                query, topics=topic_keys, types=type_names, w_topic=_TOPIC_WEIGHT,
                w_type_topic=_TYPE_TOPIC_WEIGHT, w_type_product=_TYPE_PRODUCT_WEIGHT,
            )
            for record in result:
                scores[record["doc"]] = float(record["score"])
                paths[record["doc"]] = list(record["paths"])
        return _rank(scores, paths)

    def close(self) -> None:
        self._driver.close()


def _rank(scores: dict[str, float], paths: dict[str, list[str]]) -> list[GraphHit]:
    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [GraphHit(doc_id, round(score, 4), tuple(paths.get(doc_id, ()))) for doc_id, score in ordered]


def make_graph_store(uri: str | None, user: str, password: str | None) -> GraphStore:
    if uri:
        try:
            return Neo4jGraphStore(uri, user, password)
        except Exception as exc:  # noqa: BLE001 - fall back to the in-process graph if Neo4j is unreachable
            logger.warning("Neo4j unavailable at %s (%s); using in-process networkx graph", uri, exc)
    return NetworkxGraphStore()


def topic_label(key: str) -> str:
    topic = _TOPIC_BY_KEY.get(key)
    return topic.label if topic else key
