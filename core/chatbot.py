# core/chatbot.py - Optimized Chatbot implementation with improved token usage

import logging
from typing import List, Dict, Tuple, Optional, Any
import tiktoken
from langchain_community.callbacks import get_openai_callback
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage

import config
from rag.retriever import AdvancedRetriever
from rag.chains import RAGChainManager

logger = logging.getLogger(__name__)

class Chatbot:
    """Optimized economic chatbot with RAG, general capability, and conversation memory"""
    
    def __init__(self, document_manager, vector_store):
        """Initialize the chatbot with necessary components"""
        self.document_manager = document_manager
        self.vector_store = vector_store
        self.model_name = config.OPENAI_CHAT_MODEL
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.session_histories = {}  # Store chat history by session ID
        
        # Initialize OpenAI LLM
        if not config.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set. OpenAI chat completion will not work.")
            self.llm = None
            self.rag_chain = None
            self.general_chain = None
        else:
            try:
                # Initialize LLM
                self.llm = ChatOpenAI(
                    model_name=self.model_name,
                    temperature=config.TEMPERATURE,
                    openai_api_key=config.OPENAI_API_KEY,
                    max_tokens=config.MAX_TOKENS_RESPONSE
                )
                
                # Get base retriever from vector store
                base_retriever = self.vector_store.get_retriever(
                    search_kwargs={
                        "k": config.MAX_SEARCH_RESULTS,
                        "score_threshold": 0.1  # Add required score_threshold parameter
                    }
                )
                
                # Set up advanced retriever
                advanced_retriever = AdvancedRetriever(self.llm, base_retriever)
                
                # Get query expansion chain if enabled
                query_expansion_chain = advanced_retriever.get_query_expansion_chain()
                
                # Set up RAG chain manager for document-based answers
                self.rag_chain = RAGChainManager(
                    self.llm,
                    advanced_retriever.get_retriever(),
                    query_expansion_chain
                )
                
                # Create a general-purpose chain for non-document-specific answers
                general_template = """
                You are a helpful crypto and economics assistant that can answer a wide range of questions.
                Use your general knowledge to provide a helpful response.
                
                Chat History:
                {chat_history}
                
                Current Question: {question}
                
                Think about the context of the conversation and provide a relevant, helpful answer:
                """
                
                general_prompt = PromptTemplate(
                    input_variables=["chat_history", "question"],
                    template=general_template
                )
                
                self.general_chain = LLMChain(
                    llm=self.llm,
                    prompt=general_prompt
                )
                
                logger.info(f"Chatbot initialized with {self.model_name}")
                
            except Exception as e:
                logger.error(f"Error initializing chatbot: {e}")
                self.llm = None
                self.rag_chain = None
                self.general_chain = None
    
    def get_session_history(self, session_id: str = "default") -> List[Tuple[str, str]]:
        """Get chat history for a session"""
        if session_id not in self.session_histories:
            self.session_histories[session_id] = []
        return self.session_histories[session_id]
    
    def update_session_history(self, session_id: str, user_message: str, ai_message: str) -> None:
        """Update chat history for a session"""
        if session_id not in self.session_histories:
            self.session_histories[session_id] = []
        
        # Add message pair to history
        self.session_histories[session_id].append((user_message, ai_message))
        
        # Keep only the last 5 interactions to manage token usage
        if len(self.session_histories[session_id]) > 5:
            self.session_histories[session_id] = self.session_histories[session_id][-5:]
        
        logger.info(f"Updated session history for {session_id}, now has {len(self.session_histories[session_id])} messages")
    
    def _format_conversation_history(self, history: List[Tuple[str, str]]) -> str:
        """Format conversation history into a readable string format"""
        formatted_history = ""
        for i, (user_msg, ai_msg) in enumerate(history):
            if user_msg and ai_msg:
                formatted_history += f"User: {user_msg}\nAssistant: {ai_msg}\n\n"
            elif user_msg:
                formatted_history += f"User: {user_msg}\n\n"
        return formatted_history.strip()
    
    def _merge_histories(self, 
                         session_history: List[Tuple[str, str]], 
                         provided_history: List[Dict[str, str]]) -> List[Tuple[str, str]]:
        """Merge session history with provided history, avoiding duplicates"""
        # Format incoming chat history
        formatted_history = []
        if provided_history:
            for msg in provided_history:
                if msg["role"] == "user":
                    user_content = msg["content"]
                    ai_content = ""  # Default empty assistant response
                    
                    # Check if the next message is from assistant
                    next_index = provided_history.index(msg) + 1
                    if next_index < len(provided_history) and provided_history[next_index]["role"] == "assistant":
                        ai_content = provided_history[next_index]["content"]
                    
                    formatted_history.append((user_content, ai_content))
        
        # Merge histories, avoiding duplicates
        merged_history = []
        seen_pairs = set()
        
        # First add session history
        for pair in session_history:
            if pair[0]:  # Only add if user message exists
                pair_hash = hash((pair[0], pair[1]))
                if pair_hash not in seen_pairs:
                    seen_pairs.add(pair_hash)
                    merged_history.append(pair)
        
        # Then add formatted history if not duplicate
        for pair in formatted_history:
            if pair[0]:  # Only add if user message exists
                pair_hash = hash((pair[0], pair[1]))
                if pair_hash not in seen_pairs:
                    seen_pairs.add(pair_hash)
                    merged_history.append(pair)
        
        return merged_history
    
    def _count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string using the tokenizer"""
        return len(self.tokenizer.encode(text))
    
    async def generate_answer(self, 
                        question: str, 
                        chat_history: Optional[List[Dict]] = None, 
                        session_id: str = "default") -> Tuple[str, List[Dict]]:
        """Generate an answer using RAG workflow with optimized token usage"""
        # Get current session history
        session_history = self.get_session_history(session_id)
        
        # Merge with provided history
        merged_history = self._merge_histories(session_history, chat_history or [])
        
        # Use only the most recent chat history to save tokens (up to 5 interactions)
        recent_history = merged_history[-5:] if len(merged_history) > 5 else merged_history
        
        # Format history for context
        history_text = self._format_conversation_history(recent_history)
        
        # Log token usage for history
        history_tokens = self._count_tokens(history_text)
        logger.info(f"Chat history uses {history_tokens} tokens")
        
        try:
            have_documents = len(self.document_manager.get_all_documents()) > 0
            
            # If we have documents, try to use them first
            if have_documents:
                logger.info("Using RAG to generate a response")
                
                # Use callback to track token usage
                with get_openai_callback() as cb:
                    # Get response from RAG chain
                    rag_response = self.rag_chain.generate_response(question, recent_history)
                    
                    # Log token usage
                    logger.info(f"RAG tokens used: {cb.total_tokens} (Prompt: {cb.prompt_tokens}, Completion: {cb.completion_tokens})")
                
                # Extract answer and source documents
                rag_answer = rag_response.get("answer", "")
                source_docs = rag_response.get("source_documents", [])
                
                # Extract source information from documents
                sources = []
                seen_doc_ids = set()
                
                for doc in source_docs:
                    doc_id = doc.metadata.get("doc_id", "unknown")
                    source = doc.metadata.get("source", "Unknown Source")
                    
                    # De-duplicate sources
                    if doc_id not in seen_doc_ids:
                        seen_doc_ids.add(doc_id)
                        sources.append({
                            "id": doc_id,
                            "source": source
                        })
                
                # If we found relevant documents, use the RAG answer
                if sources:
                    logger.info("Using RAG answer with relevant sources")
                    
                    # Update session history with this interaction
                    self.update_session_history(session_id, question, rag_answer)
                    
                    return rag_answer, sources
                else:
                    logger.info("No relevant sources found, falling back to general knowledge")
            else:
                logger.info("No documents available, using general knowledge")
            
            # Fallback to general knowledge if RAG didn't work or no relevant sources
            with get_openai_callback() as cb:
                answer = self.general_chain.run(
                    chat_history=history_text,
                    question=question
                )
                
                # Log token usage
                logger.info(f"General tokens used: {cb.total_tokens} (Prompt: {cb.prompt_tokens}, Completion: {cb.completion_tokens})")
            
            # Update session history with this interaction
            self.update_session_history(session_id, question, answer)
            
            # Return general knowledge answer with no sources
            return answer, []
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            error_message = f"I'm sorry, there was an error processing your request: {str(e)}"
            
            # Still update history with the error to maintain continuity
            self.update_session_history(session_id, question, error_message)
            
            return error_message, []
    
    def process_feedback(self, question: str, answer: str, feedback: str, relevant_docs: List[Dict]) -> None:
        """Process user feedback on answers (for future improvement)"""
        # This could be expanded to log feedback, retrain models, or adjust system
        logging.info(f"Received feedback: {feedback}")
        # For now, just log the feedback
        feedback_log = {
            "question": question,
            "answer": answer,
            "feedback": feedback,
            "sources": [doc["id"] for doc in relevant_docs]
        }
        logging.info(f"Feedback log: {feedback_log}")