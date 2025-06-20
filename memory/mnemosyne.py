# memory/mnemosyne.py

import json
import os
from datetime import datetime
from typing import List, Dict, Optional

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory_store.json")

class MemoryManager:
    def __init__(self, filepath="memory/memory.json"):
        self.filepath = filepath
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        self._load_memory()

    def _load_memory(self):
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r") as f:
                try:
                    self.memories = json.load(f)
                except json.JSONDecodeError:
                    self.memories = []
        else:
            self.memories = []
            self._save_memory()

    def _save_memory(self):
        with open(MEMORY_FILE, "w") as f:
            json.dump(self.memories, f, indent=2)

    def add_memory(self, content: str, metadata: Optional[Dict] = None):
        entry = {
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        self.memories.append(entry)
        self._save_memory()

    def save_entry(self, content: str, metadata: Optional[Dict] = None):
        self.add_memory(content=content, metadata=metadata)

    def save_interaction(self, content: str, metadata: Optional[Dict] = None):
        self.add_memory(content=content, metadata=metadata)        

    def search_memory(self, query: str) -> List[Dict]:
        return [m for m in self.memories if query.lower() in m["content"].lower()]

    def all_memories(self) -> List[Dict]:
        return self.memories

    def clear_memory(self):
        self.memories = []
        self._save_memory()
