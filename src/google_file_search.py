import time
from google import genai
from google.genai import types 
import dotenv
import os
import requests


#read GOOGLE_API_KEY from file .env 
dotenv.load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    print("WARNING: GOOGLE_API_KEY environment variable not set - API functions will fail at runtime")
else:
    os.environ["GOOGLE_API_KEY"] = API_KEY

os.environ["GEMINI_API_KEY"] = API_KEY

client = genai.Client()

def create_new_file_search_store(store_display_name: str) -> str:
    """
    Creates a new, empty File Search Store and returns its unique resource name.

    Args:
        store_display_name: The human-readable name for the store (e.g., "Finance_Site_Knowledge").

    Returns:
        The unique store ID (resource name), e.g., 'fileSearchStores/abc-123'.
    """
    
    print(f"Attempting to create store: {store_display_name}...")
    
    try:
        # The .create method is what provisions the new store on Google's backend
        file_search_store = client.file_search_stores.create(
            config={'display_name': store_display_name}
        )
        
        # The .name attribute holds the unique, persistent ID
        store_id = file_search_store.name
        
        print(f"✅ Successfully created store: '{store_display_name}'")
        print(f"   Resource ID: {store_id}\n")
        
        return store_id
        
    except Exception as e:
        print(f"❌ Failed to create store: {e}")
        return ""

def list_all_file_search_stores():
    """Retrieves and prints the list of all File Search Stores."""
    
    print("Fetching list of all File Search Stores...")
    
    try:
        # The list() method returns a PagedList (an iterable object)
        pager = client.file_search_stores.list()
        
        stores = list(pager)
        
        if not stores:
            print("No File Search Stores found for this project.")
            return []

        print(f"\nFound {len(stores)} File Search Store(s):")
        print("=" * 40)

        for store in stores:
            # 🔑 .name is the unique ID you need for API calls
            store_id = store.name
            
            # 🔑 .display_name is the human-readable name you set during creation
            display_name = store.display_name
            
            print(f"Chatbot Name:    {display_name}")
            print(f"Resource ID:     {store_id}")
            print(f"Created On:      {store.create_time.date()}")
            print("-" * 40)
            
        return stores

    except Exception as e:
        print(f"An error occurred while listing stores: {e}")
        return []

def delete_file_search_store(store_id_to_delete: str):
    """
    Deletes a specified File Search Store and all its contents permanently.

    Args:
        store_id_to_delete: The unique resource ID of the store 
                            (e.g., 'fileSearchStores/abc-123').
    """
    
    print(f"⚠️ Attempting to permanently delete store: {store_id_to_delete}...")
    
    try:
        # The .delete method requires the 'name' (the store_id)
        # force=True is required to confirm the removal of all resources
        client.file_search_stores.delete(
            name=store_id_to_delete,
        )
        
        print(f"✅ Successfully deleted store: {store_id_to_delete}")
        
    except Exception as e:
        print(f"❌ Failed to delete store {store_id_to_delete}: {e}")

def add_document_to_store(store_id: str, file_path: str) -> str:
    """
    Uploads a document to a specified File Search Store and waits for indexing to complete.

    Args:
        store_id: The unique resource ID of the target store 
                  (e.g., 'fileSearchStores/abc-123').
        file_path: The local path to the document you want to upload.

    Returns:
        The resource name of the uploaded document if successful, otherwise an empty string.
    """
    
    file_name = os.path.basename(file_path)
    print(f"Uploading and indexing '{file_name}' into store: {store_id}...")
    
    try:
        # The upload_to_file_search_store method initiates the indexing process
        operation = client.file_search_stores.upload_to_file_search_store(
            file=file_path,
            file_search_store_name=store_id,
            config={'display_name': file_name}
        )
        
        print("   ⌛ Waiting for file indexing to complete (This may take a moment)...")

        # --- Wait for Indexing ---
        # Polling the operation ensures the file is fully indexed before you query
        while not operation.done:
            time.sleep(5)
            operation = client.operations.get(operation)

        # Get the result from the completed operation
        # Note: operation.result() is failing with AttributeError in some versions
        
        # Workaround: Fetch the document by name from the store
        print("   Verifying upload...")
        pager = client.file_search_stores.documents.list(parent=store_id)
        all_docs = list(pager)
        
        # Find documents with matching display name
        matching_docs = [d for d in all_docs if d.display_name == file_name]
        
        if matching_docs:
            # Get the most recently created one
            newest_doc = max(matching_docs, key=lambda d: d.create_time)
            document_resource_name = newest_doc.name
            print(f"   ✅ Indexing complete! Document Resource Name: {document_resource_name}\n")
            return document_resource_name
        else:
             raise Exception(f"Document {file_name} not found in store after upload.")
        
    except Exception as e:
        print(f"❌ Failed to add document to store: {e}")
        return ""

def ask_store_question(store_id: str, query: str, system_prompt: str = None) -> str:
    """
    Asks a question, grounding the answer ONLY in the documents of the specified store.

    Args:
        store_id: The unique resource ID of the target store 
                  (e.g., 'fileSearchStores/abc-123').
        query: The user's question.
        system_prompt: Optional custom system prompt to guide the model's response.

    Returns:
        The model's answer, potentially with citations.
    """
    
    MODEL = "gemini-2.5-flash" # Supports File Search properly
    
    print(f"Querying store '{store_id}' with model {MODEL}...")
    if system_prompt:
        print(f"Using custom system prompt...")
    
    try:
        # --- 1. Configure the FileSearch Tool ---
        from google.genai import types as genai_types
        
        # Create the file search configuration
        file_search_config = genai_types.FileSearch(
            file_search_store_names=[store_id]
        )
        
        # Create tool with file_search
        file_search_tool = genai_types.Tool(
            file_search=file_search_config
        )

        # --- 2. Build GenerateContentConfig with system_instruction ---
        config_kwargs = {
            'tools': [file_search_tool]
        }
        
        if system_prompt:
            config_kwargs['system_instruction'] = system_prompt
            print(f"[DEBUG] System instruction set: {system_prompt[:50]}...")

        # --- 3. Generate Content ---
        response = client.models.generate_content(
            model=MODEL,
            contents=query,
            config=types.GenerateContentConfig(**config_kwargs)
        )

        # --- 4. Format and Return Response ---
        
        answer_text = response.text
        
        # Optional: Append citations for verification
        citations = []
        if response.candidates and response.candidates[0].grounding_metadata:
            for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
                # The title is the file's display name set during upload
                citations.append(chunk.retrieved_context.title)
        
        if citations:
            answer_text += "\n\n**Sources:** " + ", ".join(set(citations))

        return answer_text

    except Exception as e:
        return f"Error processing query: {e}"
    

def list_documents_in_store(store_id: str):
    """
    Retrieves and prints the list of all documents within a specified File Search Store.

    Args:
        store_id: The unique resource ID of the target store 
                  (e.g., 'fileSearchStores/abc-123').
    """
    
    print(f"Fetching documents for store: {store_id}...")
    
    try:
        # The list method is on the 'documents' resource of the store.
        # It requires the 'parent' argument, which is the store's ID.
        pager = client.file_search_stores.documents.list(parent=store_id)
        
        documents = list(pager)
        
        if not documents:
            print(f"No documents found in store: {store_id}")
            return []

        print(f"\nFound {len(documents)} document(s) in the store:")
        print("=" * 60)

        for doc in documents:
            # doc.name is the full Document Resource Name (used for deletion)
            doc_resource_name = doc.name
            
            # doc.display_name is the human-readable name (used for filtering)
            display_name = doc.display_name
            
            print(f"File Name (for filtering): {display_name}")
            print(f"Document ID (for deletion): {doc_resource_name}")
            print(f"State: {doc.state.name}") # State should be 'ACTIVE'
            print("-" * 60)
        
        return documents
        
        
            
    except Exception as e:
        print(f"❌ Failed to list documents for store {store_id}: {e}")
        return []
 
def delete_document_from_store(document_resource_name: str):
    """
    Deletes a specific document and its indexed embeddings from a File Search Store.
    Uses the REST API directly to delete the document.

    Args:
        document_resource_name: The full resource ID of the document to delete 
                                (e.g., 'fileSearchStores/mysecondfilesearchstore-1m3ju15v7hjz/documents/data2txt-dr72i7yy967c').
    """
    
    print(f"⚠️ Attempting to delete document: {document_resource_name}...")
    
    try:
        # Construct the full API endpoint URL with API key as query parameter
        api_url = f"https://generativelanguage.googleapis.com/v1beta/{document_resource_name}?key={API_KEY}&force=true"
        
        # Set up headers
        headers = {
            "Content-Type": "application/json",
        }
        
        # Make DELETE request
        response = requests.delete(api_url, headers=headers)
        
        # Check for successful response
        if response.status_code == 200:
            print(f"✅ Successfully deleted document: {document_resource_name}")
        elif response.status_code == 404:
            print(f"⚠️ Document not found: {document_resource_name}")
        else:
            # Raise exception for other potential errors
            raise Exception(f"API Error {response.status_code}: {response.text}")
        
    except Exception as e:
        print(f"❌ Failed to delete document {document_resource_name}: {e}")
 
def main():
    pass
    # add_document_to_store(store_id = "fileSearchStores/myfirstfilesearchstore-kdvasuq6oqk8", file_path="/Users/chrys/Gemini File Search/data1.txt")
    # add_document_to_store(store_id = "fileSearchStores/mysecondfilesearchstore-1m3ju15v7hjz", file_path="/Users/chrys/Gemini File Search/data2.txt")    

    # USER_QUESTION1 = "What is Happy Payments?"
    # USER_QUESTION2 = "What is Sad Payments?"
    
    # final_answer1 = ask_store_question("fileSearchStores/myfirstfilesearchstore-kdvasuq6oqk8", USER_QUESTION1)
    
    # print("\n--- Answer1 ---")
    # print(final_answer1)
    
    # final_answer2 = ask_store_question("fileSearchStores/mysecondfilesearchstore-1m3ju15v7hjz", USER_QUESTION2)
    
    # print("\n--- Answer2 ---")
    # print(final_answer2)
   
   #get all stores and go through their documents and delete them all 
    # stores = list_all_file_search_stores()
    # if stores:
    #     for store in stores:
    #         store_id = store.name
    #         print(f"Processing store: {store_id}")
    #         #list documents in store
    #         pager = client.file_search_stores.documents.list(parent=store_id)
    #         documents = list(pager)
    #         for doc in documents:
    #             doc_resource_name = doc.name
    #             delete_document_from_store(doc_resource_name)
    
    #get all stores and list ttheir documents
    stores = list_all_file_search_stores()
    if stores:
        for store in stores:
            store_id = store.name
            print(f"Processing store: {store_id}")
            #list documents in store
            list_documents_in_store(store_id)
            
    # delete_document_from_store("fileSearchStores/mysecondfilesearchstore-1m3ju15v7hjz/documents/data2txt-dr72i7yy967c")
    
    # stores = list_all_file_search_stores()
    # if stores:
    #     for store in stores:
    #         store_id = store.name
    #         print(f"Processing store: {store_id}")
    #         #list documents in store
    #         list_documents_in_store(store_id)

if __name__ == "__main__":
    main()