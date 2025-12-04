from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import os
import sys
import markdown
from werkzeug.utils import secure_filename
import dotenv
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Add current directory to path to import google_file_search from src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import google_file_search as gfs
from prompt_storage import get_prompt_storage

# Load environment variables from parent directory
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
dotenv.load_dotenv(env_path)

# Basic Auth Setup
security = HTTPBasic()

# Load users from .env file
def load_valid_users():
    """Load valid users from environment variable"""
    users_str = os.getenv("API_USERS")
    if not users_str:
        raise ValueError("API_USERS environment variable not set in .env file")
    
    users_dict = {}
    for user_pair in users_str.split(","):
        if ":" in user_pair:
            username, password = user_pair.strip().split(":", 1)
            users_dict[username.strip()] = password.strip()
    
    if not users_dict:
        raise ValueError("No valid users found in API_USERS environment variable")
    
    return users_dict

VALID_USERS = load_valid_users()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify basic auth credentials"""
    username = credentials.username
    password = credentials.password
    
    if username not in VALID_USERS or VALID_USERS[username] != password:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return username

# Initialize FastAPI app
app = FastAPI(title="Google File Search API", description="API for managing file search stores and chat functionality")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add middleware to handle X-Forwarded-* headers
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["fasolaki.com", "www.fasolaki.com"])

# In production, the API should be aware of the /rag-api prefix
# This is handled by nginx stripping it, so no changes needed here

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Initialize prompt storage
prompt_storage = get_prompt_storage()

# Pydantic models
class ProjectCreateRequest(BaseModel):
    display_name: str

class ChatRequest(BaseModel):
    store_id: str
    query: str
    system_prompt: str = None

class ChatResponse(BaseModel):
    user_message: str
    bot_response: str
    bot_response_html: str

class ProjectResponse(BaseModel):
    name: str
    display_name: str
    create_time: str

class DocumentResponse(BaseModel):
    name: str
    display_name: str
    state: str

# Health check
@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "healthy"}

# --- Projects (Stores) Endpoints ---

@app.get("/api/projects", response_model=list)
def list_projects(username: str = Depends(verify_credentials)):
    """List all file search stores"""
    try:
        stores = gfs.list_all_file_search_stores()
        return [
            {
                "name": store.name,
                "display_name": store.display_name,
                "create_time": str(store.create_time)
            }
            for store in stores
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects", response_model=dict)
def create_project(request: ProjectCreateRequest, username: str = Depends(verify_credentials)):
    """Create a new file search store"""
    try:
        if not request.display_name:
            raise HTTPException(status_code=400, detail="display_name is required")
        
        store_id = gfs.create_new_file_search_store(request.display_name)
        
        if not store_id:
            raise HTTPException(status_code=500, detail="Failed to create store")
        
        return {
            "status": "success",
            "store_id": store_id,
            "display_name": request.display_name
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Documents Endpoints (must come before delete_project) ---

@app.get("/api/projects/{store_id:path}/documents", response_model=list)
def list_documents(store_id: str, username: str = Depends(verify_credentials)):
    """List all documents in a store"""
    try:
        documents = gfs.list_documents_in_store(store_id)
        return [
            {
                "name": doc.name,
                "display_name": doc.display_name,
                "state": str(doc.state) if doc.state else "UNKNOWN"
            }
            for doc in documents
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects/{store_id:path}/documents")
def upload_document(store_id: str, file: UploadFile = File(...), username: str = Depends(verify_credentials)):
    """Upload a document to a store"""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file selected")
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Save uploaded file
        with open(filepath, "wb") as f:
            f.write(file.file.read())
        
        try:
            # Add to store
            document_id = gfs.add_document_to_store(store_id, filepath)
            
            if not document_id:
                raise HTTPException(status_code=500, detail="Failed to add document to store")
            
            return {
                "status": "success",
                "document_id": document_id,
                "filename": filename
            }
        finally:
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/documents/{document_id:path}")
def delete_document(document_id: str, username: str = Depends(verify_credentials)):
    """Delete a document from a store"""
    try:
        # document_id format: fileSearchStores/{store_id}/documents/{doc_id}
        # Extract store_id
        parts = document_id.split('/')
        if len(parts) < 2:
            raise HTTPException(status_code=400, detail="Invalid document_id format")
        
        store_id = f"{parts[0]}/{parts[1]}"
        
        gfs.delete_document_from_store(document_id)
        
        return {
            "status": "success",
            "message": "Document deleted",
            "store_id": store_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/projects/{store_id:path}")
def delete_project(store_id: str, username: str = Depends(verify_credentials)):
    """Delete a file search store"""
    try:
        gfs.delete_file_search_store(store_id)
        # Clean up associated prompt if it exists
        prompt_storage.delete_prompt(store_id)
        return {"status": "success", "message": f"Store {store_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Prompt Endpoints ---

@app.get("/api/projects/{store_id:path}/prompt")
def get_project_prompt(store_id: str, username: str = Depends(verify_credentials)):
    """Get custom prompt for a project"""
    try:
        prompt = prompt_storage.get_prompt(store_id)
        return {"prompt": prompt or ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects/{store_id:path}/prompt")
def set_project_prompt(store_id: str, request: dict, username: str = Depends(verify_credentials)):
    """Set custom prompt for a project"""
    try:
        prompt = request.get("prompt", "")
        prompt_storage.set_prompt(store_id, prompt)
        return {"status": "success", "message": "Prompt saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Chat Endpoints ---

@app.post("/api/chat", response_model=ChatResponse)
def ask_question(request: ChatRequest, username: str = Depends(verify_credentials)):
    """Ask a question to a file search store"""
    try:
        if not request.store_id or not request.query:
            raise HTTPException(status_code=400, detail="store_id and query are required")
        
        # Use provided system_prompt or get from stored prompts
        system_prompt = request.system_prompt
        if not system_prompt:
            system_prompt = prompt_storage.get_prompt(request.store_id)
        
        print(f"[API] Query - Store: {request.store_id}, Prompt: {system_prompt[:50] if system_prompt else 'None'}...")
        
        # Generate answer with optional custom prompt
        answer_text = gfs.ask_store_question(
            request.store_id, 
            request.query, 
            system_prompt if system_prompt else None
        )
        
        # Convert markdown to HTML
        answer_html = markdown.markdown(answer_text)
        
        return ChatResponse(
            user_message=request.query,
            bot_response=answer_text,
            bot_response_html=answer_html
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Root endpoint
@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Google File Search API",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }

if __name__ == "__main__":
    try:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except ImportError:
        print("uvicorn not installed. Run: pip install uvicorn")
