# File: execution/dev-tools/history.py
"""
Conversation history management with multi-conversation support,
JSON persistence, and a standard OpenAI message schema.
"""
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import aiofiles

from .config import config

class HistoryManager:
    """Manages conversation history with a robust, compliant message schema."""
    
    def __init__(self):
        self.history_path = config.history_path
        self.max_history = config.max_history
        self._history: Dict[str, List[Dict[str, Any]]] = {}
    
    async def load(self):
        """Loads conversation history from disk asynchronously."""
        try:
            if self.history_path.exists():
                async with aiofiles.open(self.history_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    if content:
                        self._history = json.loads(content)
        except Exception as e:
            print(f"Warning: Could not load history: {e}. Starting fresh.")
            self._history = {}
    
    async def save(self):
        """Saves conversation history to disk asynchronously."""
        try:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(self.history_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(self._history, indent=2))
        except Exception as e:
            print(f"Warning: Could not save history: {e}")
    
    async def add_message(self, conversation_id: str, role: str, content: str):
        """Adds a message to the history, respecting the max history limit."""
        if conversation_id not in self._history:
            self._history[conversation_id] = []
        
        self._history[conversation_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Prune old messages if history exceeds the max size
        if len(self._history[conversation_id]) > self.max_history:
            self._history[conversation_id] = self._history[conversation_id][-self.max_history:]
        
        await self.save()
    
    def get_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Gets messages for a conversation in the exact format the Agent needs."""
        messages = self._history.get(conversation_id, [])
        # Strip metadata (like timestamp) before sending to the LLM.
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]

    def get_conversations(self) -> List[Dict[str, Any]]:
        """Gets metadata for all conversations, for use in a UI."""
        # Implementation from Codebase V2 is excellent here.
        pass # Placeholder for brevity, use V2's implementation.
    
    async def clear(self, conversation_id: Optional[str] = None):
        """Clears history for a specific conversation or all conversations."""
        # Implementation from Codebase V2 is excellent here.
        pass # Placeholder for brevity, use V2's implementation.
