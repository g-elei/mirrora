import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

class Settings:
    PROJECT_NAME: str = "Mirrora AI Companion"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./mirrora_memory.db")
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")  # no default: never commit a credential
    QWEN_API_KEY: str = os.getenv("QWEN_API_KEY", "")
    

settings = Settings()