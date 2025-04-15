# core/utils.py - Utility functions
import uuid
import json
import tiktoken
from datetime import datetime
from typing import Dict, List, Any, Optional

def generate_id() -> str:
    """Generate a unique ID"""
    return str(uuid.uuid4())

def get_current_timestamp() -> str:
    """Get current timestamp in ISO format"""
    return datetime.now().isoformat()

def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """Count the number of tokens in a text string"""
    encoding = tiktoken.get_encoding(encoding_name)
    token_count = len(encoding.encode(text))
    return token_count

def save_json(data: Any, filepath: str) -> None:
    """Save data to a JSON file"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(filepath: str) -> Any:
    """Load data from a JSON file"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncate text to a maximum length"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def format_chat_history(history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Format chat history for OpenAI API"""
    formatted_history = []
    for msg in history:
        formatted_history.append({
            "role": "user" if msg["role"] == "user" else "assistant",
            "content": msg["content"]
        })
    return formatted_history