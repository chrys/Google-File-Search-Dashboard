import os
import sys
import markdown
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Add current directory to path to import google_file_search from src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import google_file_search as gfs
from prompt_storage import get_prompt_storage

# Setup template and static folders to point to parent directory
template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static')
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
CORS(app)

# Initialize prompt storage
prompt_storage = get_prompt_storage()

# Configuration
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
    stores = gfs.list_all_file_search_stores()
    list_type = request.args.get('type', 'admin')
    
    if list_type == 'chat':
        return render_template('partials/chat_project_list.html', stores=stores)
    return render_template('partials/project_list.html', stores=stores)

@app.route('/api/projects', methods=['POST'])
def create_project():
    display_name = request.form.get('display_name')
    if display_name:
        gfs.create_new_file_search_store(display_name)
    
    # Return updated list
    stores = gfs.list_all_file_search_stores()
    return render_template('partials/project_list.html', stores=stores)

@app.route('/api/projects/<path:store_id>', methods=['DELETE'])
def delete_project(store_id):
    gfs.delete_file_search_store(store_id)
    
    # Return updated list
    stores = gfs.list_all_file_search_stores()
    return render_template('partials/project_list.html', stores=stores)

# Documents
@app.route('/api/projects/<path:store_id>/documents', methods=['GET'])
def list_documents(store_id):
    documents = gfs.list_documents_in_store(store_id)
    # We need to find the project name to display it
    # This is a bit inefficient, but we don't have a direct "get store" function in the helper yet
    # We can pass it from the frontend or fetch all stores.
    # For now, let's just pass the store_id as the name if we can't find it, or fetch all.
    # Actually, the frontend `loadProjectDetails` passes `displayName` but we are using HTMX GET.
    # Let's just use the store_id or fetch all to find the name.
    
    project_name = "Project Documents"
    stores = gfs.list_all_file_search_stores()
    for store in stores:
        if store.name == store_id:
            project_name = store.display_name
            break
            
    return render_template('partials/document_list.html', documents=documents, store_id=store_id, project_name=project_name)

@app.route('/api/projects/<path:store_id>/documents', methods=['POST'])
def upload_document(store_id):
    if 'file' not in request.files:
        return 'No file part', 400
    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            gfs.add_document_to_store(store_id, filepath)
        finally:
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)
        
        # Return updated document items only (to keep the header)
        # Wait, the target in document_list.html is #document-list which contains the items.
        # So we should return document_items.html
@app.route('/api/documents/<path:document_id>', methods=['DELETE'])
def delete_document(document_id):
    # document_id is the full resource name, e.g. fileSearchStores/.../documents/...
    # We need to extract the store_id to re-list documents
    # Format: fileSearchStores/{store_id}/documents/{doc_id}
    parts = document_id.split('/')
    store_id = f"{parts[0]}/{parts[1]}"
    
    gfs.delete_document_from_store(document_id)
    
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

# Chatcuments = gfs.list_documents_in_store(store_id)
    return render_template('partials/document_items.html', documents=documents)

# Chat
@app.route('/api/chat', methods=['POST'])
def ask_question():
    import time
    import logging
    
    store_id = request.form.get('store_id')
    query = request.form.get('query')
    
    if not store_id or not query:
        return '', 400
    
    # Record start time
    start_time = time.time()
    app.logger.info(f'[CHAT] Query started at {start_time:.3f} - Store: {store_id} | Query: {query[:50]}...')
    
    # Get the custom prompt if it exists
    system_prompt = prompt_storage.get_prompt(store_id)
    
    # Generate answer with optional custom prompt
    answer_text = gfs.ask_store_question(store_id, query, system_prompt if system_prompt else None)
    
    # Calculate duration
    end_time = time.time()
    duration = end_time - start_time
    app.logger.info(f'[CHAT] Query completed in {duration:.2f}s - Store: {store_id}')
    
    # Convert markdown to HTML
    answer_html = markdown.markdown(answer_text)
    
    # Render both user message and bot response
    user_html = render_template('partials/chat_message.html', message=query, sender='user')
    bot_html = render_template('partials/chat_message.html', message=answer_html, sender='bot')
    
    return user_html + bot_html

if __name__ == '__main__':
    app.run(debug=True, port=5000)
