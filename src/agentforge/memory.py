"""
AgentForge Memory Module
Manages conversation history and persistent storage
"""

import json
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Any


class ConversationMemory:
    """Manages conversation history with SQLite backend"""
    
    def __init__(self, db_path: str = 'database/agentforge.db'):
        self.db_path = db_path
        self._ensure_database()
    
    def _ensure_database(self):
        """Initialize database tables if they don't exist"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Conversations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tool_calls TEXT,
                tool_results TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tokens_used INTEGER DEFAULT 0
            )
        ''')
        
        # Sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                metadata TEXT
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_session_id 
            ON conversations(session_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON conversations(timestamp)
        ''')
        
        conn.commit()
        conn.close()
    
    def add_message(
        self, 
        session_id: str, 
        role: str, 
        content: str, 
        tool_calls: Optional[List[Dict]] = None,
        tool_results: Optional[List[str]] = None,
        tokens_used: int = 0
    ) -> int:
        """Add a message to conversation history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insert message
        cursor.execute(
            '''INSERT INTO conversations 
               (session_id, role, content, tool_calls, tool_results, tokens_used) 
               VALUES (?, ?, ?, ?, ?, ?)''',
            (
                session_id, 
                role, 
                content, 
                json.dumps(tool_calls) if tool_calls else None,
                json.dumps(tool_results) if tool_results else None,
                tokens_used
            )
        )
        
        message_id = cursor.lastrowid
        
        # Update or create session
        cursor.execute(
            '''INSERT INTO sessions (session_id, message_count, total_tokens) 
               VALUES (?, 1, ?)
               ON CONFLICT(session_id) 
               DO UPDATE SET 
                   last_active = CURRENT_TIMESTAMP,
                   message_count = message_count + 1,
                   total_tokens = total_tokens + ?''',
            (session_id, tokens_used, tokens_used)
        )
        
        conn.commit()
        conn.close()
        
        return message_id
    
    def get_conversation_history(
        self, 
        session_id: str, 
        limit: int = 20,
        include_system: bool = False
    ) -> List[Dict[str, Any]]:
        """Retrieve conversation history for a session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if include_system:
            query = '''SELECT role, content, tool_calls, tool_results, timestamp 
                       FROM conversations 
                       WHERE session_id = ? 
                       ORDER BY timestamp DESC 
                       LIMIT ?'''
        else:
            query = '''SELECT role, content, tool_calls, tool_results, timestamp 
                       FROM conversations 
                       WHERE session_id = ? AND role != 'system'
                       ORDER BY timestamp DESC 
                       LIMIT ?'''
        
        cursor.execute(query, (session_id, limit))
        results = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts (reverse to get chronological order)
        history = []
        for role, content, tool_calls, tool_results, timestamp in reversed(results):
            message = {
                "role": role,
                "content": content,
                "timestamp": timestamp
            }
            
            if tool_calls:
                message["tool_calls"] = json.loads(tool_calls)
            if tool_results:
                message["tool_results"] = json.loads(tool_results)
            
            history.append(message)
        
        return history
    
    def format_for_llm(
        self, 
        session_id: str, 
        limit: int = 10,
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Format conversation history for LLM API"""
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Get conversation history
        history = self.get_conversation_history(session_id, limit, include_system=False)
        
        # Convert to simple format for LLM
        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return messages
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            '''SELECT created_at, last_active, message_count, total_tokens, metadata 
               FROM sessions 
               WHERE session_id = ?''',
            (session_id,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "session_id": session_id,
                "created_at": result[0],
                "last_active": result[1],
                "message_count": result[2],
                "total_tokens": result[3],
                "metadata": json.loads(result[4]) if result[4] else {}
            }
        return None
    
    def clear_session(self, session_id: str) -> bool:
        """Delete all messages for a session"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM conversations WHERE session_id = ?', (session_id,))
            cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False