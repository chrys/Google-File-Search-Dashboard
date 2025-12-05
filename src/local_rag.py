import os
from typing import List, Optional
from datetime import datetime
import pypdf
from pathlib import Path

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    from llama_index.core import Document, VectorStoreIndex
    from llama_index.embeddings.ollama import OllamaEmbedding
    from llama_index.llms.ollama import Ollama
    from llama_index.core.node_parser import SimpleNodeParser
    LLAMAINDEX_AVAILABLE = True
except ImportError:
    LLAMAINDEX_AVAILABLE = False


class LocalRAGEngine:
    """Handles RAG operations for local projects using Ollama and ChromaDB"""
    
    def __init__(self, project_id: str, data_dir: str = None):
        """
        Initialize RAG engine for a project
        
        Args:
            project_id: The local project ID
            data_dir: Directory for ChromaDB storage. Defaults to project root/rag_data
        """
        if not LLAMAINDEX_AVAILABLE or not CHROMADB_AVAILABLE:
            raise ImportError(
                "LocalRAGEngine requires chromadb and llama-index packages. "
                "Install with: pip install chromadb llama-index llama-index-llms-ollama "
                "llama-index-embeddings-ollama"
            )
        
        self.project_id = project_id
        
        if data_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(project_root, 'rag_data', project_id)
        
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize ChromaDB with persistent storage
        self.chroma_client = chromadb.HttpClient() if self._is_chroma_server_running() else self._init_local_chroma()
        self.collection_name = f"project_{project_id.replace('-', '_').replace(':', '_')}"
        
        # Get or create collection
        # CRITICAL: Use get_or_create_collection to ensure collection exists and persists
        try:
            self.chroma_collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"📊 [INIT] Opened collection '{self.collection_name}' with {self.chroma_collection.count()} documents")
        except Exception as e:
            print(f"❌ [INIT] Error opening collection: {e}")
            raise
        
        # Initialize embeddings model
        self.embed_model = OllamaEmbedding(
            model_name="embeddinggemma",
            base_url="http://localhost:11434"
        )
        
        # Initialize LLM
        self.llm = Ollama(
            model="gemma3:4b",
            base_url="http://localhost:11434",
            temperature=0.7
        )
        
        # We'll manually handle embedding and storage since we removed ChromaVectorStore
        print(f"✅ RAG Engine initialized for project: {project_id}")
    
    def _is_chroma_server_running(self) -> bool:
        """Check if ChromaDB server is running"""
        try:
            import requests
            requests.get("http://localhost:8000/api/v1", timeout=2)
            return True
        except:
            return False
    
    def _init_local_chroma(self):
        """Initialize local ChromaDB client with persistent storage"""
        if chromadb is None:
            raise ImportError("chromadb is not installed")
        
        try:
            # For chromadb 0.3.x, use duckdb+parquet for persistent storage
            persist_dir = os.path.join(self.data_dir, ".chroma")
            os.makedirs(persist_dir, exist_ok=True)
            print(f"📊 Initializing ChromaDB with persistent storage at: {persist_dir}")
            
            client = chromadb.Client(
                settings=chromadb.config.Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=persist_dir,
                    anonymized_telemetry=False
                )
            )
            print("✅ ChromaDB persistent storage initialized successfully")
            return client
        except Exception as e:
            print(f"⚠️ Error initializing persistent ChromaDB: {e}")
            print("⚠️ Falling back to ephemeral client - data will NOT persist between app restarts")
            return chromadb.Client()
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text()
            print(f"✅ Extracted text from PDF: {len(text)} characters")
            return text
        except Exception as e:
            print(f"❌ Error extracting PDF: {e}")
            raise
    
    def extract_text_from_file(self, file_path: str) -> str:
        """Extract text from various file formats"""
        file_ext = Path(file_path).suffix.lower()
        
        try:
            if file_ext == '.pdf':
                return self.extract_text_from_pdf(file_path)
            elif file_ext in ['.txt', '.md']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                print(f"✅ Extracted text from {file_ext}: {len(text)} characters")
                return text
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")
        except Exception as e:
            print(f"❌ Error extracting text: {e}")
            raise
    
    def index_document(self, file_path: str, document_name: str) -> bool:
        """
        Index a document by extracting text and creating embeddings in ChromaDB
        
        Args:
            file_path: Path to the document file
            document_name: Name/ID for the document
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract text from file
            text = self.extract_text_from_file(file_path)
            
            if not text:
                print(f"⚠️ No text extracted from document: {document_name}")
                return False
            
            # Create embedding using Ollama
            embedding = self.embed_model.get_text_embedding(text)
            
            # Get count before adding
            count_before = self.chroma_collection.count()
            
            # Store in ChromaDB
            self.chroma_collection.add(
                ids=[document_name],
                embeddings=[embedding],
                metadatas=[{
                    "document_name": document_name,
                    "file_path": file_path,
                    "indexed_at": datetime.now().isoformat(),
                    "project_id": self.project_id
                }],
                documents=[text]
            )
            
            # Get count after adding
            count_after = self.chroma_collection.count()
            print(f"✅ Indexed document: {document_name}")
            print(f"📊 Collection size: {count_before} → {count_after}")
            
            # Persist the changes to disk
            try:
                if hasattr(self.chroma_client, 'persist'):
                    self.chroma_client.persist()
                    print(f"💾 Persisted ChromaDB to disk")
            except Exception as e:
                print(f"⚠️ Could not persist ChromaDB: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error indexing document: {e}")
            raise
    
    def query(self, query_text: str, top_k: int = 3) -> dict:
        """
        Query the indexed documents
        
        Args:
            query_text: The query string
            top_k: Number of relevant documents to retrieve
            
        Returns:
            Dictionary with query response and source documents
        """
        try:
            # Check collection count first
            collection_count = self.chroma_collection.count()
            print(f"📊 [QUERY] Collection has {collection_count} documents")
            
            # List all document IDs
            all_docs = self.chroma_collection.get()
            all_ids = all_docs.get('ids', [])
            print(f"📊 [QUERY] Document IDs in collection: {all_ids}")
            
            if collection_count == 0:
                print(f"⚠️ [QUERY] No documents in collection, returning empty result")
                return {
                    "response": "I don't have any indexed documents to answer this question. Please upload documents first.",
                    "source_nodes": []
                }
            
            # Embed the query
            query_embedding = self.embed_model.get_text_embedding(query_text)
            
            # Determine actual k value
            actual_k = min(top_k, collection_count)
            print(f"📊 [QUERY] Requesting {actual_k} results (top_k={top_k}, available={collection_count})")
            
            # Query ChromaDB
            results = self.chroma_collection.query(
                query_embeddings=[query_embedding],
                n_results=actual_k
            )
            
            print(f"📊 [QUERY] ChromaDB returned {len(results.get('documents', [[]])[0])} results")
            
            # Extract documents and create context
            source_docs = []
            context_text = ""
            
            if results['documents'] and len(results['documents']) > 0:
                for i, doc in enumerate(results['documents'][0]):
                    source_docs.append({
                        "document": results['metadatas'][0][i].get("document_name"),
                        "score": float(results['distances'][0][i]) if results['distances'] else 0
                    })
                    context_text += f"\n---\nDocument: {results['metadatas'][0][i].get('document_name')}\n{doc}\n"
            
            print(f"📊 [QUERY] Found {len(source_docs)} source documents: {[s['document'] for s in source_docs]}")
            
            # Generate response using LLM
            if len(source_docs) == 0:
                # No documents found - tell the LLM explicitly not to answer from general knowledge
                response_text = "I don't have any indexed documents to answer this question. Please upload documents first."
            else:
                prompt = f"Based on the following documents, answer this question: {query_text}\n\nDocuments:{context_text}"
                response_text = self.llm.complete(prompt).text if hasattr(self.llm, 'complete') else f"No relevant documents found for: {query_text}"
            
            return {
                "response": response_text,
                "source_nodes": source_docs
            }
        except Exception as e:
            print(f"❌ Error querying documents: {e}")
            raise
    
    def get_collection_info(self) -> dict:
        """Get information about the indexed documents"""
        try:
            collection = self.chroma_client.get_collection(self.collection_name)
            count = collection.count()
            
            return {
                "project_id": self.project_id,
                "collection_name": self.collection_name,
                "document_count": count,
                "data_dir": self.data_dir
            }
        except Exception as e:
            print(f"⚠️ Error getting collection info: {e}")
            return {
                "project_id": self.project_id,
                "collection_name": self.collection_name,
                "document_count": 0,
                "data_dir": self.data_dir
            }
    
    def delete_document(self, document_name: str) -> bool:
        """Delete a document's embeddings from ChromaDB by document name/ID"""
        try:
            # Get collection count before deletion
            count_before = self.chroma_collection.count()
            print(f"📊 Collection count BEFORE deletion: {count_before}")
            
            # List all document IDs in collection
            all_docs = self.chroma_collection.get()
            print(f"📊 Document IDs in collection: {all_docs.get('ids', [])}")
            print(f"📊 Attempting to delete: '{document_name}'")
            
            # Delete the document from ChromaDB by ID (which is the document name)
            self.chroma_collection.delete(ids=[document_name])
            
            # Get collection count after deletion
            count_after = self.chroma_collection.count()
            print(f"📊 Collection count AFTER deletion: {count_after}")
            print(f"✅ Deleted embeddings for document: {document_name}")
            
            # Verify deletion by checking remaining docs
            remaining_docs = self.chroma_collection.get()
            print(f"📊 Remaining document IDs: {remaining_docs.get('ids', [])}")
            
            # Persist the changes to disk
            try:
                if hasattr(self.chroma_client, 'persist'):
                    self.chroma_client.persist()
                    print(f"💾 Persisted ChromaDB to disk after deletion")
            except Exception as e:
                print(f"⚠️ Could not persist ChromaDB after deletion: {e}")
            
            # Verify deletion by trying to get the document
            try:
                result = self.chroma_collection.get(ids=[document_name])
                if result['ids']:
                    print(f"⚠️ WARNING: Document still exists after deletion attempt!")
                    return False
            except:
                pass
            
            return True
        except Exception as e:
            print(f"❌ Error deleting document embeddings: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def clear_collection(self) -> bool:
        """Clear all embeddings from the collection"""
        try:
            self.chroma_client.delete_collection(self.collection_name)
            # Recreate empty collection
            self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"✅ Cleared collection: {self.collection_name}")
            return True
        except Exception as e:
            print(f"❌ Error clearing collection: {e}")
            return False


# Global RAG engines cache - DISABLED for now due to stale data issues
# Each request will create a fresh instance to load current data from disk
_rag_engines = {}


def get_rag_engine(project_id: str) -> LocalRAGEngine:
    """Get or create a RAG engine for a project
    
    NOTE: We create a fresh instance each time instead of caching
    to ensure we always load the latest data from disk.
    The underlying ChromaDB with duckdb+parquet handles persistence.
    """
    # For now, don't use caching - create fresh instance each time
    # This ensures we always load the latest data from disk
    engine = LocalRAGEngine(project_id)
    print(f"🔄 Created fresh RAG engine for {project_id} (caching disabled)")
    return engine

def get_rag_engine_cached(project_id: str) -> LocalRAGEngine:
    """Get or reuse a cached RAG engine for a project"""
    if project_id not in _rag_engines:
        _rag_engines[project_id] = LocalRAGEngine(project_id)
    return _rag_engines[project_id]
