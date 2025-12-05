import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from copy import deepcopy

class LocalProjectStorage:
    """Handles loading and saving local projects to a JSON file"""
    
    def __init__(self, data_dir: str = None):
        """
        Initialize local project storage
        
        Args:
            data_dir: Directory to store local_projects.json file. Defaults to project root/configuration.
        """
        if data_dir is None:
            # Get the project root (parent of src) then add configuration subdirectory
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(project_root, 'configuration')
        
        self.data_dir = data_dir
        self.projects_file = os.path.join(data_dir, 'local_projects.json')
        self.projects = self._load_projects()
    
    def _load_projects(self) -> dict:
        """Load projects from JSON file or create empty dict if file doesn't exist"""
        # Ensure directory exists first
        os.makedirs(self.data_dir, exist_ok=True)
        
        if os.path.exists(self.projects_file):
            try:
                with open(self.projects_file, 'r') as f:
                    content = f.read().strip()
                    if not content:
                        print(f"📝 Local projects file is empty at {self.projects_file}. Starting with empty projects.")
                        return {}
                    projects = json.loads(content)
                    print(f"✅ Loaded {len(projects)} local projects from {self.projects_file}")
                    return projects
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️ Error reading local projects file: {e}. Starting with empty projects.")
                return {}
        else:
            print(f"📝 No local projects file found at {self.projects_file}. Creating new one on first save.")
            return {}
    
    def _save_projects(self):
        """Save projects to JSON file"""
        try:
            # Ensure directory exists
            os.makedirs(self.data_dir, exist_ok=True)
            
            with open(self.projects_file, 'w') as f:
                json.dump(self.projects, f, indent=2)
            print(f"✅ Saved local projects to {self.projects_file}")
        except IOError as e:
            print(f"❌ Error saving local projects: {e}")
    
    def create_project(self, display_name: str) -> str:
        """
        Create a new local project
        
        Args:
            display_name: The display name for the project
            
        Returns:
            The unique project ID
        """
        try:
            # Generate a unique ID based on timestamp and name
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            project_id = f"local_{timestamp}_{display_name.lower().replace(' ', '_')}"
            
            self.projects[project_id] = {
                "id": project_id,
                "display_name": display_name,
                "created_at": datetime.now().isoformat(),
                "documents": {}  # Store as dict: {document_name: {indexed_at, ...}}
            }
            
            self._save_projects()
            print(f"✅ Created local project: {display_name} (ID: {project_id})")
            return project_id
        except Exception as e:
            print(f"❌ Error creating local project: {e}")
            raise
    
    def get_project(self, project_id: str) -> Optional[dict]:
        """Get a project by ID"""
        return self.projects.get(project_id)
    
    def list_projects(self) -> List[dict]:
        """Get all local projects"""
        return list(self.projects.values())
    
    def delete_project(self, project_id: str) -> bool:
        """Delete a project"""
        if project_id in self.projects:
            del self.projects[project_id]
            self._save_projects()
            print(f"✅ Deleted local project: {project_id}")
            return True
        return False
    
    def add_document(self, project_id: str, document_name: str) -> bool:
        """Add a document to a project with metadata"""
        if project_id in self.projects:
            self.projects[project_id]["documents"][document_name] = {
                "indexed_at": datetime.now().isoformat()
            }
            self._save_projects()
            print(f"✅ Added document to project: {document_name}")
            return True
        return False
    
    def remove_document(self, project_id: str, document_name: str) -> bool:
        """Remove a document from a project"""
        if project_id in self.projects:
            if document_name in self.projects[project_id]["documents"]:
                del self.projects[project_id]["documents"][document_name]
                self._save_projects()
                print(f"✅ Removed document from project: {document_name}")
                return True
        return False
    
    def get_all_projects(self) -> dict:
        """Get all projects as a deep copy"""
        return deepcopy(self.projects)


# Global instance
local_project_storage = None

def get_local_project_storage() -> LocalProjectStorage:
    """Get or create the global local project storage instance"""
    global local_project_storage
    if local_project_storage is None:
        local_project_storage = LocalProjectStorage()
    return local_project_storage
