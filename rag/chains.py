# rag/chains.py - Enhanced LLM chains for RAG with better context handling
import logging
from langchain.chains import ConversationalRetrievalChain
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate 

import config

logger = logging.getLogger(__name__)

class RAGChainManager:
    """Manages RAG chains for conversational retrieval with improved context handling"""
    
    def __init__(self, llm, retriever, query_expansion_chain=None):
        """Initialize the RAG chain manager"""
        self.llm = llm
        self.retriever = retriever
        self.query_expansion_chain = query_expansion_chain
        
        # Create the QA chain
        self.qa_chain = self._create_qa_chain()
        
        # Create the final conversational retrieval chain
        self.conversation_chain = self._create_conversation_chain()
        
        logger.info("RAG chains initialized successfully")
    
    def _create_qa_chain(self):
        """Create an enhanced question answering chain with better prompting"""
        qa_template = """
        You are a helpful assistant that specializes in cryptocurrency and economics. Your task is to provide informative answers based on the provided context.
        
        Use the following pieces of context to answer the question. The context contains information from various cryptocurrency news sources.
        
        If the context provides the information needed to answer the question, use it to give a complete and accurate response.
        If the context doesn't contain enough information, say so clearly - don't try to make up an answer.
        
        When using information from the context, cite your sources by mentioning the source.
        
        Context:
        {context}
        
        Question: {question}
        
        Answer:
        """
        
        qa_prompt = PromptTemplate(
            input_variables=["context", "question"],
            template=qa_template
        )
        
        return load_qa_chain(
            llm=self.llm,
            chain_type="stuff",
            prompt=qa_prompt
        )
    
    def _create_conversation_chain(self):
        """Create an improved conversational retrieval chain"""
        return ConversationalRetrievalChain(
            retriever=self.retriever,
            combine_docs_chain=self.qa_chain,
            question_generator=self.query_expansion_chain,
            return_source_documents=True,
            verbose=config.DEBUG,
            # Increase max token limit for context to allow more flexible responses
            max_tokens_limit=config.MAX_CONTEXT_LENGTH
        )
    
    def generate_response(self, question, chat_history=None):
        """Generate a response using the conversational retrieval chain with improved context handling"""
        if chat_history is None:
            chat_history = []
            
        try:
            # Convert chat history to the format expected by LangChain
            langchain_history = []
            for user_msg, ai_msg in chat_history:
                if user_msg:
                    langchain_history.append((user_msg, ai_msg if ai_msg else ""))
            
            # Get response from conversation chain with error handling
            response = self.conversation_chain({
                "question": question,
                "chat_history": langchain_history
            })
            
            return response
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            logger.error(f"Chat history type: {type(chat_history)}")
            logger.error(f"Chat history content: {chat_history}")
            raise