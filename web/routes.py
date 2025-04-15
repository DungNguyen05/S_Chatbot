# web/routes.py - Enhanced web interface routes
import logging
import json
from fastapi import APIRouter, Request, Form, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

import config
from api.dependencies import get_document_manager
from integration_manager import check_embedding_status

logger = logging.getLogger(__name__)

# Set up templates
templates = Jinja2Templates(directory=str(config.TEMPLATES_DIR))

# Create router
router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def get_interface(request: Request):
    """Render the enhanced crypto news assistant interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@router.post("/upload", response_class=HTMLResponse)
async def upload_document(
    request: Request,
    content: str = Form(...),
    source: str = Form(...),
    document_manager=Depends(get_document_manager)
):
    """Upload a document from the web interface"""
    try:
        doc_id = document_manager.add_document(content, source)
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "message": f"Document added successfully with ID: {doc_id}"}
        )
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "error": str(e)}
        )

@router.get("/dashboard-data", response_class=JSONResponse)
async def get_dashboard_data():
    """Get aggregated data for the dashboard"""
    try:
        # Get embedding status
        embedding_stats = check_embedding_status()
        
        # Get stats from database
        from database import connect_db
        conn = connect_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get latest fear and greed data
        cursor.execute("SELECT * FROM fear_and_greed ORDER BY update_time DESC LIMIT 1")
        fear_and_greed = cursor.fetchone()
        
        # Get latest coin data
        cursor.execute("SELECT * FROM coin_data ORDER BY created_at DESC LIMIT 10")
        coins = cursor.fetchall()
        
        # Get recent articles
        cursor.execute("""
            SELECT id, title, published_at, source, summary 
            FROM articles 
            WHERE summary IS NOT NULL 
            ORDER BY published_at DESC 
            LIMIT 10
        """)
        articles = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {
            "embedding_stats": embedding_stats,
            "fear_and_greed": fear_and_greed,
            "coins": coins,
            "articles": articles,
            "timestamp": embedding_stats.get("latest_article")
        }
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@router.post("/manual-crawl", response_class=JSONResponse)
async def trigger_manual_crawl(background_tasks: BackgroundTasks):
    """Trigger a manual crawl from the web interface"""
    try:
        # Import the crawler running function
        from cron_job import run_cron_job
        
        # Run crawler in a background task
        background_tasks.add_task(run_cron_job)
        
        return {
            "success": True,
            "message": "Crawler job started in background"
        }
    except Exception as e:
        logger.error(f"Error triggering manual crawl: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )