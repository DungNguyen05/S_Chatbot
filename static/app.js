/**
 * app.js - Main JavaScript for the Crypto News Assistant
 * Handles chat functionality, dashboard updates, and UI interactions
 */

// Global variables
let chatHistory = [];
let settings = {
    maxResults: 5,
    temperature: 0.3
};
let lastCrawlTime = null;

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initial setup
    loadChatHistory();
    setupEventListeners();
    loadDashboardData();
    startStatusUpdates();
    
    // Set next crawl time estimate
    updateNextCrawlTime();
});

// ------------- Chat Functions -------------

// Add a message to the chat display
function addMessageToChat(message, role, sources = []) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message');
    messageDiv.classList.add(role === 'user' ? 'user-message' : 'bot-message');
    
    // Add message content with proper formatting for new lines
    messageDiv.innerHTML = message.replace(/\n/g, '<br>');
    
    // Add sources if available
    if (sources && sources.length > 0) {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.classList.add('sources');
        sourcesDiv.innerHTML = '<strong>Sources:</strong> ' + 
            sources.map(s => s.source).join(', ');
        messageDiv.appendChild(sourcesDiv);
    }
    
    chatMessages.appendChild(messageDiv);
    
    // Auto scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // Add to chat history
    chatHistory.push({
        role: role,
        content: message,
        sources: sources
    });
    
    // Save chat history to localStorage for persistence
    saveChatHistory();
}

// Add typing indicator
function addTypingIndicator() {
    const chatMessages = document.getElementById('chatMessages');
    const typingDiv = document.createElement('div');
    typingDiv.classList.add('typing-indicator');
    
    // Add three dots for animation
    for (let i = 0; i < 3; i++) {
        const span = document.createElement('span');
        typingDiv.appendChild(span);
    }
    
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return typingDiv;
}

// Remove typing indicator
function removeTypingIndicator(element) {
    if (element && element.parentNode) {
        element.parentNode.removeChild(element);
    }
}

// Send a message to the chatbot
async function sendMessage() {
    const userQuestion = document.getElementById('userQuestion').value.trim();
    if (!userQuestion) return;
    
    // Add user message to chat
    addMessageToChat(userQuestion, 'user');
    document.getElementById('userQuestion').value = '';
    
    try {
        // Disable send button while processing
        const sendButton = document.getElementById('sendButton');
        sendButton.disabled = true;
        sendButton.style.opacity = '0.7';
        
        // Show typing indicator
        const typingDiv = addTypingIndicator();
        
        // Prepare chat history format for API
        const apiChatHistory = formatChatHistoryForAPI();
        
        // Call chat API
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: userQuestion,
                chat_history: apiChatHistory,
                settings: settings
            })
        });
        
        // Remove typing indicator
        removeTypingIndicator(typingDiv);
        
        if (!response.ok) {
            throw new Error('Error getting response');
        }
        
        const data = await response.json();
        
        // Add bot response to chat
        addMessageToChat(data.answer, 'bot', data.sources);
        
    } catch (error) {
        console.error('Error:', error);
        // Remove typing indicator if still exists
        document.querySelectorAll('.typing-indicator').forEach(el => el.remove());
        addMessageToChat('Sorry, there was an error processing your request. Please try again later.', 'bot');
    } finally {
        // Re-enable send button
        const sendButton = document.getElementById('sendButton');
        sendButton.disabled = false;
        sendButton.style.opacity = '1';
    }
}

// Format chat history for API request
function formatChatHistoryForAPI() {
    // Format the chat history for the API with proper role labels
    return chatHistory.map(msg => ({
        role: msg.role === 'user' ? 'user' : 'assistant',
        content: msg.content
    }));
}

// Save chat history to localStorage
function saveChatHistory() {
    try {
        localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
    } catch (e) {
        console.warn('Could not save chat history to localStorage', e);
    }
}

// Load chat history from localStorage
function loadChatHistory() {
    try {
        const savedHistory = localStorage.getItem('chatHistory');
        if (savedHistory) {
            chatHistory = JSON.parse(savedHistory);
            
            // Display loaded messages
            const chatMessages = document.getElementById('chatMessages');
            chatMessages.innerHTML = ''; // Clear existing messages
            
            chatHistory.forEach(msg => {
                const messageDiv = document.createElement('div');
                messageDiv.classList.add('message');
                messageDiv.classList.add(msg.role === 'user' ? 'user-message' : 'bot-message');
                
                // Add message content with proper formatting for new lines
                messageDiv.innerHTML = msg.content.replace(/\n/g, '<br>');
                
                // Add sources if available
                if (msg.sources && msg.sources.length > 0) {
                    const sourcesDiv = document.createElement('div');
                    sourcesDiv.classList.add('sources');
                    sourcesDiv.innerHTML = '<strong>Sources:</strong> ' + 
                        msg.sources.map(s => s.source).join(', ');
                    messageDiv.appendChild(sourcesDiv);
                }
                
                chatMessages.appendChild(messageDiv);
            });
            
            // Auto scroll to bottom
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            console.log(`Loaded ${chatHistory.length} messages from localStorage`);
            return;
        }
    } catch (e) {
        console.warn('Could not load chat history from localStorage', e);
    }
    
    // Add welcome message if no history loaded
    addMessageToChat('Hello! I\'m your Crypto News Assistant. I can answer questions about cryptocurrency news, trends, and prices based on real-time data. How can I help you today?', 'bot');
}

// Clear chat history
function clearChat() {
    // Clear chat display
    document.getElementById('chatMessages').innerHTML = '';
    
    // Clear chat history array
    chatHistory = [];
    
    // Clear localStorage
    localStorage.removeItem('chatHistory');
    
    // Also clear server-side session
    fetch('/api/session', {
        method: 'DELETE'
    }).then(() => {
        console.log('Server-side session cleared');
    }).catch(error => {
        console.error('Error clearing server-side session:', error);
    });
    
    // Add welcome message
    addMessageToChat('Chat history cleared. How can I help you today?', 'bot');
}

// ------------- Dashboard Functions -------------

// Load dashboard data
async function loadDashboardData() {
    try {
        // Load embedding status
        await loadEmbeddingStatus();
        
        // Load fear and greed index
        await loadFearAndGreedIndex();
        
        // Load top coins
        await loadTopCoins();
        
        // Load latest news
        await loadLatestNews();
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        setStatusIndicator(false, 'Connection error');
    }
}

// Load embedding status
async function loadEmbeddingStatus() {
    try {
        const response = await fetch('/api/status');
        if (!response.ok) throw new Error('Failed to fetch status');
        
        const data = await response.json();
        
        // Update UI with embedding status
        document.getElementById('articlesCount').textContent = data.total_articles || '0';
        document.getElementById('embeddedCount').textContent = data.embedded_articles || '0';
        
        if (data.latest_article) {
            const date = new Date(data.latest_article);
            document.getElementById('latestArticleTime').textContent = date.toLocaleString();
            lastCrawlTime = date;
            updateNextCrawlTime();
        } else {
            document.getElementById('latestArticleTime').textContent = 'No data';
        }
        
        return data;
    } catch (error) {
        console.error('Error loading embedding status:', error);
        document.getElementById('articlesCount').textContent = 'Error';
        document.getElementById('embeddedCount').textContent = 'Error';
        document.getElementById('latestArticleTime').textContent = 'Error';
        throw error;
    }
}

// Load Fear and Greed Index
async function loadFearAndGreedIndex() {
    try {
        const response = await fetch('/api/fear_and_greed?limit=1');
        if (!response.ok) throw new Error('Failed to fetch fear and greed index');
        
        const data = await response.json();
        if (!data.fear_and_greed || data.fear_and_greed.length === 0) {
            throw new Error('No fear and greed data available');
        }
        
        const fgIndex = data.fear_and_greed[0];
        const value = fgIndex.value || 50;
        const classification = fgIndex.value_classification || 'Neutral';
        
        // Update UI
        document.getElementById('fearGreedValue').style.left = `${value}%`;
        document.getElementById('sentimentText').textContent = classification;
        document.getElementById('sentimentValue').textContent = value;
        
        // Set color based on classification
        let color;
        if (value < 25) color = '#dc3545'; // Extreme Fear
        else if (value < 45) color = '#ff9500'; // Fear
        else if (value < 55) color = '#ffc107'; // Neutral
        else if (value < 75) color = '#28a745'; // Greed
        else color = '#198754'; // Extreme Greed
        
        document.getElementById('fearGreedValue').style.backgroundColor = color;
        document.getElementById('fearGreedValue').style.borderColor = color;
        
    } catch (error) {
        console.error('Error loading fear and greed index:', error);
        document.getElementById('sentimentText').textContent = 'Data unavailable';
        document.getElementById('sentimentValue').textContent = '--';
    }
}

// Load top coins
async function loadTopCoins() {
    try {
        const response = await fetch('/api/coins?limit=5');
        if (!response.ok) throw new Error('Failed to fetch coins');
        
        const data = await response.json();
        if (!data.coins || data.coins.length === 0) {
            throw new Error('No coin data available');
        }
        
        // Update UI
        const tableBody = document.querySelector('#coinsTable tbody');
        tableBody.innerHTML = '';
        
        data.coins.forEach(coin => {
            const row = document.createElement('tr');
            
            // Format price with appropriate decimals
            let formattedPrice;
            if (coin.price < 0.01) {
                formattedPrice = coin.price.toFixed(8);
            } else if (coin.price < 1) {
                formattedPrice = coin.price.toFixed(4);
            } else {
                formattedPrice = coin.price.toFixed(2);
            }
            
            // For demonstration, we'll use random values for price change
            // In a real app, this would come from the API
            const changePercent = (Math.random() * 10 - 5).toFixed(2);
            const changeClass = changePercent >= 0 ? 'price-up' : 'price-down';
            const changePrefix = changePercent >= 0 ? '+' : '';
            
            row.innerHTML = `
                <td><strong>${coin.symbol}</strong> - ${coin.name}</td>
                <td>$${formattedPrice}</td>
                <td class="${changeClass}">${changePrefix}${changePercent}%</td>
            `;
            
            tableBody.appendChild(row);
        });
        
    } catch (error) {
        console.error('Error loading coins:', error);
        const tableBody = document.querySelector('#coinsTable tbody');
        tableBody.innerHTML = '<tr><td colspan="3" class="loading-message">Could not load coin data</td></tr>';
    }
}

// Load latest news
async function loadLatestNews() {
    try {
        const response = await fetch('/api/articles?limit=10');
        if (!response.ok) throw new Error('Failed to fetch news');
        
        const data = await response.json();
        if (!data.articles || data.articles.length === 0) {
            throw new Error('No news articles available');
        }
        
        // Update UI
        const newsList = document.getElementById('newsList');
        newsList.innerHTML = '';
        
        data.articles.forEach(article => {
            const newsItem = document.createElement('div');
            newsItem.classList.add('news-item');
            
            // Format date
            let dateStr = 'Unknown date';
            if (article.published_at) {
                const date = new Date(article.published_at);
                dateStr = date.toLocaleString();
            }
            
            // Truncate summary if needed
            let summary = article.summary || article.content || 'No content available';
            if (summary.length > 150) {
                summary = summary.substring(0, 150) + '...';
            }
            
            newsItem.innerHTML = `
                <div class="news-title">${article.title || 'Untitled'}</div>
                <div class="news-meta">
                    <span>${article.source || 'Unknown source'}</span>
                    <span>${dateStr}</span>
                </div>
                <div class="news-summary">${summary}</div>
            `;
            
            // Add click event to ask question about this news
            newsItem.addEventListener('click', () => {
                document.getElementById('userQuestion').value = `Tell me about the news: "${article.title}"`;
                showTab('dashboardTab', document.querySelector('.tab.active'));
                document.getElementById('userQuestion').focus();
            });
            
            newsList.appendChild(newsItem);
        });
        
    } catch (error) {
        console.error('Error loading news:', error);
        document.getElementById('newsList').innerHTML = '<p class="loading-message">Could not load news articles</p>';
    }
}

// ------------- UI Functions -------------

// Show tab content
function showTab(tabId, tabElement) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Deactivate all tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tabId).classList.add('active');
    
    // Activate selected tab button
    tabElement.classList.add('active');
}

// Filter news by search term
function filterNews() {
    const searchTerm = document.getElementById('newsSearch').value.toLowerCase();
    const newsItems = document.querySelectorAll('.news-item');
    
    newsItems.forEach(item => {
        const title = item.querySelector('.news-title').textContent.toLowerCase();
        const summary = item.querySelector('.news-summary').textContent.toLowerCase();
        
        if (title.includes(searchTerm) || summary.includes(searchTerm)) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}

// Set status indicator
function setStatusIndicator(isConnected, message = null) {
    const indicator = document.getElementById('statusIndicator');
    const statusIcon = indicator.querySelector('i');
    const statusText = document.getElementById('statusText');
    
    if (isConnected) {
        statusIcon.style.color = 'var(--success-color)';
        statusText.textContent = message || 'Connected';
    } else {
        statusIcon.style.color = 'var(--danger-color)';
        statusText.textContent = message || 'Disconnected';
    }
}

// Update next crawl time estimation
function updateNextCrawlTime() {
    if (!lastCrawlTime) return;
    
    const crawlDate = new Date(lastCrawlTime);
    const nextCrawl = new Date(crawlDate.getTime() + 15 * 60 * 1000); // Add 15 minutes
    
    const now = new Date();
    const minutesUntilNextCrawl = Math.round((nextCrawl - now) / (60 * 1000));
    
    // Update UI
    const nextCrawlTimeElement = document.getElementById('nextCrawlTime');
    if (minutesUntilNextCrawl <= 0) {
        nextCrawlTimeElement.textContent = 'any moment now';
    } else {
        nextCrawlTimeElement.textContent = `in about ${minutesUntilNextCrawl} minute${minutesUntilNextCrawl !== 1 ? 's' : ''}`;
    }
}

// Periodically check status
function startStatusUpdates() {
    // Check status every 30 seconds
    setInterval(async () => {
        try {
            await loadEmbeddingStatus();
            setStatusIndicator(true);
        } catch (error) {
            setStatusIndicator(false, 'Connection lost');
        }
    }, 30000);
}

// Trigger manual crawl
async function triggerManualCrawl() {
    try {
        document.getElementById('triggerCrawl').disabled = true;
        document.getElementById('triggerCrawl').textContent = 'Crawling...';
        
        const response = await fetch('/api/trigger-crawl', {
            method: 'POST'
        });
        
        if (!response.ok) throw new Error('Failed to trigger crawl');
        
        const data = await response.json();
        
        // Show success message
        alert('Crawl job triggered successfully! Check back in a few minutes for updated data.');
        
        // Refresh dashboard data after a delay
        setTimeout(loadDashboardData, 5000);
        
    } catch (error) {
        console.error('Error triggering crawl:', error);
        alert('Failed to trigger crawl job. Please try again later.');
    } finally {
        document.getElementById('triggerCrawl').disabled = false;
        document.getElementById('triggerCrawl').innerHTML = '<i class="fas fa-spider"></i> Trigger Manual Crawl';
    }
}

// Save settings
function saveSettings() {
    const maxResults = parseInt(document.getElementById('resultCount').value);
    const temperature = parseFloat(document.getElementById('temperature').value);
    
    settings = {
        maxResults: maxResults,
        temperature: temperature
    };
    
    localStorage.setItem('settings', JSON.stringify(settings));
    alert('Settings saved successfully!');
}

// Load settings
function loadSettings() {
    try {
        const savedSettings = localStorage.getItem('settings');
        if (savedSettings) {
            settings = JSON.parse(savedSettings);
            
            // Update UI
            document.getElementById('resultCount').value = settings.maxResults;
            document.getElementById('resultCountValue').textContent = settings.maxResults;
            document.getElementById('temperature').value = settings.temperature;
            document.getElementById('temperatureValue').textContent = settings.temperature;
        }
    } catch (e) {
        console.warn('Could not load settings from localStorage', e);
    }
}

// ------------- Event Listeners -------------

function setupEventListeners() {
    // Chat input - send on Enter (Shift+Enter for new line)
    document.getElementById('userQuestion').addEventListener('keydown', function(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });
    
    // Clear chat button
    document.getElementById('clearChat').addEventListener('click', clearChat);
    
    // News search filter
    document.getElementById('newsSearch').addEventListener('input', filterNews);
    
    // Refresh news button
    document.getElementById('refreshNews').addEventListener('click', loadLatestNews);
    
    // Range sliders - update displayed value
    document.getElementById('resultCount').addEventListener('input', function() {
        document.getElementById('resultCountValue').textContent = this.value;
    });
    
    document.getElementById('temperature').addEventListener('input', function() {
        document.getElementById('temperatureValue').textContent = this.value;
    });
    
    // Save settings button
    document.getElementById('saveSettings').addEventListener('click', saveSettings);
    
    // Trigger crawl button
    document.getElementById('triggerCrawl').addEventListener('click', triggerManualCrawl);
    
    // Load saved settings
    loadSettings();
}