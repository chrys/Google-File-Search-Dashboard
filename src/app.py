import os
import sys
import time
import markdown
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix

# Add current directory to path to import google_file_search from src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import google_file_search as gfs
from prompt_storage import get_prompt_storage
from local_project_storage import get_local_project_storage

# Add parent directory to path for config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_config

# Try to import local RAG, but don't fail if dependencies are missing
try:
    from local_rag import get_rag_engine
    LOCAL_RAG_AVAILABLE = True
except ImportError:
    LOCAL_RAG_AVAILABLE = False
    print("⚠️  Local RAG features disabled - chromadb/llama-index dependencies not available")

# Setup template and static folders to point to parent directory
template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static')
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# Load configuration based on environment
env = os.getenv('FLASK_ENV', 'development')
config_class = get_config(env)
app.config.from_object(config_class)

# Validate production configuration at runtime if needed
if env == 'production' and hasattr(config_class, 'validate'):
    try:
        config_class.validate()
    except ValueError as e:
        print(f"⚠️  WARNING: Production configuration issue: {e}")
        print("   The app will still start, but ensure SECRET_KEY is set in production!")

# Set APPLICATION_ROOT for production (handles /rag prefix)
if env == 'production':
    app.config['APPLICATION_ROOT'] = '/rag'

# Handle reverse proxy headers (for /rag/ prefix behind nginx)
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,
    x_proto=1,
    x_host=1,
    x_prefix=1,
    x_port=1
)

# Context processor to provide url prefix for templates
@app.context_processor
def inject_url_prefix():
    """Inject URL prefix into all templates for proper URL generation"""
    url_prefix = app.config.get('APPLICATION_ROOT', '')
    # Ensure url_prefix doesn't end with slash for proper concatenation
    if url_prefix.endswith('/'):
        url_prefix = url_prefix[:-1]
    return dict(url_prefix=url_prefix)

# Setup CORS with environment-specific origins
if env == 'production':
    CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}})
else:
    CORS(app)

# Initialize prompt storage
prompt_storage = get_prompt_storage()

# Initialize local project storage
local_project_storage = get_local_project_storage()

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('base.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/chat')
def chat():
    return render_template('chat.html')

# --- API Routes ---

# Projects (Stores)
@app.route('/api/projects', methods=['GET'])
def list_projects():
    # Get Google stores
    google_stores = gfs.list_all_file_search_stores()
    
    # Get local projects and convert to store-like objects
    local_projects = local_project_storage.list_projects()
    local_stores = [
        type('Store', (), {
            'name': project['id'],
            'display_name': project['display_name'],
            'create_time': project['created_at'],
            'storage_type': 'local'
        })()
        for project in local_projects
    ]
    
    # Combine both lists
    all_stores = google_stores + local_stores
    
    list_type = request.args.get('type', 'admin')
    
    if list_type == 'chat':
        return render_template('partials/chat_project_list.html', stores=all_stores)
    return render_template('partials/project_list.html', stores=all_stores)

@app.route('/api/projects', methods=['POST'])
def create_project():
    display_name = request.form.get('display_name')
    storage_type = request.form.get('storage_type', 'google')  # Default to Google
    
    print(f"[CREATE PROJECT] display_name={display_name}, storage_type={storage_type}")
    
    if display_name:
        if storage_type == 'local':
            # Create local project
            print(f"[CREATE PROJECT] Creating local project...")
            local_project_storage.create_project(display_name)
            print(f"[CREATE PROJECT] Local project created successfully")
        else:
            # Create Google File Search store
            print(f"[CREATE PROJECT] Creating Google store...")
            gfs.create_new_file_search_store(display_name)
    
    # Return updated combined list
    google_stores = gfs.list_all_file_search_stores()
    local_projects = local_project_storage.list_projects()
    local_stores = [
        type('Store', (), {
            'name': project['id'],
            'display_name': project['display_name'],
            'create_time': project['created_at'],
            'storage_type': 'local'
        })()
        for project in local_projects
    ]
    
    all_stores = google_stores + local_stores
    return render_template('partials/project_list.html', stores=all_stores)

@app.route('/api/projects/<path:store_id>', methods=['DELETE'])
def delete_project(store_id):
    # Check if it's a local project
    if store_id.startswith('local_'):
        local_project_storage.delete_project(store_id)
    else:
        # It's a Google store
        gfs.delete_file_search_store(store_id)
    
    # Return updated combined list
    google_stores = gfs.list_all_file_search_stores()
    local_projects = local_project_storage.list_projects()
    local_stores = [
        type('Store', (), {
            'name': project['id'],
            'display_name': project['display_name'],
            'create_time': project['created_at'],
            'storage_type': 'local'
        })()
        for project in local_projects
    ]
    
    all_stores = google_stores + local_stores
    return render_template('partials/project_list.html', stores=all_stores)

# Documents
@app.route('/api/projects/<path:store_id>/documents', methods=['GET'])
def list_documents(store_id):
    # Check if it's a local project
    if store_id.startswith('local_'):
        # Get local project documents
        local_projects = local_project_storage.list_projects()
        project = next((p for p in local_projects if p['id'] == store_id), None)
        
        if not project:
            return 'Project not found', 404
        
        documents = [
            {
                'name': doc_name,
                'display_name': doc_name,
                'mime_type': 'document',
                'indexed_at': doc_info.get('indexed_at') if isinstance(doc_info, dict) else None,
                'state': type('State', (), {'name': 'INDEXED'})()  # Mock state object for template compatibility
            }
            for doc_name, doc_info in (
                ((d, project['documents'].get(d)) if isinstance(project['documents'], dict) else (d, {}))
                for d in project.get('documents', []) if d
            )
        ]
        
        return render_template('partials/document_list.html', 
                             documents=documents, 
                             store_id=store_id, 
                             project_name=project['display_name'],
                             storage_type='local')
    else:
        # Google store documents
        documents = gfs.list_documents_in_store(store_id)
        
        project_name = "Project Documents"
        stores = gfs.list_all_file_search_stores()
        for store in stores:
            if store.name == store_id:
                project_name = store.display_name
                break
        
        return render_template('partials/document_list.html', 
                             documents=documents, 
                             store_id=store_id, 
                             project_name=project_name,
                             storage_type='google')

@app.route('/api/projects/<path:store_id>/documents', methods=['POST'])
def upload_document(store_id):
    """Upload and index a document for a project"""
    if 'file' not in request.files:
        return 'No file part', 400
    
    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400
    
    if not file:
        return 'Invalid file', 400
    
    filepath = None
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Check if it's a local project
        if store_id.startswith('local_'):
            print(f"[UPLOAD] Processing local project: {store_id}, file: {filename}")
            
            # Get RAG engine for this project
            # NOTE: Don't clear cache here - we want to reuse the same engine for consistency
            rag_engine = get_rag_engine(store_id)
            
            # Index the document (creates embeddings)
            success = rag_engine.index_document(filepath, filename)
            
            if success:
                # Add document metadata to local project storage
                local_project_storage.add_document(store_id, filename)
                print(f"[UPLOAD] ✅ Document indexed and stored: {filename}")
            else:
                print(f"[UPLOAD] ❌ Failed to index document: {filename}")
                return 'Failed to index document', 500
        else:
            # Google store document
            print(f"[UPLOAD] Processing Google store: {store_id}, file: {filename}")
            gfs.add_document_to_store(store_id, filepath)
            print(f"[UPLOAD] ✅ Document uploaded to Google store: {filename}")
        
        # Return updated document items
        local_projects = local_project_storage.list_projects()
        project = next((p for p in local_projects if p['id'] == store_id), None)
        
        if project:
            # Local project
            documents = [
                {
                    'name': doc_name,
                    'display_name': doc_name,
                    'mime_type': 'document',
                    'indexed_at': doc_info.get('indexed_at') if isinstance(doc_info, dict) else None,
                    'state': type('State', (), {'name': 'INDEXED'})()  # Mock state object for template compatibility
                }
                for doc_name, doc_info in (
                    ((d, project['documents'].get(d)) if isinstance(project['documents'], dict) else (d, {}))
                    for d in project.get('documents', []) if d
                )
            ]
        else:
            # Google store
            documents = gfs.list_documents_in_store(store_id)
        
        return render_template('partials/document_items.html', documents=documents)
        
    except Exception as e:
        print(f"[UPLOAD] ❌ Error uploading document: {e}")
        import traceback
        traceback.print_exc()
        return f'Error uploading document: {str(e)}', 500
    finally:
        # Clean up uploaded file
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
            print(f"[UPLOAD] Cleaned up temporary file: {filename}")
@app.route('/api/documents/<path:document_id>', methods=['DELETE'])
def delete_document(document_id):
    """Delete a document from either local or Google storage"""
    # document_id format for Google: fileSearchStores/{store_id}/documents/{doc_id}
    # For local projects, store_id will be in the query params
    
    # URL decode the document_id in case it contains special characters
    from urllib.parse import unquote
    document_id = unquote(document_id)
    
    # Check if this is a local document (store_id will be in the query params)
    store_id = request.args.get('store_id')
    
    print(f"[DELETE] Starting deletion process...")
    print(f"[DELETE]   document_id (decoded): {document_id}")
    print(f"[DELETE]   store_id: {store_id}")
    
    if store_id and store_id.startswith('local_'):
        # Local document deletion
        print(f"[DELETE] Deleting local document...")
        
        # Delete from FAISS FIRST, then from local storage
        # This ensures consistency: if FAISS deletion fails, we still have the document in local storage
        deletion_success = False
        try:
            from src.local_rag import get_rag_engine
            
            # Get RAG engine (fresh instance will load latest data from disk)
            rag_engine = get_rag_engine(store_id)
            
            # Delete the document from FAISS index
            # document_id is the filename, delete_document expects document_name
            success = rag_engine.delete_document(document_id)
            
            if success:
                print(f"[DELETE] ✅ Deleted from FAISS index: {document_id}")
                deletion_success = True
            else:
                print(f"[DELETE] ⚠️  Document not found in FAISS index: {document_id}")
                # Still treat as success if document wasn't in FAISS (already deleted or never indexed)
                deletion_success = True
            
        except Exception as e:
            print(f"[DELETE] ❌ Error deleting embeddings: {e}")
            import traceback
            traceback.print_exc()
            deletion_success = False
        
        # Only remove from local storage if FAISS deletion succeeded
        if deletion_success:
            local_project_storage.remove_document(store_id, document_id)
            print(f"[DELETE] ✅ Removed from local storage: {document_id}")
        else:
            print(f"[DELETE] ⚠️  Not removing from local storage due to FAISS deletion failure")
    else:
        # Google document deletion - parse store_id from document_id
        parts = document_id.split('/')
        if len(parts) >= 2:
            store_id = f"{parts[0]}/{parts[1]}"
        gfs.delete_document_from_store(document_id)
        print(f"[DELETE] Removed Google document: {document_id}")
    
    # Return updated document items
    if store_id and store_id.startswith('local_'):
        local_projects = local_project_storage.list_projects()
        project = next((p for p in local_projects if p['id'] == store_id), None)
        
        if project:
            documents = [
                {
                    'name': doc_name,
                    'display_name': doc_name,
                    'mime_type': 'document',
                    'indexed_at': doc_info.get('indexed_at') if isinstance(doc_info, dict) else None,
                    'state': type('State', (), {'name': 'INDEXED'})()  # Mock state object for template compatibility
                }
                for doc_name, doc_info in (
                    ((d, project['documents'].get(d)) if isinstance(project['documents'], dict) else (d, {}))
                    for d in project.get('documents', []) if d
                )
            ]
        else:
            documents = []
    else:
        documents = gfs.list_documents_in_store(store_id)
    
    return render_template('partials/document_items.html', documents=documents)

# Prompts
@app.route('/api/projects/<path:store_id>/prompt', methods=['GET', 'POST'])
def manage_project_prompt(store_id):
    """Get or set custom prompt for a project"""
    if request.method == 'POST':
        prompt = request.form.get('prompt', '')
        print(f"[PROMPT] Saving prompt for store {store_id}: {prompt[:50]}...")
        prompt_storage.set_prompt(store_id, prompt)
        return jsonify({'success': True, 'message': 'Prompt saved'})
    
    prompt = prompt_storage.get_prompt(store_id)
    print(f"[PROMPT] Loading prompt for store {store_id}: {prompt[:50] if prompt else 'None'}...")
    return jsonify({'prompt': prompt})

# Chat
@app.route('/api/chat', methods=['POST'])
def ask_question():
    import time
    
    store_id = request.form.get('store_id')
    query = request.form.get('query')
    system_prompt = request.form.get('system_prompt', '')  # Get prompt from frontend
    
    if not store_id or not query:
        return '', 400
    
    # Record start time
    start_time = time.time()
    app.logger.info(f'[CHAT] Query started at {start_time:.3f} - Store: {store_id} | Query: {query[:50]}...')
    
    try:
        source_nodes = []  # Initialize source nodes
        
        # Check if it's a local project
        if store_id.startswith('local_'):
            if not LOCAL_RAG_AVAILABLE:
                error_html = render_template('partials/chat_message.html', 
                                            message="Local RAG is not available. Please install chromadb and llama-index dependencies: pip install chromadb llama-index llama-index-llms-ollama llama-index-embeddings-ollama",
                                            sender='bot')
                return error_html, 400
            print(f"[CHAT] Processing local project: {store_id}")
            rag_engine = get_rag_engine(store_id)
            result = rag_engine.query(query, top_k=3)
            answer_text = result['response']
            source_nodes = result.get('source_nodes', [])
        else:
            # Google store
            print(f"[CHAT] Processing Google store: {store_id}")
            answer_text = gfs.ask_store_question(store_id, query, system_prompt if system_prompt else None)
        
        # Calculate duration
        end_time = time.time()
        duration = end_time - start_time
        app.logger.info(f'[CHAT] Query completed in {duration:.2f}s - Store: {store_id}')
        
        # Convert markdown to HTML
        answer_html = markdown.markdown(answer_text)
        
        # Render both user message and bot response
        user_html = render_template('partials/chat_message.html', message=query, sender='user')
        bot_html = render_template('partials/chat_message.html', 
                                   message=answer_html, 
                                   sender='bot',
                                   source_nodes=source_nodes,
                                   is_local=store_id.startswith('local_'))
        
        return user_html + bot_html
    
    except Exception as e:
        print(f"[CHAT] ❌ Error processing query: {e}")
        error_html = render_template('partials/chat_message.html', 
                                    message=f"Error processing query: {str(e)}", 
                                    sender='bot')
        return error_html, 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)