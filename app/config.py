from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    app_env: str = "dev"
    mock_llm: bool = True
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "financial_knowledge"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "financialpass"
    mysql_url: str = "mysql+pymysql://advisor:advisorpass@localhost:3306/advisor"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    top_k: int = 6
    max_reflections: int = 1
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
settings=Settings()
