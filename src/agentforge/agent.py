"""
AgentForge Core Agent
Main AI agent with autonomous reasoning and tool use
"""

import os
import json
from typing import Generator, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

from .tools import ToolRegistry, ToolExecutor
from .memory import ConversationMemory

load_dotenv()


class AgentForge:
    """Autonomous AI Agent with tool use and memory"""
    
    def __init__(
        self,
        model: str = "llama-3.3-70b-versatile",
        session_id: str = "default",
        db_path: str = "database/agentforge.db",
        max_iterations: int = 5,
        temperature: float = 0.7
    ):
        """Initialize AgentForge"""
        self.model = model
        self.session_id = session_id
        self.max_iterations = max_iterations
        self.temperature = temperature
        
        # Initialize components
        self.memory = ConversationMemory(db_path)
        self.tool_executor = ToolExecutor(db_path)
        self.tool_registry = ToolRegistry()
        
        # Setup OpenAI client
        self._setup_client()
        
        # Get tool definitions
        self.tools = self.tool_registry.get_tool_definitions()
    
    def _setup_client(self):
        """Setup OpenAI or Groq client"""
        
        # Check for Groq API key first
        groq_key = os.getenv("GROQ_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if groq_key:
            self.client = OpenAI(
                api_key=groq_key,
                base_url="https://api.groq.com/openai/v1"
            )
            self.provider = "Groq"
        
        elif openai_key:
            self.client = OpenAI(api_key=openai_key)
            self.provider = "OpenAI"
        
        else:
            raise ValueError(
                "No API key found. Please set OPENAI_API_KEY or GROQ_API_KEY in .env file"
            )
    
    def get_system_prompt(self) -> str:
        """Get the system prompt that defines agent behavior"""
        return """You are AgentForge, an advanced AI assistant with access to multiple tools.

Your capabilities:
🔍 Web Search - Search for current information and news
🧮 Calculator - Perform mathematical calculations  
🌤️ Weather - Check weather for any city
📝 Notes - Save and retrieve notes/tasks
⏰ Time - Get current date and time

Guidelines:
1. Use tools ONCE per request - do not retry failed tools
2. If a tool fails, explain the issue to the user
3. Think step-by-step and use appropriate tools
4. Provide clear, accurate responses based on tool results
5. If you cannot complete a task, explain why

Important: Call each tool only once. If it fails, inform the user instead of retrying."""
    
    def chat(self, user_message: str) -> Generator[Dict[str, Any], None, None]:
        """Process a user message and generate response with tool use"""
        
        # Save user message to memory
        self.memory.add_message(self.session_id, "user", user_message)
        
        # Build message history
        messages = self.memory.format_for_llm(
            self.session_id,
            limit=8,
            system_prompt=self.get_system_prompt()
        )
        
        # Track tool usage and prevent duplicate calls
        tools_used = []
        tools_called = set()  # Track which tools have been called
        iteration = 0
        
        while iteration < self.max_iterations:
            iteration += 1
            
            try:
                # Call LLM
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=self.tools,
                        tool_choice="auto",
                        temperature=self.temperature,
                        max_tokens=2000
                    )
                except Exception as api_error:
                    error_str = str(api_error)
                    # If tool calling fails, respond without tools
                    if "tool_use_failed" in error_str or "failed_generation" in error_str:
                        response = self.client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            temperature=self.temperature,
                            max_tokens=2000
                        )
                    else:
                        raise api_error
                
                assistant_message = response.choices[0].message
                
                # Check if agent wants to use tools
                if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
                    
                    # Check for duplicate tool calls
                    skip_tools = False
                    for tc in assistant_message.tool_calls:
                        tool_key = f"{tc.function.name}:{tc.function.arguments}"
                        if tool_key in tools_called:
                            # Tool already called, force response
                            skip_tools = True
                            break
                    
                    if skip_tools:
                        # Add a message to force final response
                        messages.append({
                            "role": "user",
                            "content": "Please provide your final answer based on the previous tool results. Do not call tools again."
                        })
                        continue
                    
                    # Prepare assistant message for conversation history
                    messages.append({
                        "role": "assistant",
                        "content": assistant_message.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in assistant_message.tool_calls
                        ]
                    })
                    
                    # Execute each tool call
                    for tool_call in assistant_message.tool_calls:
                        function_name = tool_call.function.name
                        
                        try:
                            function_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            function_args = {}
                        
                        # Mark this tool as called
                        tool_key = f"{function_name}:{json.dumps(function_args)}"
                        tools_called.add(tool_key)
                        
                        # Yield tool call notification
                        yield {
                            'type': 'tool_call',
                            'content': {
                                'name': function_name,
                                'args': function_args
                            }
                        }
                        
                        # Execute the tool
                        tool_result = self.tool_executor.execute(
                            function_name, 
                            function_args
                        )
                        
                        # Track tool usage
                        tools_used.append({
                            'name': function_name,
                            'args': function_args,
                            'result': tool_result
                        })
                        
                        # Yield tool result
                        yield {
                            'type': 'tool_result',
                            'content': tool_result
                        }
                        
                        # Add tool result to messages
                        messages.append({
                            "role": "tool",
                            "content": tool_result,
                            "tool_call_id": tool_call.id
                        })
                    
                    # Continue loop to let agent process tool results
                    continue
                
                else:
                    # No more tool calls - agent has final response
                    final_response = assistant_message.content
                    
                    if not final_response:
                        final_response = "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."
                    
                    # Save assistant response to memory
                    self.memory.add_message(
                        self.session_id,
                        "assistant",
                        final_response,
                        tool_calls=[t['name'] for t in tools_used] if tools_used else None
                    )
                    
                    # Yield final response
                    yield {
                        'type': 'response',
                        'content': final_response
                    }
                    
                    break
            
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                
                # Save error to memory
                self.memory.add_message(
                    self.session_id,
                    "assistant",
                    f"[Error occurred: {error_msg}]"
                )
                
                yield {
                    'type': 'error',
                    'content': error_msg
                }
                break
        
        # Check if max iterations reached
        if iteration >= self.max_iterations:
            # Try to give a helpful response with what we have
            if tools_used:
                summary = "I've gathered the following information:\n\n"
                for tool in tools_used:
                    summary += f"- Used {tool['name']}: {tool['result'][:200]}...\n\n"
                summary += "\nHowever, I reached the maximum number of steps. Please ask a more specific question."
                
                self.memory.add_message(
                    self.session_id,
                    "assistant",
                    summary
                )
                
                yield {
                    'type': 'response',
                    'content': summary
                }
            else:
                yield {
                    'type': 'error',
                    'content': "Maximum iterations reached. Try breaking the task into smaller parts."
                }
    
    def clear_history(self) -> bool:
        """Clear conversation history for current session"""
        return self.memory.clear_session(self.session_id)
    
    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Get information about current session"""
        return self.memory.get_session_info(self.session_id)