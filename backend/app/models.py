from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ChatRequest(BaseModel):
    user_id: str = "beihang_student"
    message: str
    mode: str = "confidant"

class GraphResponse(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]

class RecommendationItem(BaseModel):
    title: str
    media_type: str
    creator: str
    pitch: str
    score: float
    graph_reasoning: List[str]