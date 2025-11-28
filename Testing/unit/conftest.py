import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))


@pytest.fixture
def mock_genai_client():
    """Mock the Google Generative AI client"""
    with patch('google_file_search.client') as mock_client:
        yield mock_client


@pytest.fixture
def mock_store():
    """Create a mock file search store object"""
    mock = Mock()
    mock.name = 'fileSearchStores/test-store-123'
    mock.display_name = 'Test Store'
    mock.create_time = Mock()
    mock.create_time.date.return_value = '2025-01-01'
    return mock


@pytest.fixture
def mock_document():
    """Create a mock document object"""
    mock = Mock()
    mock.name = 'fileSearchStores/test-store-123/documents/test-doc-456'
    mock.display_name = 'test_document.pdf'
    mock.state.name = 'ACTIVE'
    mock.create_time = Mock()
    return mock


@pytest.fixture
def mock_response():
    """Create a mock API response object"""
    mock = Mock()
    mock.text = 'This is the AI response'
    
    # Mock grounding metadata with citations
    chunk = Mock()
    chunk.retrieved_context.title = 'source_document.pdf'
    
    candidate = Mock()
    candidate.grounding_metadata = Mock()
    candidate.grounding_metadata.grounding_chunks = [chunk]
    
    mock.candidates = [candidate]
    return mock
