# api/routes.py - Enhanced API routes for integrated system
import logging
import subprocess
import os
from fastapi import APIRouter, HTTPException, Depends, Cookie, Response, BackgroundTasks
import uuid
from typing import Optional
import asyncio

from api.models import (
    DocumentInput, DocumentResponse, Query, 
    ChatRequest, ChatResponse, SearchResult
)
from api.dependencies import get_document_manager, get_chatbot, validate_openai_key
from integration_manager import check_embedding_status

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/api")

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    response: Response,
    chatbot=Depends(get_chatbot),
    api_key: str = Depends(validate_openai_key),
    session_id: Optional[str] = Cookie(None)
):
    """Chat with the assistant using Langchain RAG with session management"""
    try:
        # Create or use session ID for maintaining chat context
        if not session_id:
            session_id = str(uuid.uuid4())
            response.set_cookie(
                key="session_id", 
                value=session_id, 
                httponly=True,
                max_age=3600*24*7,  # 7 day cookie
                samesite="lax"
            )
            logger.info(f"Created new session: {session_id}")
        else:
            logger.info(f"Using existing session: {session_id}")
        
        # Generate answer using the enhanced chatbot with relevance checking
        answer, sources = await chatbot.generate_answer(
            request.question, 
            request.chat_history, 
            session_id
        )
        
        return {"answer": answer, "sources": sources}
    except Exception as e:
        logger.error(f"Error generating chat response: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_system_status():
    """Get system status information including embedding statistics"""
    try:
        status = check_embedding_status()
        return status
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/trigger-crawl")
async def trigger_crawler(background_tasks: BackgroundTasks):
    """Manually trigger the news crawler job"""
    try:
        # Define a function to run the crawler in the background
        def run_crawler_job():
            try:
                # Get the path to the cron_job.py script
                script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cron_job.py")
                
                # Run the crawler script as a subprocess
                result = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                logger.info(f"Crawler job triggered manually: {result.stdout}")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"Error running crawler job: {e}")
                logger.error(f"Stdout: {e.stdout}")
                logger.error(f"Stderr: {e.stderr}")
                return False
            except Exception as e:
                logger.error(f"Unexpected error running crawler job: {e}")
                return False
        
        # Add the crawler job to background tasks
        background_tasks.add_task(run_crawler_job)
        
        return {"message": "Crawler job started in background"}
    except Exception as e:
        logger.error(f"Error triggering crawler job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session")
async def get_session_info(
    session_id: Optional[str] = Cookie(None),
    chatbot=Depends(get_chatbot)
):
    """Get information about the current session"""
    if not session_id:
        return {"has_session": False, "message": "No active session"}
    
    # Get session history
    history = chatbot.get_session_history(session_id)
    message_count = len(history)
    
    return {
        "has_session": True,
        "session_id": session_id,
        "message_count": message_count
    }

@router.delete("/session")
async def clear_session(
    response: Response,
    session_id: Optional[str] = Cookie(None),
    chatbot=Depends(get_chatbot)
):
    """Clear the current session history"""
    if session_id and session_id in chatbot.session_histories:
        # Clear the session history
        chatbot.session_histories[session_id] = []
        logger.info(f"Cleared session history for {session_id}")
        
    # Clear the cookie
    response.delete_cookie(key="session_id")
    
    return {"message": "Session cleared successfully"}