# core/document_manager.py - Document handling and storage with database integration
import os
import logging
from typing import List, Dict, Any, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

import config
from core.utils import generate_id, get_current_timestamp, save_json, load_json
from database import connect_db

logger = logging.getLogger(__name__)

class DocumentManager:
    """Manages document processing, storage, and retrieval with database integration"""
    
    def __init__(self, vector_store):
        """Initialize document manager with a vector store"""
        self.vector_store = vector_store
        self.documents = []
        self.documents_file = config.DOCUMENTS_FILE
        
        # Initialize text splitter for chunking documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Load documents directly from database
        self.load_documents_from_db()
        
        logger.info(f"Document manager initialized with {len(self.documents)} documents")
    
    def add_document(self, content: str, source: str, metadata: Optional[Dict] = None) -> str:
        """Add a document to the knowledge base"""
        # Generate document ID and timestamp
        doc_id = generate_id()
        date_added = get_current_timestamp()
        
        # Create document record
        doc = {
            "id": doc_id,
            "content": content,
            "source": source,
            "date_added": date_added,
            "metadata": metadata or {}
        }
        
        # Store in our documents list
        self.documents.append(doc)
        
        # Process document with text splitter for better retrieval
        chunks = self.text_splitter.split_text(content)
        langchain_docs = []
        
        for i, chunk in enumerate(chunks):
            chunk_metadata = {
                "source": source,
                "date_added": date_added,
                "doc_id": doc_id,
                "chunk_id": i,
                **(metadata or {})
            }
            langchain_docs.append(Document(page_content=chunk, metadata=chunk_metadata))
        
        # Add to vector store
        try:
            self.vector_store.add_documents(langchain_docs)
            logger.info(f"Added document with ID {doc_id} split into {len(chunks)} chunks")
            
            # Save updated documents to JSON for backward compatibility
            self.save_data()
            
            return doc_id
        except Exception as e:
            logger.error(f"Error adding document to vector store: {e}")
            # Roll back document addition
            self.documents = [d for d in self.documents if d["id"] != doc_id]
            raise
    
    def bulk_add_documents(self, documents: List[Dict]) -> List[str]:
        """Add multiple documents at once (more efficient)"""
        if not documents:
            return []
            
        doc_ids = []
        all_langchain_docs = []
        
        for doc in documents:
            # Generate document ID and timestamp
            doc_id = generate_id()
            date_added = get_current_timestamp()
            
            # Store document info
            new_doc = {
                "id": doc_id,
                "content": doc["content"],
                "source": doc["source"],
                "date_added": date_added,
                "metadata": doc.get("metadata", {})
            }
            
            # Add to our documents list
            self.documents.append(new_doc)
            doc_ids.append(doc_id)
            
            # Split document into chunks
            chunks = self.text_splitter.split_text(doc["content"])
            
            # Create Langchain documents
            for i, chunk in enumerate(chunks):
                chunk_metadata = {
                    "source": doc["source"],
                    "date_added": date_added,
                    "doc_id": doc_id,
                    "chunk_id": i,
                    **(doc.get("metadata", {}))
                }
                all_langchain_docs.append(Document(page_content=chunk, metadata=chunk_metadata))
        
        # Batch add to vector store
        try:
            self.vector_store.add_documents(all_langchain_docs)
            logger.info(f"Added {len(documents)} documents with {len(all_langchain_docs)} total chunks")
            
            # Save updated documents to JSON for backward compatibility
            self.save_data()
            
            return doc_ids
        except Exception as e:
            logger.error(f"Error bulk adding documents: {e}")
            # Roll back addition
            self.documents = [d for d in self.documents if d["id"] not in doc_ids]
            raise
    
    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Get a document by ID"""
        for doc in self.documents:
            if doc["id"] == doc_id:
                return doc
        return None
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from storage and vector store"""
        # Find document index
        doc_index = None
        for i, doc in enumerate(self.documents):
            if doc["id"] == doc_id:
                doc_index = i
                break
                
        if doc_index is None:
            return False
        
        # Delete from vector store
        deleted = self.vector_store.delete_by_metadata("doc_id", doc_id)
        
        if deleted:
            # Remove document from list
            self.documents.pop(doc_index)
            
            # Save updated documents
            self.save_data()
            
            return True
        
        return False
    
    def save_data(self) -> None:
        """Save documents metadata to disk for backward compatibility"""
        save_json(self.documents, str(self.documents_file))
        logging.info(f"Saved {len(self.documents)} document metadata to disk")
    
    def load_documents_from_db(self) -> None:
        """Load documents metadata from the database"""
        try:
            conn = connect_db()
            if not conn:
                logger.error("Failed to connect to database")
                return
                
            cursor = conn.cursor(dictionary=True)
            
            # Get all embedded articles
            cursor.execute("""
                SELECT id, title, source, content, published_at, summary, currencies
                FROM articles
                WHERE embedded = 1
            """)
            
            articles = cursor.fetchall()
            
            # Convert articles to document format
            self.documents = []
            for article in articles:
                try:
                    if not article['content'] or not article['summary']:
                        continue
                        
                    doc_id = f"db-{article['id']}"
                    metadata = {
                        "db_id": article['id'],
                        "published_at": str(article['published_at']),
                        "currencies": article['currencies'] or "Unknown"
                    }
                    
                    self.documents.append({
                        "id": doc_id,
                        "content": f"{article['title']}\n\n{article['summary']}\n\n{article['content']}",
                        "source": f"{article['title']} ({article['source']})",
                        "date_added": get_current_timestamp(),
                        "metadata": metadata
                    })
                except Exception as e:
                    logger.error(f"Error processing article {article['id']}: {e}")
            
            cursor.close()
            conn.close()
            
            logger.info(f"Loaded {len(self.documents)} documents from database")
                
        except Exception as e:
            logger.error(f"Error loading documents from database: {e}")
    
    def sync_documents(self) -> None:
        """Resync documents metadata with vector store and database"""
        doc_count = self.vector_store.count_vectors()
        
        if doc_count == 0 and self.documents:
            logger.warning(f"Vector store is empty but {len(self.documents)} documents exist in metadata")
            
            all_langchain_docs = []
            
            # Re-add all documents to vector store
            for doc in self.documents:
                try:
                    # Split content into chunks
                    chunks = self.text_splitter.split_text(doc['content'])
                    
                    for i, chunk in enumerate(chunks):
                        chunk_metadata = {
                            "source": doc["source"],
                            "date_added": doc.get("date_added", get_current_timestamp()),
                            "doc_id": doc["id"],
                            "chunk_id": i,
                            **(doc.get("metadata", {}))
                        }
                        all_langchain_docs.append(Document(page_content=chunk, metadata=chunk_metadata))
                
                except Exception as e:
                    logger.error(f"Error preparing document {doc['id']} for re-indexing: {e}")
            
            # Batch add all documents
            if all_langchain_docs:
                try:
                    self.vector_store.add_documents(all_langchain_docs)
                    logger.info(f"Re-added {len(self.documents)} documents with {len(all_langchain_docs)} chunks")
                except Exception as e:
                    logger.error(f"Error re-adding documents to vector store: {e}")
                    
        else:
            logger.info(f"Vector store has {doc_count} vectors which seems consistent with document metadata")
    
    def get_all_documents(self) -> List[Dict]:
        """Return all documents metadata"""
        return self.documents