# core/chatbot.py - Enhanced Chatbot implementation with improved relevance checking

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
    """Enhanced economic chatbot with RAG, general capability, conversation memory, and relevance checking"""
    
    def __init__(self, document_manager, vector_store):
        """Initialize the chatbot with necessary components"""
        self.document_manager = document_manager
        self.vector_store = vector_store
        self.model_name = config.OPENAI_CHAT_MODEL
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.session_histories = {}  # Store chat history by session ID
        
        # Minimum relevance score threshold
        self.relevance_threshold = 0
        
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
                base_retriever = self.vector_store.get_retriever()
                
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
                
                # Create a relevance checking chain for evaluating if the RAG answer is relevant to the query
                relevance_checking_template = """
                Your task is to determine whether an answer is directly relevant to the question asked.
                Score the relevance on a scale from a 0.0 to 1.0, where:
                - 1.0 means the answer is highly relevant and directly addresses the question
                - 0.0 means the answer is not at all relevant to the question
                
                Examples:
                Question: "What's the price of Bitcoin?"
                Answer: "As of today, Bitcoin is trading at approximately $50,000 per coin."
                Score: 1.0 (Directly answers the question)
                
                Question: "What are the recent developments in DeFi protocols?"
                Answer: "Sorry, I don't have specific information about recent DeFi protocol developments."
                Score: 0.2 (Acknowledges the topic but doesn't provide substantive information)
                
                Question: "Will crypto recover in the future?"
                Answer: "While I cannot predict the future with certainty, many analysts believe the cryptocurrency market is cyclical..."
                Score: 0.8 (Addresses the question thoughtfully within limitations)
                
                Question: "What's your favorite color?"
                Answer: "I don't have preferences or favorites as I'm an AI assistant."
                Score: 1.0 (Direct and appropriate response to the question)
                
                Question: {question}
                Answer: {answer}
                
                First, analyze how directly the answer addresses the specific question asked.
                Then provide your score as a decimal number between 0.0 and 1.0.
                
                Relevance Score (just the number):
                """
                
                relevance_checking_prompt = PromptTemplate(
                    input_variables=["question", "answer"],
                    template=relevance_checking_template
                )
                
                self.relevance_checking_chain = LLMChain(
                    llm=self.llm,
                    prompt=relevance_checking_prompt
                )
                
                logger.info(f"Chatbot initialized with {self.model_name}")
                
            except Exception as e:
                logger.error(f"Error initializing chatbot: {e}")
                self.llm = None
                self.rag_chain = None
                self.general_chain = None
                self.relevance_checking_chain = None
    
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
    
    async def _check_answer_relevance(self, question: str, answer: str) -> float:
        """
        Check if the RAG-generated answer is relevant to the question.
        Returns a relevance score between 0.0 and 1.0.
        """
        try:
            # Use the relevance checking chain to get a score
            response = self.relevance_checking_chain.run(question=question, answer=answer)
            
            # Parse the response to extract just the score
            try:
                # Extract numeric value from the response
                cleaned_response = response.strip()
                
                # If multiple lines, take the last line
                if "\n" in cleaned_response:
                    cleaned_response = cleaned_response.split("\n")[-1]
                
                # Try to convert to float
                relevance_score = float(cleaned_response)
                
                # Ensure it's in range 0.0-1.0
                relevance_score = max(0.0, min(1.0, relevance_score))
                
                logger.info(f"Answer relevance score: {relevance_score}")
                return relevance_score
                
            except ValueError:
                # If parsing fails, default to a middle value
                logger.warning(f"Could not parse relevance score: '{response}', defaulting to 0.5")
                return 0.5
                
        except Exception as e:
            logger.error(f"Error checking answer relevance: {e}")
            # Default to 0.5 in case of errors
            return 0.5
    
    async def generate_answer(self, 
                        question: str, 
                        chat_history: Optional[List[Dict]] = None, 
                        session_id: str = "default") -> Tuple[str, List[Dict]]:
        """Generate an answer using RAG workflow"""
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
            
            # Step 1: First, always try the RAG approach if we have documents
            if have_documents:
                logger.info("Using RAG to generate an initial response")
                
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
                
                # Step 2: Check if we have sources and if the answer is relevant
                if sources:
                    # Step 3: Evaluate the relevance of the answer to the question
                    relevance_score = await self._check_answer_relevance(question, rag_answer)
                    
                    # Step 4: If the answer is relevant enough, use it
                    if relevance_score >= self.relevance_threshold:
                        logger.info(f"Using RAG answer (relevance score: {relevance_score})")
                        
                        # Update session history with this interaction
                        self.update_session_history(session_id, question, rag_answer)
                        
                        return rag_answer, sources
                    else:
                        logger.info(f"RAG answer not relevant enough (score: {relevance_score}), falling back to general knowledge")
                else:
                    logger.info("No relevant sources found, falling back to general knowledge")
            else:
                logger.info("No documents available, using general knowledge")
            
            # Step 5: Fallback to general knowledge if RAG didn't work or wasn't relevant
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
        # This could be expanded to log feedback, retrain models, or adjust relevance scores
        logging.info(f"Received feedback: {feedback}")
        # For now, just log the feedback
        feedback_log = {
            "question": question,
            "answer": answer,
            "feedback": feedback,
            "sources": [doc["id"] for doc in relevant_docs]
        }
        logging.info(f"Feedback log: {feedback_log}")