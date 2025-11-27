# Gemini File Search Dashboard

A fully managed RAG (Retrieval-Augmented Generation) system that demonstrates the use of Google's Gemini API with File Search capabilities. This web application allows users to upload documents, organize them into projects, and query them using an AI-powered chat interface.

## Features

- **Project Management**: Create and manage file search stores (projects) to organize your documents
- **Document Management**: Upload files to projects for indexing and retrieval
- **AI Chat Interface**: Query documents using Gemini API with grounded responses
- **Dynamic UI**: HTMX-powered interface for seamless interactions without full page reloads
- **Citations**: Responses include references to source documents
- **Admin Dashboard**: Manage projects and documents with an intuitive interface

## Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: HTMX + Tailwind CSS
- **AI/ML**: Google Gemini API with File Search
- **File Processing**: Google File Search API

## Prerequisites

- Python 3.8+
- Google Cloud Account with Gemini API access
- API credentials configured for Google File Search

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd "Google File Search Dashboard"
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up Google API credentials:
   - Create a `.env` file in the project root
   - Add your Gemini API key:
   ```
   GOOGLE_API_KEY=your_gemini_api_key_here
   ```
   - Get your API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Follow [Google's authentication guide](https://cloud.google.com/docs/authentication) for additional setup if needed

## Usage

1. Activate the virtual environment:
```bash
source .venv/bin/activate
```

2. Run the Flask application:
```bash
python app.py
```

3. Open your browser and navigate to:
   - **Chat**: `http://localhost:5000/chat` - Query documents
   - **Admin**: `http://localhost:5000/admin` - Manage projects and documents

## Project Structure

```
├── app.py                    # Flask application and routes
├── google_file_search.py     # Google File Search API wrapper
├── requirements.txt          # Python dependencies
├── templates/
│   ├── base.html            # Base template with navigation
│   ├── admin.html           # Admin dashboard
│   ├── chat.html            # Chat interface
│   └── partials/            # Reusable template components
│       ├── chat_message.html
│       ├── chat_project_list.html
│       ├── document_items.html
│       ├── document_list.html
│       └── project_list.html
├── uploads/                 # Temporary directory for file uploads (auto-cleaned)
└── __pycache__/            # Python cache files
```

## API Endpoints

### Projects (File Search Stores)
- `GET /api/projects` - List all projects
- `POST /api/projects` - Create a new project
- `DELETE /api/projects/<store_id>` - Delete a project

### Documents
- `GET /api/projects/<store_id>/documents` - List documents in a project
- `POST /api/projects/<store_id>/documents` - Upload a document to a project
- `DELETE /api/documents/<document_id>` - Delete a document

### Chat
- `POST /api/chat` - Send a query to a project's documents

## How It Works

1. **Upload Documents**: Use the Admin tab to create projects (File Search Stores) and upload documents
2. **Indexing**: Google's File Search API automatically indexes uploaded documents
3. **Querying**: Switch to the Chat tab, select a project, and ask questions
4. **AI Responses**: Gemini API processes queries against indexed documents and returns grounded responses with citations

## Environment Variables

If using environment-based configuration, ensure the following are set:
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to your Google Cloud service account JSON file

## Development

To run in development mode with auto-reload:
```bash
python app.py
```

The Flask app runs on `http://localhost:5000` with debug mode enabled.

## Troubleshooting

### Chat input not clearing after sending
- Ensure HTMX is properly loaded in the chat template
- Check browser console for any JavaScript errors

### Messages not scrolling to bottom
- Verify the chat messages container has the correct ID (`#chat-messages`)
- Check that the scroll event listener is properly attached

### Documents not appearing in project
- Verify the file upload was successful (check terminal logs)
- Ensure the document is properly indexed by Google File Search API
- Check that the project (store) ID is correct

## Contributing

Feel free to submit issues and enhancement requests!


## Support

For issues with:
- **Google File Search API**: See [Google's documentation](https://ai.google.dev/docs/file-api)
- **Gemini API**: See [Gemini API documentation](https://ai.google.dev/)
- **HTMX**: See [HTMX documentation](https://htmx.org/)
