# rag/retriever.py - Simplified and more effective retriever implementation
import logging
from langchain.retrievers.contextual_compression import ContextualCompressionRetriever
from langchain.retrievers.document_compressors.chain_extract import LLMChainExtractor
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

import config

logger = logging.getLogger(__name__)

class AdvancedRetriever:
    """Implements a simplified and effective retrieval strategy for RAG"""
    
    def __init__(self, llm, base_retriever):
        """Initialize the advanced retriever with components"""
        self.llm = llm
        self.base_retriever = base_retriever
        
        # Create a single optimized retriever
        logger.info("Initializing optimized retriever")
        self.retriever = self._create_optimized_retriever()
        
        # Create query expansion chain if enabled
        self.query_expansion_chain = None
        if config.USE_QUERY_EXPANSION:
            self.query_expansion_chain = self._create_query_expansion_chain()
    
    def _create_query_expansion_chain(self):
        """Create a query expansion chain for better retrieval"""
        query_expansion_template = """
        You are an AI assistant helping to generate better search queries for an economic knowledge base.
        Given the user's question, create an improved search query that will help find the most relevant information.
        Make the query more specific, include synonyms, and focus on the key economic concepts.
        
        Original question: {question}
        
        Improved search query:
        """
        
        query_expansion_prompt = PromptTemplate(
            input_variables=["question"],
            template=query_expansion_template
        )
        
        return LLMChain(
            llm=self.llm,
            prompt=query_expansion_prompt
        )
    
    def _create_optimized_retriever(self):
        """Create a single optimized retriever with contextual compression"""
        # Use contextual compression to get more relevant results
        compressor = LLMChainExtractor.from_llm(self.llm)
        
        return ContextualCompressionRetriever(
            base_compressor=compressor,
            base_retriever=self.base_retriever
        )
    
    def get_retriever(self):
        """Return the configured retriever"""
        return self.retriever
    
    def get_query_expansion_chain(self):
        """Return the query expansion chain if enabled, or None"""
        return self.query_expansion_chain