import os
import sys
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.local_project_storage import LocalProjectStorage
from src.local_rag import LocalRAGEngine


class TestLocalProjectStorage:
    """Test suite for LocalProjectStorage"""
    
    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for test data"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def storage(self, temp_data_dir):
        """Create a LocalProjectStorage instance with temp directory"""
        return LocalProjectStorage(data_dir=temp_data_dir)
    
    def test_storage_initialization(self, storage, temp_data_dir):
        """Test that storage initializes with empty projects"""
        assert storage.data_dir == temp_data_dir
        assert storage.projects == {}
        assert os.path.exists(temp_data_dir)
    
    def test_create_project(self, storage):
        """Test creating a local project"""
        project_id = storage.create_project("Test Project")
        
        assert project_id.startswith("local_")
        assert "test_project" in project_id  # Project name is lowercased with underscores
        assert project_id in storage.projects
        
        project = storage.projects[project_id]
        assert project["display_name"] == "Test Project"
        assert project["documents"] == {}
        assert "created_at" in project
    
    def test_create_project_persists_to_file(self, storage, temp_data_dir):
        """Test that created projects are saved to file"""
        project_id = storage.create_project("Test Project")
        
        # Verify file exists
        projects_file = os.path.join(temp_data_dir, "local_projects.json")
        assert os.path.exists(projects_file)
        
        # Verify data in file
        with open(projects_file, 'r') as f:
            data = json.load(f)
            assert project_id in data
            assert data[project_id]["display_name"] == "Test Project"
    
    def test_list_projects(self, storage):
        """Test listing all projects"""
        project_id_1 = storage.create_project("Project 1")
        project_id_2 = storage.create_project("Project 2")
        
        projects = storage.list_projects()
        
        assert len(projects) == 2
        display_names = [p["display_name"] for p in projects]
        assert "Project 1" in display_names
        assert "Project 2" in display_names
    
    def test_get_project(self, storage):
        """Test retrieving a specific project"""
        project_id = storage.create_project("Test Project")
        
        project = storage.get_project(project_id)
        
        assert project is not None
        assert project["display_name"] == "Test Project"
        assert project["id"] == project_id
    
    def test_get_nonexistent_project(self, storage):
        """Test retrieving a project that doesn't exist"""
        project = storage.get_project("nonexistent")
        assert project is None
    
    def test_add_document_to_project(self, storage):
        """Test adding a document to a project"""
        project_id = storage.create_project("Test Project")
        
        success = storage.add_document(project_id, "document.pdf")
        
        assert success is True
        project = storage.projects[project_id]
        assert "document.pdf" in project["documents"]
        assert "indexed_at" in project["documents"]["document.pdf"]
    
    def test_add_document_persists(self, storage, temp_data_dir):
        """Test that added documents are saved to file"""
        project_id = storage.create_project("Test Project")
        storage.add_document(project_id, "document.pdf")
        
        # Verify file persistence
        projects_file = os.path.join(temp_data_dir, "local_projects.json")
        with open(projects_file, 'r') as f:
            data = json.load(f)
            assert "document.pdf" in data[project_id]["documents"]
    
    def test_remove_document_from_project(self, storage):
        """Test removing a document from a project"""
        project_id = storage.create_project("Test Project")
        storage.add_document(project_id, "document.pdf")
        
        success = storage.remove_document(project_id, "document.pdf")
        
        assert success is True
        project = storage.projects[project_id]
        assert "document.pdf" not in project["documents"]
    
    def test_remove_nonexistent_document(self, storage):
        """Test removing a document that doesn't exist"""
        project_id = storage.create_project("Test Project")
        
        success = storage.remove_document(project_id, "nonexistent.pdf")
        
        assert success is False
    
    def test_delete_project(self, storage):
        """Test deleting a project"""
        project_id = storage.create_project("Test Project")
        assert project_id in storage.projects
        
        success = storage.delete_project(project_id)
        
        assert success is True
        assert project_id not in storage.projects
    
    def test_delete_project_persists(self, storage, temp_data_dir):
        """Test that deleted projects are removed from file"""
        project_id = storage.create_project("Test Project")
        storage.delete_project(project_id)
        
        # Verify file update
        projects_file = os.path.join(temp_data_dir, "local_projects.json")
        with open(projects_file, 'r') as f:
            data = json.load(f)
            assert project_id not in data
    
    def test_delete_nonexistent_project(self, storage):
        """Test deleting a project that doesn't exist"""
        success = storage.delete_project("nonexistent")
        assert success is False
    
    def test_load_existing_projects(self, temp_data_dir):
        """Test loading existing projects from file"""
        # Create a projects file
        projects_data = {
            "local_test_project": {
                "id": "local_test_project",
                "display_name": "Test Project",
                "created_at": datetime.now().isoformat(),
                "documents": {
                    "document.pdf": {
                        "indexed_at": datetime.now().isoformat()
                    }
                }
            }
        }
        
        projects_file = os.path.join(temp_data_dir, "local_projects.json")
        with open(projects_file, 'w') as f:
            json.dump(projects_data, f)
        
        # Load storage
        storage = LocalProjectStorage(data_dir=temp_data_dir)
        
        assert "local_test_project" in storage.projects
        assert storage.projects["local_test_project"]["display_name"] == "Test Project"
        assert "document.pdf" in storage.projects["local_test_project"]["documents"]
    
    def test_multiple_documents_in_project(self, storage):
        """Test managing multiple documents in a single project"""
        project_id = storage.create_project("Multi-Doc Project")
        
        storage.add_document(project_id, "doc1.pdf")
        storage.add_document(project_id, "doc2.pdf")
        storage.add_document(project_id, "doc3.txt")
        
        project = storage.projects[project_id]
        assert len(project["documents"]) == 3
        assert "doc1.pdf" in project["documents"]
        assert "doc2.pdf" in project["documents"]
        assert "doc3.txt" in project["documents"]
    
    def test_get_all_projects(self, storage):
        """Test getting all projects as a copy"""
        project_id_1 = storage.create_project("Project 1")
        project_id_2 = storage.create_project("Project 2")
        
        all_projects = storage.get_all_projects()
        
        assert len(all_projects) == 2
        # Verify it's a copy
        all_projects[project_id_1]["display_name"] = "Modified"
        assert storage.projects[project_id_1]["display_name"] == "Project 1"


class TestLocalRAGEngine:
    """Test suite for LocalRAGEngine - skipped if packages not available"""
    
    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for test data"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_rag_engine_requires_dependencies(self, temp_data_dir):
        """Test that RAG engine requires LLaMA Index and ChromaDB"""
        try:
            from src.local_rag import LLAMAINDEX_AVAILABLE, CHROMADB_AVAILABLE
            
            # If dependencies aren't available, should fail gracefully
            if not LLAMAINDEX_AVAILABLE or not CHROMADB_AVAILABLE:
                with pytest.raises(ImportError):
                    engine = LocalRAGEngine(
                        project_id="local_test_project",
                        data_dir=temp_data_dir
                    )
        except ImportError:
            # Skip if local_rag module can't be imported
            pytest.skip("LLaMA Index or ChromaDB not fully installed")
    
    def test_extract_text_from_txt_file(self, temp_data_dir):
        """Test extracting text from .txt file"""
        try:
            engine = LocalRAGEngine(
                project_id="local_test_project",
                data_dir=temp_data_dir
            )
        except ImportError:
            pytest.skip("LLaMA Index or ChromaDB not fully installed")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is test content from a text file.")
            f.flush()
            temp_file = f.name
        
        try:
            text = engine.extract_text_from_file(temp_file)
            assert "This is test content from a text file." in text
        finally:
            os.unlink(temp_file)
    
    def test_extract_text_from_markdown_file(self, temp_data_dir):
        """Test extracting text from .md file"""
        try:
            engine = LocalRAGEngine(
                project_id="local_test_project",
                data_dir=temp_data_dir
            )
        except ImportError:
            pytest.skip("LLaMA Index or ChromaDB not fully installed")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Markdown Test\n\nThis is markdown content.")
            f.flush()
            temp_file = f.name
        
        try:
            text = engine.extract_text_from_file(temp_file)
            assert "# Markdown Test" in text
            assert "This is markdown content." in text
        finally:
            os.unlink(temp_file)
    
    def test_extract_text_unsupported_format(self, temp_data_dir):
        """Test that unsupported file formats raise error"""
        try:
            engine = LocalRAGEngine(
                project_id="local_test_project",
                data_dir=temp_data_dir
            )
        except ImportError:
            pytest.skip("LLaMA Index or ChromaDB not fully installed")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.unknown', delete=False) as f:
            f.write("content")
            f.flush()
            temp_file = f.name
        
        try:
            with pytest.raises(ValueError) as exc_info:
                engine.extract_text_from_file(temp_file)
            assert "Unsupported file type" in str(exc_info.value)
        finally:
            os.unlink(temp_file)


class TestRAGIntegrationWithStorage:
    """Integration tests for RAG and Storage"""
    
    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for test data"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def storage(self, temp_data_dir):
        """Create storage instance"""
        return LocalProjectStorage(data_dir=temp_data_dir)
    
    def test_project_document_tracking(self, storage, temp_data_dir):
        """Test that documents are properly tracked in projects"""
        project_id = storage.create_project("Document Test Project")
        
        # Simulate adding multiple documents
        storage.add_document(project_id, "research_paper.pdf")
        storage.add_document(project_id, "notes.txt")
        storage.add_document(project_id, "article.md")
        
        # Verify tracking
        project = storage.get_project(project_id)
        assert len(project["documents"]) == 3
        
        # Verify persistence
        storage_reloaded = LocalProjectStorage(data_dir=temp_data_dir)
        project_reloaded = storage_reloaded.get_project(project_id)
        assert len(project_reloaded["documents"]) == 3
        assert "research_paper.pdf" in project_reloaded["documents"]
    
    def test_document_removal_workflow(self, storage):
        """Test complete document removal workflow"""
        project_id = storage.create_project("Workflow Test")
        
        # Add documents
        storage.add_document(project_id, "doc1.pdf")
        storage.add_document(project_id, "doc2.pdf")
        
        assert len(storage.get_project(project_id)["documents"]) == 2
        
        # Remove one document
        storage.remove_document(project_id, "doc1.pdf")
        
        assert len(storage.get_project(project_id)["documents"]) == 1
        assert "doc2.pdf" in storage.get_project(project_id)["documents"]
        assert "doc1.pdf" not in storage.get_project(project_id)["documents"]
    
    def test_empty_project_structure(self, storage):
        """Test that projects start with empty documents"""
        project_id = storage.create_project("Empty Project")
        project = storage.get_project(project_id)
        
        assert project["documents"] == {}
        assert isinstance(project["documents"], dict)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
