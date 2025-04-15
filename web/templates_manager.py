# web/templates_manager.py - Enhanced HTML templates for the integrated system
import os
import logging
import shutil
from pathlib import Path

import config

logger = logging.getLogger(__name__)

def create_templates() -> None:
    """Create or update HTML templates for the web interface"""
    # Check if the template directory exists
    templates_dir = Path(config.TEMPLATES_DIR)
    if not templates_dir.exists():
        templates_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created templates directory: {templates_dir}")
    
    # Check if the static directory exists
    static_dir = Path(config.STATIC_DIR)
    if not static_dir.exists():
        static_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created static directory: {static_dir}")
    
    # List of required template files
    required_files = {
        templates_dir / "index.html": "Main UI template",
        static_dir / "styles.css": "CSS styles",
        static_dir / "app.js": "JavaScript functionality"
    }
    
    # Check if files exist and create defaults if needed
    missing_files = []
    for file_path, description in required_files.items():
        if not file_path.exists():
            missing_files.append((file_path, description))
    
    if missing_files:
        logger.warning(f"Missing {len(missing_files)} template files. Attempting to create defaults...")
        create_default_templates(missing_files)
    else:
        logger.info("All template files exist")

def create_default_templates(missing_files):
    """Create default template files if they are missing"""
    for file_path, description in missing_files:
        try:
            # Check if we have a default template in the package
            default_template = Path(__file__).parent / "defaults" / file_path.name
            
            if default_template.exists():
                # Copy the default template
                shutil.copy(default_template, file_path)
                logger.info(f"Created {description} from default template: {file_path}")
            else:
                # Create a basic placeholder file
                with open(file_path, 'w') as f:
                    if file_path.name == "index.html":
                        f.write(get_default_html())
                    elif file_path.name == "styles.css":
                        f.write(get_default_css())
                    elif file_path.name == "app.js":
                        f.write(get_default_js())
                    else:
                        f.write(f"/* Default {file_path.name} */")
                
                logger.info(f"Created basic placeholder for {description}: {file_path}")
        
        except Exception as e:
            logger.error(f"Error creating {description}: {e}")

def get_default_html():
    """Return a basic HTML template"""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crypto News Assistant</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>Crypto News Assistant</h1>
        </header>
        
        <main>
            <div class="chat-container">
                <div class="chat-messages" id="chatMessages"></div>
                <div class="chat-input">
                    <input type="text" id="userQuestion" placeholder="Ask about crypto...">
                    <button onclick="sendMessage()">Send</button>
                </div>
            </div>
        </main>
        
        <footer>
            <p>Integrated Crawler and RAG System</p>
        </footer>
    </div>

    <script src="/static/app.js"></script>
</body>
</html>"""

def get_default_css():
    """Return basic CSS styles"""
    return """/* Basic styles */
body {
    font-family: Arial, sans-serif;
    line-height: 1.6;
    margin: 0;
    padding: 0;
    background-color: #f4f4f8;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 1rem;
}

header {
    background-color: #2c3e50;
    color: white;
    padding: 1rem;
    text-align: center;
}

.chat-container {
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin: 1rem 0;
    overflow: hidden;
}

.chat-messages {
    height: 400px;
    overflow-y: auto;
    padding: 1rem;
}

.chat-input {
    display: flex;
    padding: 1rem;
    border-top: 1px solid #eee;
}

.chat-input input {
    flex: 1;
    padding: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
}

.chat-input button {
    background-color: #3498db;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 0.5rem 1rem;
    margin-left: 0.5rem;
    cursor: pointer;
}

footer {
    text-align: center;
    padding: 1rem;
    color: #666;
}"""

def get_default_js():
    """Return basic JavaScript functionality"""
    return """// Basic chat functionality
let chatHistory = [];

// Send a message to the chatbot
async function sendMessage() {
    const userQuestion = document.getElementById('userQuestion').value.trim();
    if (!userQuestion) return;
    
    // Add user message to chat
    addMessageToChat(userQuestion, 'user');
    document.getElementById('userQuestion').value = '';
    
    try {
        // Call chat API
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: userQuestion,
                chat_history: chatHistory
            })
        });
        
        if (!response.ok) {
            throw new Error('Error getting response');
        }
        
        const data = await response.json();
        
        // Add bot response to chat
        addMessageToChat(data.answer, 'bot');
        
    } catch (error) {
        console.error('Error:', error);
        addMessageToChat('Sorry, there was an error processing your request.', 'bot');
    }
}

// Add a message to the chat display
function addMessageToChat(message, role) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message');
    messageDiv.classList.add(role === 'user' ? 'user-message' : 'bot-message');
    
    // Add message content with proper formatting for new lines
    messageDiv.innerHTML = message.replace(/\\n/g, '<br>');
    
    chatMessages.appendChild(messageDiv);
    
    // Auto scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // Add to chat history
    chatHistory.push({
        role: role,
        content: message
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Add welcome message
    addMessageToChat('Hello! I\'m your Crypto News Assistant. How can I help you today?', 'bot');
    
    // Listen for Enter key in the input field
    document.getElementById('userQuestion').addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });
});"""