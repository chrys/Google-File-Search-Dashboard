import json
import os
from pathlib import Path

class PromptStorage:
    """Handles loading and saving project prompts to a JSON file"""
    
    def __init__(self, data_dir: str = None):
        """
        Initialize prompt storage
        
        Args:
            data_dir: Directory to store prompts.json file. Defaults to project root/configuration.
        """
        if data_dir is None:
            # Get the project root (parent of src) then add configuration subdirectory
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(project_root, 'configuration')
        
        self.data_dir = data_dir
        self.prompts_file = os.path.join(data_dir, 'prompts.json')
        self.prompts = self._load_prompts()
    
    def _load_prompts(self) -> dict:
        """Load prompts from JSON file or create empty dict if file doesn't exist"""
        if os.path.exists(self.prompts_file):
            try:
                with open(self.prompts_file, 'r') as f:
                    content = f.read().strip()
                    if not content:
                        print(f"📝 Prompts file is empty at {self.prompts_file}. Starting with empty prompts.")
                        return {}
                    prompts = json.loads(content)
                    print(f"✅ Loaded {len(prompts)} prompts from {self.prompts_file}")
                    return prompts
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️ Error reading prompts file: {e}. Starting with empty prompts.")
                return {}
        else:
            print(f"📝 No prompts file found at {self.prompts_file}. Creating new one on first save.")
            return {}
    
    def _save_prompts(self):
        """Save prompts to JSON file"""
        try:
            # Ensure directory exists
            os.makedirs(self.data_dir, exist_ok=True)
            
            with open(self.prompts_file, 'w') as f:
                json.dump(self.prompts, f, indent=2)
            print(f"✅ Saved prompts to {self.prompts_file}")
        except IOError as e:
            print(f"❌ Error saving prompts: {e}")
    
    def get_prompt(self, store_id: str) -> str:
        """
        Get prompt for a specific store
        
        Args:
            store_id: The file search store ID
            
        Returns:
            The custom prompt for the store, or empty string if not found
        """
        return self.prompts.get(store_id, "")
    
    def set_prompt(self, store_id: str, prompt: str):
        """
        Set/update prompt for a specific store and save to file
        
        Args:
            store_id: The file search store ID
            prompt: The custom system prompt
        """
        self.prompts[store_id] = prompt
        self._save_prompts()
    
    def delete_prompt(self, store_id: str):
        """
        Delete prompt for a specific store and save to file
        
        Args:
            store_id: The file search store ID
        """
        if store_id in self.prompts:
            del self.prompts[store_id]
            self._save_prompts()
    
    def get_all_prompts(self) -> dict:
        """Get all prompts"""
        return self.prompts.copy()


# Global instance
prompt_storage = None

def get_prompt_storage() -> PromptStorage:
    """Get or create the global prompt storage instance"""
    global prompt_storage
    if prompt_storage is None:
        prompt_storage = PromptStorage()
    return prompt_storage
