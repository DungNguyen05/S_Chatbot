# api/dependencies.py - Dependency functions for FastAPI routes
from fastapi import HTTPException

import config

def get_document_manager():
    """Get the document manager instance from the app state"""
    from app import document_manager
    return document_manager

def get_chatbot():
    """Get the chatbot instance from the app state"""
    from app import chatbot
    return chatbot

def get_vector_store():
    """Get the vector store instance from the app state"""
    from app import vector_store
    return vector_store

def validate_openai_key():
    """Validate that OpenAI API key is configured"""
    if not config.OPENAI_API_KEY:
        raise HTTPException(
            status_code=500, 
            detail="OpenAI API key not configured. Set the OPENAI_API_KEY environment variable."
        )
    return config.OPENAI_API_KEY