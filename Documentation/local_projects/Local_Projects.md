# Local Projects RAG System

## Overview

This document describes the Local Projects RAG (Retrieval-Augmented Generation) system that allows users to create and manage projects stored locally with LLM capabilities powered by Ollama.

## Architecture

```
┌─────────────────────────────────────────┐
│     Flask Web Application               │
│  (Admin UI + Chat Interface)            │
└────────────┬────────────────────────────┘
             │
    ┌────────┴─────────────────┐
    │                          │
    ▼                          ▼
┌─────────────────┐   ┌──────────────────┐
│ Google Projects │   │ Local Projects   │
│  (Google API)   │   │ (Local Storage)  │
└─────────────────┘   └────────┬─────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
              ┌──────────────┐    ┌──────────────┐
              │  ChromaDB    │    │ local_projects.json
              │(Vector Store)│    │(Metadata)
              └──────┬───────┘    └──────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
    ┌─────────────────────────────────┐
    │      Ollama (Local)             │
    ├─────────────────────────────────┤
    │ LLM: gemma3:4b                  │
    │ Embeddings: embeddinggemma      │
    └─────────────────────────────────┘
```

## Components

### 1. **Local Project Storage** (`src/local_project_storage.py`)

Manages local projects persisted to JSON file.

**Features:**
- Create local projects with unique IDs
- Track documents added to projects
- Delete projects
- List all local projects
- Stores metadata including creation timestamp

**File Location:** `configuration/local_projects.json`

**Data Structure:**
```json
{
  "local_20251205_143022_my_documents": {
    "id": "local_20251205_143022_my_documents",
    "display_name": "My Documents",
    "created_at": "2025-12-05T14:30:22.123456",
    "documents": [
      {
        "name": "document_name.pdf",
        "added_at": "2025-12-05T14:31:00.123456"
      }
    ]
  }
}
```

### 2. **Ollama Integration**

Uses Ollama to run LLM and embedding models locally.

**Models:**
- **LLM:** `gemma3:4b` (3.3 GB)
  - Fast, 4B parameter model suitable for local inference
  - Used for generating responses to queries
  
- **Embeddings:** `embeddinggemma:latest` (621 MB)
  - Generates embeddings for documents and queries
  - Used for semantic search in ChromaDB

**Setup Requirements:**
```bash
# Start Ollama service (in separate terminal)
ollama serve

# Models should be pre-downloaded
ollama list
# Should show:
# embeddinggemma:latest
# gemma3:4b
```

### 3. **Vector Database** (ChromaDB)

Stores document embeddings and enables semantic search.

**Features:**
- In-memory or persistent storage
- Efficient similarity search
- Integration with LLaMA Index

### 4. **RAG Framework** (LLaMA Index)

Orchestrates the RAG pipeline.

**Components:**
- `llama-index-llms-ollama` - Connects to Ollama LLM
- `llama-index-vector-stores-chroma` - Uses ChromaDB for storage
- `llama-index-embeddings-ollama` - Uses Ollama embeddings

## Frontend Integration

### Create Local Project

**Screen:** Admin Dashboard → Create New Project
**Steps:**
1. Click "New" button
2. Select Storage Type → "Locally"
3. Enter Project Name
4. Click "Create"

**Result:** Project saved to `local_projects.json` and appears in project list

### Project List Display

Both Google and Local projects are displayed in a unified interface:
- Local projects have ID starting with `local_`
- Can be selected, viewed, and deleted like Google projects

### Document Management

Local projects can have documents tracked:
- Upload documents
- Track document metadata
- Delete documents

### Chat Interface

When a local project is selected:
- Documents are indexed in ChromaDB
- Queries are embedded using `embeddinggemma`
- Semantic search retrieves relevant documents
- `gemma3:4b` generates contextual responses

## API Endpoints

### Projects

```
GET /api/projects              # List all projects (Google + Local)
POST /api/projects             # Create new project (with storage_type)
DELETE /api/projects/{id}      # Delete project (auto-detects local vs Google)
```

### Documents (for Local Projects)

```
GET /api/projects/{id}/documents      # List documents in project
POST /api/projects/{id}/documents     # Upload document
DELETE /api/documents/{id}            # Delete document
```

### Chat

```
POST /api/chat                 # Ask question to project
```

## File Structure

```
/Users/chrys/Projects/Google File Search Dashboard/
├── src/
│   ├── app.py                           # Flask main app
│   ├── API.py                           # FastAPI (exposed at /rag-api/)
│   ├── google_file_search.py            # Google File Search integration
│   ├── local_project_storage.py         # Local project management (NEW)
│   ├── prompt_storage.py                # Prompt management
│   └── configuration/
│       ├── prompts.json                 # Project prompts
│       ├── local_projects.json          # Local projects (NEW)
│       └── rag/                         # RAG engine files (TODO)
├── configuration/
│   ├── prompts.json                     # Synced from src/configuration/
│   └── local_projects.json              # Synced from src/configuration/
├── templates/
│   ├── admin.html                       # Admin dashboard
│   ├── chat.html                        # Chat interface
│   └── partials/
│       ├── project_list.html            # Project list (supports local + Google)
│       └── ...
└── requirements.txt                     # Python dependencies (includes RAG packages)
```

## Implementation Status

### ✅ Completed
- Local project storage system
- Admin UI with storage type selector
- Combined project list (Google + Local)
- Project creation, listing, deletion
- Configuration file management

### 🚧 In Progress
- RAG pipeline implementation
- Document embedding and indexing
- Query processing with ChromaDB
- Local chat functionality

### 📋 TODO
- Create `src/local_rag.py` - RAG engine implementation
- Integrate Ollama LLM and embeddings
- Implement document chunking and indexing
- Add document upload handler for local projects
- Implement semantic search queries
- Add response generation for local projects

## Usage

### 1. Start Ollama Service
```bash
ollama serve
```

### 2. Start Flask Application
```bash
cd /Users/chrys/Projects/Google File Search Dashboard
source .venv/bin/activate
python src/app.py
```

### 3. Access Web Interface
```
http://localhost:5000
```

### 4. Create Local Project
1. Click "New" button
2. Select "Locally" as storage type
3. Enter project name
4. Project appears in the list

### 5. Upload Documents (When Implemented)
- Select local project
- Upload PDF or text files
- Documents are embedded and indexed in ChromaDB

### 6. Chat with Documents (When Implemented)
- Ask questions about project documents
- System retrieves relevant docs using ChromaDB
- `gemma3:4b` generates contextual answers
- Responses powered by locally running models

## Configuration

### Ollama Models
- Can be changed by modifying model names in RAG implementation
- Models must be available in Ollama: `ollama pull <model-name>`

### ChromaDB
- Default: In-memory storage (ephemeral)
- Optional: Configure persistent storage path

### LLM Parameters
- Temperature: Controls randomness of responses
- Max tokens: Limits response length
- Top-p, Top-k: Sampling parameters

## Performance Considerations

- **Model Size:** `gemma3:4b` is optimized for local inference (~4GB memory)
- **Embedding Speed:** `embeddinggemma` processes documents efficiently
- **ChromaDB:** Fast similarity search even with large document collections
- **Response Time:** Depends on document size and query complexity

## Future Enhancements

- [ ] Support for more local LLMs (Mistral, Llama 2, etc.)
- [ ] Hybrid search (keyword + semantic)
- [ ] Document preprocessing pipeline
- [ ] Fine-tuning support
- [ ] Multi-document comparison
- [ ] Batch document processing
- [ ] Export/import project data
- [ ] Web UI for document management

## Dependencies

See `requirements.txt` for complete list. Key packages:
- `chromadb` - Vector database
- `llama-index` - RAG framework
- `llama-index-llms-ollama` - Ollama LLM integration
- `llama-index-vector-stores-chroma` - ChromaDB integration
- `llama-index-embeddings-ollama` - Ollama embeddings
- `ollama` - Ollama Python client
- `sentence-transformers` - Local embeddings (backup)

## Troubleshooting

### Ollama Not Running
```
Error: Connection refused
Solution: Start Ollama with: ollama serve
```

### Models Not Found
```
Error: Model not found
Solution: Download models with: ollama pull gemma3:4b
```

### Out of Memory
```
Error: CUDA out of memory
Solution: Use smaller model or reduce batch size
```

### ChromaDB Connection Issues
```
Error: Cannot connect to database
Solution: Check ChromaDB persistence path and permissions
```

## References

- [Ollama Documentation](https://ollama.ai)
- [LLaMA Index Documentation](https://docs.llamaindex.ai)
- [ChromaDB Documentation](https://docs.trychroma.com)
- [Gemma Models](https://ai.google.dev/gemma)
