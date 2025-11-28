"""
Unit tests for google_file_search.py
Tests the core functionality of file search store management
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

import google_file_search as gfs


class TestCreateNewFileSearchStore:
    """Tests for create_new_file_search_store function"""
    
    def test_create_store_success(self, mock_genai_client, mock_store):
        """Test successful store creation"""
        mock_genai_client.file_search_stores.create.return_value = mock_store
        
        result = gfs.create_new_file_search_store('Test Store')
        
        assert result == 'fileSearchStores/test-store-123'
        mock_genai_client.file_search_stores.create.assert_called_once()
        
    def test_create_store_failure(self, mock_genai_client):
        """Test store creation failure handling"""
        mock_genai_client.file_search_stores.create.side_effect = Exception('API Error')
        
        result = gfs.create_new_file_search_store('Test Store')
        
        assert result == ''
    
    def test_create_store_with_special_characters(self, mock_genai_client, mock_store):
        """Test store creation with special characters in name"""
        mock_store.display_name = 'Test-Store_2025 (V2)'
        mock_genai_client.file_search_stores.create.return_value = mock_store
        
        result = gfs.create_new_file_search_store('Test-Store_2025 (V2)')
        
        assert result == 'fileSearchStores/test-store-123'


class TestListAllFileSearchStores:
    """Tests for list_all_file_search_stores function"""
    
    def test_list_stores_success(self, mock_genai_client, mock_store):
        """Test successful retrieval of stores"""
        mock_genai_client.file_search_stores.list.return_value = [mock_store, mock_store]
        
        result = gfs.list_all_file_search_stores()
        
        assert len(result) == 2
        assert result[0].name == 'fileSearchStores/test-store-123'
    
    def test_list_stores_empty(self, mock_genai_client):
        """Test retrieval when no stores exist"""
        mock_genai_client.file_search_stores.list.return_value = []
        
        result = gfs.list_all_file_search_stores()
        
        assert result == []
    
    def test_list_stores_api_error(self, mock_genai_client):
        """Test error handling when API call fails"""
        mock_genai_client.file_search_stores.list.side_effect = Exception('API Error')
        
        result = gfs.list_all_file_search_stores()
        
        assert result == []


class TestDeleteFileSearchStore:
    """Tests for delete_file_search_store function"""
    
    def test_delete_store_success(self, mock_genai_client):
        """Test successful store deletion"""
        gfs.delete_file_search_store('fileSearchStores/test-store-123')
        
        mock_genai_client.file_search_stores.delete.assert_called_once_with(
            name='fileSearchStores/test-store-123'
        )
    
    def test_delete_store_failure(self, mock_genai_client):
        """Test error handling during store deletion"""
        mock_genai_client.file_search_stores.delete.side_effect = Exception('Not Found')
        
        # Should not raise exception, just log error
        gfs.delete_file_search_store('fileSearchStores/nonexistent')
        
        mock_genai_client.file_search_stores.delete.assert_called_once()


class TestAddDocumentToStore:
    """Tests for add_document_to_store function"""
    
    def test_add_document_success(self, mock_genai_client, mock_document):
        """Test successful document upload"""
        # Mock the upload operation
        mock_operation = Mock()
        mock_operation.done = True
        mock_genai_client.file_search_stores.upload_to_file_search_store.return_value = mock_operation
        
        # Mock document listing - document display_name must match the uploaded filename
        mock_document.display_name = 'test.pdf'
        mock_genai_client.file_search_stores.documents.list.return_value = [mock_document]
        
        result = gfs.add_document_to_store('fileSearchStores/test-store-123', '/path/to/test.pdf')
        
        assert result == 'fileSearchStores/test-store-123/documents/test-doc-456'
    def test_add_document_wait_for_indexing(self, mock_genai_client, mock_document):
        """Test that function waits for document indexing to complete"""
        # Mock operation that takes multiple calls to complete
        mock_operation = Mock()
        mock_operation.done = False
        mock_operation_complete = Mock()
        mock_operation_complete.done = True
        
        mock_genai_client.file_search_stores.upload_to_file_search_store.return_value = mock_operation
        mock_genai_client.operations.get.return_value = mock_operation_complete
        mock_document.display_name = 'document.pdf'
        mock_genai_client.file_search_stores.documents.list.return_value = [mock_document]
        
        result = gfs.add_document_to_store('fileSearchStores/test-store-123', '/path/to/document.pdf')
        
        # Verify get was called to poll operation status
        mock_genai_client.operations.get.assert_called()
        assert result == 'fileSearchStores/test-store-123/documents/test-doc-456'
        assert result == 'fileSearchStores/test-store-123/documents/test-doc-456'
    
    def test_add_document_file_not_found(self, mock_genai_client):
        """Test error when file doesn't exist"""
        mock_genai_client.file_search_stores.upload_to_file_search_store.side_effect = FileNotFoundError()
        
        result = gfs.add_document_to_store('fileSearchStores/test-store-123', '/nonexistent/file.pdf')
        
        assert result == ''


class TestListDocumentsInStore:
    """Tests for list_documents_in_store function"""
    
    def test_list_documents_success(self, mock_genai_client, mock_document):
        """Test successful document retrieval"""
        mock_genai_client.file_search_stores.documents.list.return_value = [mock_document, mock_document]
        
        result = gfs.list_documents_in_store('fileSearchStores/test-store-123')
        
        assert len(result) == 2
        assert result[0].display_name == 'test_document.pdf'
    
    def test_list_documents_empty(self, mock_genai_client):
        """Test retrieval when store has no documents"""
        mock_genai_client.file_search_stores.documents.list.return_value = []
        
        result = gfs.list_documents_in_store('fileSearchStores/test-store-123')
        
        assert result == []
    
    def test_list_documents_api_error(self, mock_genai_client):
        """Test error handling when API call fails"""
        mock_genai_client.file_search_stores.documents.list.side_effect = Exception('API Error')
        
        result = gfs.list_documents_in_store('fileSearchStores/test-store-123')
        
        assert result == []


class TestDeleteDocumentFromStore:
    """Tests for delete_document_from_store function"""
    
    @patch('google_file_search.requests.delete')
    def test_delete_document_success(self, mock_delete):
        """Test successful document deletion"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_delete.return_value = mock_response
        
        gfs.delete_document_from_store('fileSearchStores/test-store-123/documents/doc-456')
        
        mock_delete.assert_called_once()
        # Verify the URL format
        call_args = mock_delete.call_args
        assert 'fileSearchStores/test-store-123/documents/doc-456' in call_args[0][0]
    
    @patch('google_file_search.requests.delete')
    def test_delete_document_not_found(self, mock_delete):
        """Test deletion when document doesn't exist"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_delete.return_value = mock_response
        
        # Should handle gracefully
        gfs.delete_document_from_store('fileSearchStores/test-store-123/documents/nonexistent')
        
        mock_delete.assert_called_once()
    
    @patch('google_file_search.requests.delete')
    def test_delete_document_api_error(self, mock_delete):
        """Test error handling during deletion"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_delete.return_value = mock_response
        
        # Should handle gracefully
        gfs.delete_document_from_store('fileSearchStores/test-store-123/documents/doc-456')
        
        mock_delete.assert_called_once()


class TestAskStoreQuestion:
    """Tests for ask_store_question function"""
    
    def test_ask_question_basic(self, mock_genai_client, mock_response):
        """Test basic question answering"""
        mock_genai_client.models.generate_content.return_value = mock_response
        
        result = gfs.ask_store_question('fileSearchStores/test-store-123', 'What is this?')
        
        assert 'This is the AI response' in result
        assert '**Sources:**' in result
        assert 'source_document.pdf' in result
    
    def test_ask_question_with_system_prompt(self, mock_genai_client, mock_response):
        """Test question answering with custom system prompt"""
        mock_genai_client.models.generate_content.return_value = mock_response
        
        system_prompt = 'You are a helpful assistant'
        result = gfs.ask_store_question(
            'fileSearchStores/test-store-123',
            'What is this?',
            system_prompt=system_prompt
        )
        
        # Verify generate_content was called
        mock_genai_client.models.generate_content.assert_called_once()
        call_kwargs = mock_genai_client.models.generate_content.call_args[1]
        
        # Verify system_instruction was included in config
        assert call_kwargs['config'].system_instruction == system_prompt
    
    def test_ask_question_without_system_prompt(self, mock_genai_client, mock_response):
        """Test question answering without system prompt"""
        mock_genai_client.models.generate_content.return_value = mock_response
        
        result = gfs.ask_store_question(
            'fileSearchStores/test-store-123',
            'What is this?'
        )
        
        assert 'This is the AI response' in result
        # Verify generate_content was called without system_instruction
        call_kwargs = mock_genai_client.models.generate_content.call_args[1]
        assert not hasattr(call_kwargs['config'], 'system_instruction') or \
               call_kwargs['config'].system_instruction is None
    
    def test_ask_question_no_citations(self, mock_genai_client):
        """Test response handling when no citations available"""
        mock_response = Mock()
        mock_response.text = 'This is the AI response'
        mock_response.candidates = [Mock(grounding_metadata=None)]
        mock_genai_client.models.generate_content.return_value = mock_response
        
        result = gfs.ask_store_question('fileSearchStores/test-store-123', 'What is this?')
        
        assert 'This is the AI response' in result
        assert '**Sources:**' not in result
    
    def test_ask_question_api_error(self, mock_genai_client):
        """Test error handling when API call fails"""
        mock_genai_client.models.generate_content.side_effect = Exception('API Error')
        
        result = gfs.ask_store_question('fileSearchStores/test-store-123', 'What is this?')
        
        assert 'Error processing query' in result
    
    def test_ask_question_uses_correct_model(self, mock_genai_client, mock_response):
        """Test that the correct model is being used"""
        mock_genai_client.models.generate_content.return_value = mock_response
        
        gfs.ask_store_question('fileSearchStores/test-store-123', 'What is this?')
        
        call_kwargs = mock_genai_client.models.generate_content.call_args[1]
        assert call_kwargs['model'] == 'gemini-2.5-flash'
    
    def test_ask_question_uses_file_search_tool(self, mock_genai_client, mock_response):
        """Test that file search tool is configured correctly"""
        mock_genai_client.models.generate_content.return_value = mock_response
        
        gfs.ask_store_question('fileSearchStores/test-store-123', 'What is this?')
        
        call_kwargs = mock_genai_client.models.generate_content.call_args[1]
        config = call_kwargs['config']
        
        # Verify tools are configured
        assert hasattr(config, 'tools')
        assert len(config.tools) > 0
