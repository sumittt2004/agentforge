"""
AgentForge Tools Module
Defines all available tools and their implementations
"""

import json
import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Any
import requests
from duckduckgo_search import DDGS


class ToolRegistry:
    """Registry of all available tools for the agent"""
    
    @staticmethod
    def get_tool_definitions() -> List[Dict[str, Any]]:
        """Returns OpenAI function calling format tool definitions"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for current information, news, facts, or answers. Use this when you need up-to-date information beyond your knowledge cutoff.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query (e.g., 'latest AI news', 'weather in Paris')"
                            },
                            "num_results": {
                                "type": "integer",
                                "description": "Number of results to return (1-10)",
                                "default": 3
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculator",
                    "description": "Evaluate mathematical expressions and perform calculations. Supports basic arithmetic, exponents, and common math functions (sqrt, sin, cos, log, etc.).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {
                                "type": "string",
                                "description": "Mathematical expression to evaluate (e.g., '2 + 2', 'sqrt(16)', '10 ** 2', 'sin(3.14159/2)')"
                            }
                        },
                        "required": ["expression"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get current weather information for any city in the world. Returns temperature, conditions, humidity, and wind speed.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "City name (e.g., 'London', 'New York', 'Tokyo')"
                            }
                        },
                        "required": ["city"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "save_note",
                    "description": "Save a note, task, or reminder to the database for later retrieval. Perfect for to-do lists, important information, or things to remember.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Brief title for the note (e.g., 'Shopping List', 'Meeting Notes')"
                            },
                            "content": {
                                "type": "string",
                                "description": "The full content of the note"
                            },
                            "tags": {
                                "type": "string",
                                "description": "Optional comma-separated tags (e.g., 'work,urgent')"
                            }
                        },
                        "required": ["title", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_notes",
                    "description": "Retrieve saved notes from the database. Can search by keyword or retrieve all notes.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_term": {
                                "type": "string",
                                "description": "Optional search term to filter notes by title, content, or tags"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of notes to return (default: 10)",
                                "default": 10
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_datetime",
                    "description": "Get the current date, time, and day of the week.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            }
        ]


class ToolExecutor:
    """Executes tools and returns results"""
    
    def __init__(self, db_path: str = "database/agentforge.db"):
        self.db_path = db_path
        self._ensure_database()
    
    def _ensure_database(self):
        """Ensure database and tables exist"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool by name with given arguments"""
        
        tool_methods = {
            'web_search': self.web_search,
            'calculator': self.calculator,
            'get_weather': self.get_weather,
            'save_note': self.save_note,
            'get_notes': self.get_notes,
            'get_current_datetime': self.get_current_datetime
        }
        
        if tool_name not in tool_methods:
            return f"❌ Error: Unknown tool '{tool_name}'"
        
        try:
            # Special handling for tools that don't need arguments
            if tool_name == 'get_current_datetime':
                result = tool_methods[tool_name]()
            elif tool_name == 'get_notes' and not arguments:
                result = tool_methods[tool_name]()
            else:
                # Filter out None values from arguments
                clean_args = {k: v for k, v in arguments.items() if v is not None}
                result = tool_methods[tool_name](**clean_args)
            return result
        except Exception as e:
            return f"❌ Error executing {tool_name}: {str(e)}"
    
    def web_search(self, query: str, num_results: int = 3) -> str:
        """Search the web using DuckDuckGo"""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=num_results))
            
            if not results:
                return "No results found for your search query."
            
            formatted_results = ["🔍 Search Results:\n"]
            for i, result in enumerate(results, 1):
                formatted_results.append(
                    f"{i}. **{result['title']}**\n"
                    f"   🔗 {result['href']}\n"
                    f"   📝 {result['body']}\n"
                )
            
            return "\n".join(formatted_results)
        
        except Exception as e:
            return f"❌ Search error: {str(e)}"
    
    def calculator(self, expression: str) -> str:
        """Safely evaluate mathematical expressions"""
        try:
            import math
            
            # Safe namespace with math functions
            safe_dict = {
                'sqrt': math.sqrt,
                'sin': math.sin,
                'cos': math.cos,
                'tan': math.tan,
                'log': math.log,
                'log10': math.log10,
                'exp': math.exp,
                'pi': math.pi,
                'e': math.e,
                'abs': abs,
                'round': round,
                'pow': pow
            }
            
            # Evaluate expression
            result = eval(expression, {"__builtins__": {}}, safe_dict)
            
            return f"🧮 Calculation Result:\n{expression} = **{result}**"
        
        except Exception as e:
            return f"❌ Calculation error: {str(e)}\nMake sure your expression is valid (e.g., '2 + 2', 'sqrt(16)')"
    
    def get_weather(self, city: str) -> str:
        """Get weather using free wttr.in API"""
        try:
            url = f"https://wttr.in/{city}?format=j1"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                current = data['current_condition'][0]
                
                return (
                    f"🌤️ **Weather in {city}:**\n\n"
                    f"🌡️ Temperature: {current['temp_C']}°C ({current['temp_F']}°F)\n"
                    f"☁️ Condition: {current['weatherDesc'][0]['value']}\n"
                    f"💧 Humidity: {current['humidity']}%\n"
                    f"💨 Wind: {current['windspeedKmph']} km/h ({current['windspeedMiles']} mph)\n"
                    f"👁️ Visibility: {current['visibility']} km\n"
                    f"🌡️ Feels like: {current['FeelsLikeC']}°C ({current['FeelsLikeF']}°F)"
                )
            else:
                return f"❌ Could not fetch weather for '{city}'. Status code: {response.status_code}"
        
        except Exception as e:
            return f"❌ Weather error for '{city}': {str(e)}"
        except requests.Timeout:
            return f"⏱️ Weather service timed out for '{city}'. The service may be temporarily unavailable."
        except requests.ConnectionError:
            return f"🌐 Could not connect to weather service for '{city}'. Please check your internet connection."
    
    def save_note(self, title: str, content: str, tags: str = None) -> str:
        """Save a note to the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)',
                (title, content, tags)
            )
            
            note_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return (
                f"✅ **Note Saved Successfully!**\n\n"
                f"📝 Title: {title}\n"
                f"🆔 Note ID: {note_id}\n"
                f"📌 Tags: {tags if tags else 'None'}"
            )
        
        except Exception as e:
            return f"❌ Error saving note: {str(e)}"
    
    def get_notes(self, search_term: str = None, limit: int = 10) -> str:
        """Retrieve notes from the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if search_term:
                cursor.execute(
                    '''SELECT id, title, content, tags, created_at 
                       FROM notes 
                       WHERE title LIKE ? OR content LIKE ? OR tags LIKE ?
                       ORDER BY created_at DESC 
                       LIMIT ?''',
                    (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%', limit)
                )
            else:
                cursor.execute(
                    '''SELECT id, title, content, tags, created_at 
                       FROM notes 
                       ORDER BY created_at DESC 
                       LIMIT ?''',
                    (limit,)
                )
            
            results = cursor.fetchall()
            conn.close()
            
            if not results:
                return "📝 No notes found." + (f" Search term: '{search_term}'" if search_term else "")
            
            formatted_notes = [f"📚 **Found {len(results)} note(s):**\n"]
            
            for note_id, title, content, tags, created_at in results:
                formatted_notes.append(
                    f"\n📝 **{title}** (ID: {note_id})\n"
                    f"   {content}\n"
                    f"   📌 Tags: {tags if tags else 'None'}\n"
                    f"   🕒 Created: {created_at}"
                )
            
            return "\n".join(formatted_notes)
        
        except Exception as e:
            return f"❌ Error retrieving notes: {str(e)}"
    
    def get_current_datetime(self) -> str:
        """Get current date and time"""
        now = datetime.now()
        
        return (
            f"🕒 **Current Date & Time:**\n\n"
            f"📅 Date: {now.strftime('%A, %B %d, %Y')}\n"
            f"⏰ Time: {now.strftime('%I:%M:%S %p')}\n"
            f"📊 Week: {now.strftime('Week %W of %Y')}"
        )