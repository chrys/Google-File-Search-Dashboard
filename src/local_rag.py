import os
from typing import List, Optional, Dict
from datetime import datetime
import pypdf
from pathlib import Path
import json
import pickle

try:
    import faiss
    import numpy as np
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

try:
    from llama_index.core import Document, VectorStoreIndex
    from llama_index.embeddings.ollama import OllamaEmbedding
    from llama_index.llms.ollama import Ollama
    from llama_index.core.node_parser import SimpleNodeParser
    LLAMAINDEX_AVAILABLE = True
except ImportError:
    LLAMAINDEX_AVAILABLE = False


class LocalRAGEngine:
    """Handles RAG operations for local projects using Ollama and FAISS"""
    
    def __init__(self, project_id: str, data_dir: str = None):
        """
        Initialize RAG engine for a project
        
        Args:
            project_id: The local project ID
            data_dir: Directory for FAISS index storage. Defaults to project root/rag_data
        """
        if not LLAMAINDEX_AVAILABLE or not FAISS_AVAILABLE:
            raise ImportError(
                "LocalRAGEngine requires faiss and llama-index packages. "
                "Install with: pip install faiss-cpu llama-index llama-index-llms-ollama "
                "llama-index-embeddings-ollama"
            )
        
        self.project_id = project_id
        
        if data_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(project_root, 'rag_data', project_id)
        
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        
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
        
        # Initialize FAISS index with IndexIDMap for efficient deletion
        self.index_path = os.path.join(self.data_dir, "faiss_index.bin")
        self.metadata_path = os.path.join(self.data_dir, "metadata.json")
        
        self.documents = {}  # Store document content by ID
        self.metadata = {}   # Store metadata
        self.embedding_dim = None  # Will be determined from first embedding
        self.index = None
        self.id_counter = 0  # Counter for assigning document IDs
        
        # Load existing index if it exists
        self._load_index()
        
        print(f"✅ RAG Engine initialized for project: {project_id}")
    
    def _load_index(self):
        """Load FAISS IndexIDMap from disk if it exists"""
        if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
            try:
                print(f"📂 Loading FAISS index from disk...")
                # Load metadata first to get ID counter and data
                with open(self.metadata_path, 'r') as f:
                    data = json.load(f)
                    self.metadata = {int(k): v for k, v in data.get('metadata', {}).items()}
                    self.documents = {int(k): v for k, v in data.get('documents', {}).items()}
                    # Use stored embedding_dim if available, otherwise will be set on first embedding
                    stored_dim = data.get('embedding_dim')
                    if stored_dim:
                        self.embedding_dim = stored_dim
                        print(f"📂 Loaded embedding_dim from metadata: {self.embedding_dim}")
                    self.id_counter = data.get('id_counter', max(self.metadata.keys()) + 1 if self.metadata else 0)
                print(f"📂 Loaded metadata with {len(self.metadata)} documents (IDs: {sorted(self.metadata.keys())})")
                
                # Load the FAISS index
                loaded_index = faiss.read_index(self.index_path)
                print(f"📂 Loaded raw index type: {type(loaded_index).__name__} with {loaded_index.ntotal} vectors")
                
                # If it's already an IndexIDMap, use it directly; otherwise, we have a problem
                if isinstance(loaded_index, faiss.IndexIDMap):
                    self.index = loaded_index
                    print(f"✅ Index is already IndexIDMap with IDs intact")
                else:
                    # This shouldn't happen if we saved correctly, but warn user
                    print(f"⚠️ WARNING: Loaded index is not IndexIDMap! Type: {type(loaded_index).__name__}")
                    print(f"⚠️ This indicates the save didn't preserve the IndexIDMap wrapper!")
                    # Try to rewrap it, but this will lose the original IDs
                    self.index = faiss.IndexIDMap(loaded_index)
                    print(f"⚠️ Rewrapped as IndexIDMap, but IDs may be lost. Document count: {self.index.ntotal}")
                
                print(f"✅ Loaded FAISS IndexIDMap with {self.index.ntotal} documents")
                
                # Sanity check: index vector count should match metadata count
                if self.index.ntotal != len(self.metadata):
                    print(f"⚠️ MISMATCH: Index has {self.index.ntotal} vectors but metadata has {len(self.metadata)} documents!")
                    print(f"⚠️ This could cause inconsistency issues!")
                    
            except Exception as e:
                print(f"⚠️ Error loading index: {e}")
                import traceback
                traceback.print_exc()
                self.index = None
        
        if self.index is None:
            # Create new IndexIDMap with FlatL2
            # Use a temporary dimension; it will be set to actual dimension on first indexing
            temp_dim = self.embedding_dim if self.embedding_dim else 768  # Default to 768 (Ollama embeddinggemma dimension)
            quantizer = faiss.IndexFlatL2(temp_dim)
            self.index = faiss.IndexIDMap(quantizer)
            self.embedding_dim = temp_dim  # Set embedding_dim now
            self.id_counter = 0
            print(f"📊 Created new FAISS IndexIDMap (dimension: {self.embedding_dim})")
    
    def _save_index(self):
        """Save FAISS IndexIDMap and metadata to disk"""
        try:
            if self.index is not None:
                print(f"💾 Saving FAISS index with {self.index.ntotal} documents...")
                # For IndexIDMap, we need to save the wrapper itself, not the base index
                # Make sure we're saving the complete IndexIDMap with IDs intact
                faiss.write_index(self.index, self.index_path)
                print(f"💾 Saved FAISS IndexIDMap to {self.index_path}")
                
                # Verify the save by reading it back
                try:
                    test_index = faiss.read_index(self.index_path)
                    print(f"✅ Verified save: index has {test_index.ntotal} vectors")
                except Exception as ve:
                    print(f"⚠️ Warning: Could not verify index save: {ve}")
                
                # Save metadata with ID counter
                with open(self.metadata_path, 'w') as f:
                    json.dump({
                        'metadata': {str(k): v for k, v in self.metadata.items()},
                        'documents': {str(k): v for k, v in self.documents.items()},
                        'embedding_dim': self.embedding_dim,
                        'id_counter': self.id_counter
                    }, f, indent=2)
                print(f"💾 Saved metadata with {len(self.metadata)} documents to {self.metadata_path}")
        except Exception as e:
            print(f"❌ Error saving index: {e}")
            import traceback
            traceback.print_exc()
    
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
        Index a document by extracting text and creating embeddings in FAISS IndexIDMap
        
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
            embedding_array = np.array([embedding], dtype=np.float32)
            
            # Validate embedding dimension
            embedding_dim = len(embedding)
            print(f"📊 Embedding dimension: {embedding_dim}, Index dimension: {self.embedding_dim}")
            
            # Initialize FAISS index if not already done
            if self.index is None:
                self.embedding_dim = embedding_dim
                quantizer = faiss.IndexFlatL2(self.embedding_dim)
                self.index = faiss.IndexIDMap(quantizer)
                print(f"📊 Created FAISS IndexIDMap with dimension {self.embedding_dim}")
            elif embedding_dim != self.embedding_dim:
                # Dimension mismatch - this shouldn't happen but let's handle it
                print(f"⚠️ Embedding dimension mismatch! Expected {self.embedding_dim}, got {embedding_dim}")
                print(f"⚠️ Recreating index with correct dimension...")
                self.embedding_dim = embedding_dim
                quantizer = faiss.IndexFlatL2(self.embedding_dim)
                self.index = faiss.IndexIDMap(quantizer)
                self.id_counter = 0
                self.metadata = {}
                self.documents = {}
            
            # Assign document ID and add to FAISS with ID
            doc_id = self.id_counter
            self.id_counter += 1
            doc_id_array = np.array([doc_id], dtype=np.int64)
            self.index.add_with_ids(embedding_array, doc_id_array)
            
            # Store metadata and document
            self.metadata[doc_id] = {
                "document_name": document_name,
                "file_path": file_path,
                "indexed_at": datetime.now().isoformat(),
                "project_id": self.project_id
            }
            self.documents[doc_id] = text
            
            print(f"✅ Indexed document: {document_name} (ID: {doc_id})")
            print(f"📊 Index size: {self.index.ntotal} documents")
            
            # Save to disk
            self._save_index()
            
            return True
            
        except Exception as e:
            print(f"❌ Error indexing document: {e}")
            import traceback
            traceback.print_exc()
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
            # Check if index exists and has documents
            if self.index is None or self.index.ntotal == 0:
                print(f"⚠️ [QUERY] No documents in index")
                return {
                    "response": "I don't have any indexed documents to answer this question. Please upload documents first.",
                    "source_nodes": []
                }
            
            # Embed the query
            query_embedding = self.embed_model.get_text_embedding(query_text)
            query_array = np.array([query_embedding], dtype=np.float32)
            
            # Determine actual k value
            actual_k = min(top_k, self.index.ntotal)
            print(f"📊 [QUERY] Searching {actual_k} results (top_k={top_k}, available={self.index.ntotal})")
            
            # Query FAISS
            distances, indices = self.index.search(query_array, actual_k)
            
            print(f"📊 [QUERY] FAISS returned {len(indices[0])} results")
            
            # Extract documents and create context
            source_docs = []
            context_text = ""
            
            for i, doc_id in enumerate(indices[0]):
                if doc_id >= 0:  # -1 means no result found
                    if doc_id in self.documents:
                        metadata = self.metadata.get(doc_id, {})
                        doc_text = self.documents[doc_id]
                        distance = float(distances[0][i])
                        
                        source_docs.append({
                            "document": metadata.get("document_name", f"Doc {doc_id}"),
                            "score": distance
                        })
                        context_text += f"\n---\nDocument: {metadata.get('document_name')}\n{doc_text[:1000]}\n"  # Limit context
            
            print(f"📊 [QUERY] Found {len(source_docs)} source documents: {[s['document'] for s in source_docs]}")
            
            # Generate response using LLM
            if len(source_docs) == 0:
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
            return {
                "project_id": self.project_id,
                "index_name": "FAISS",
                "document_count": self.index.ntotal if self.index else 0,
                "data_dir": self.data_dir
            }
        except Exception as e:
            print(f"⚠️ Error getting index info: {e}")
            return {
                "project_id": self.project_id,
                "index_name": "FAISS",
                "document_count": 0,
                "data_dir": self.data_dir
            }
    
    def delete_document(self, document_name: str) -> bool:
        """Delete a document from FAISS IndexIDMap by document name"""
        try:
            print(f"📊 Attempting to delete: '{document_name}'")
            
            # Find the document ID by name
            doc_id_to_delete = None
            for doc_id, meta in self.metadata.items():
                if meta.get("document_name") == document_name:
                    doc_id_to_delete = doc_id
                    break
            
            if doc_id_to_delete is not None:
                # Remove from metadata and documents first
                del self.metadata[doc_id_to_delete]
                del self.documents[doc_id_to_delete]
                
                print(f"✅ Deleted document: {document_name}")
                print(f"📊 Remaining documents: {len(self.metadata)}")
                
                # Rebuild the FAISS index with remaining documents
                # This ensures embeddings are actually removed (remove_ids can leave orphaned vectors)
                if len(self.metadata) > 0:
                    print(f"🔄 Rebuilding FAISS index with remaining documents...")
                    embeddings_list = []
                    id_list = []
                    
                    # Get embeddings for all remaining documents
                    for doc_id in sorted(self.metadata.keys()):
                        text = self.documents[doc_id]
                        embedding = self.embed_model.get_text_embedding(text)
                        embeddings_list.append(embedding)
                        id_list.append(doc_id)
                    
                    # Create new index with remaining documents
                    embeddings_array = np.array(embeddings_list, dtype=np.float32)
                    id_array = np.array(id_list, dtype=np.int64)
                    
                    quantizer = faiss.IndexFlatL2(self.embedding_dim)
                    self.index = faiss.IndexIDMap(quantizer)
                    self.index.add_with_ids(embeddings_array, id_array)
                    
                    print(f"✅ Rebuilt FAISS index with {len(self.metadata)} documents")
                else:
                    # No documents left - create empty index
                    print(f"🔄 Clearing FAISS index (no documents left)...")
                    quantizer = faiss.IndexFlatL2(self.embedding_dim)
                    self.index = faiss.IndexIDMap(quantizer)
                    print(f"✅ FAISS index cleared")
                
                self._save_index()
                return True
            else:
                print(f"⚠️ Document not found: {document_name}")
                return False
        except Exception as e:
            print(f"❌ Error deleting document: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def clear_collection(self) -> bool:
        """Clear all embeddings from the index"""
        try:
            self.index = None
            self.metadata = {}
            self.documents = {}
            
            # Delete index files
            if os.path.exists(self.index_path):
                os.remove(self.index_path)
            if os.path.exists(self.metadata_path):
                os.remove(self.metadata_path)
            
            print(f"✅ Cleared FAISS index for project: {self.project_id}")
            return True
        except Exception as e:
            print(f"❌ Error clearing index: {e}")
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
