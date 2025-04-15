# api/models.py - Pydantic models for API requests and responses
from typing import List, Dict, Optional
from pydantic import BaseModel

class DocumentInput(BaseModel):
    """Model for document input"""
    content: str
    source: str
    metadata: Optional[Dict] = None

class DocumentResponse(BaseModel):
    """Model for document creation response"""
    id: str
    message: str

class Query(BaseModel):
    """Model for search query"""
    question: str
    max_results: int = 5

class SearchResult(BaseModel):
    """Model for search result"""
    id: str
    content: str
    source: str
    score: float

class MessageItem(BaseModel):
    """Model for a chat message"""
    role: str
    content: str

class ChatRequest(BaseModel):
    """Model for chat request"""
    question: str
    chat_history: Optional[List[Dict[str, str]]] = None

class SourceReference(BaseModel):
    """Model for source reference"""
    id: str
    source: str

class ChatResponse(BaseModel):
    """Model for chat response"""
    answer: str
    sources: List[SourceReference]