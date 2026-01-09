"""
AgentForge Streamlit Application
Interactive UI for the AI agent
"""

import streamlit as st
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agentforge import AgentForge
from datetime import datetime
import time

# Page configuration
st.set_page_config(
    page_title="AgentForge - AI Agent Platform",
    page_icon="🔨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* Main theme */
    .stApp {
       background: linear-gradient(135deg, #ff5858 0%, #f09819 50%, #8e2de2 100%);
    }
    
    /* Content area */
    .main .block-container {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 10px;
        padding: 2rem;
    }
    
    /* Tool call styling */
    .tool-call {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Tool result styling */
    .tool-result {
        background-color: #f0f9ff;
        border: 2px solid #0ea5e9;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    
    /* Metrics */
    .metric-card {
        background: rgba(255, 255, 255, 0.95);
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(15, 23, 42, 0.18);
        text-align: center;
        margin: 10px 0;
        color: #0f172a;
    }
    
    /* Thinking animation */
    .agent-thinking {
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    /* Headers */
    h1 {
        color: #667eea;
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 5px;
        font-weight: bold;
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, #5568d3 0%, #653a8b 100%);
        border: none;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    """Initialize all session state variables"""
    if 'agent' not in st.session_state:
        st.session_state.agent = None
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'session_id' not in st.session_state:
        st.session_state.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if 'stats' not in st.session_state:
        st.session_state.stats = {
            'messages_sent': 0,
            'tools_used': 0,
            'searches_made': 0,
            'notes_saved': 0,
            'calculations': 0,
            'weather_checks': 0
        }

init_session_state()

# Sidebar
with st.sidebar:
    st.markdown("# 🔨 AgentForge")
    st.markdown("*Autonomous AI Agent Platform*")
    st.markdown("---")
    
    # Session Statistics
    st.subheader("📊 Session Stats")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("💬 Messages", st.session_state.stats['messages_sent'])
        st.metric("🔧 Tools Used", st.session_state.stats['tools_used'])
        st.metric("🔍 Searches", st.session_state.stats['searches_made'])
    with col2:
        st.metric("📝 Notes", st.session_state.stats['notes_saved'])
        st.metric("🧮 Calculations", st.session_state.stats['calculations'])
        st.metric("🌤️ Weather", st.session_state.stats['weather_checks'])
    
    st.markdown("---")
    
    # Configuration
    with st.expander("⚙️ Configuration", expanded=st.session_state.agent is None):
        
        api_key = st.text_input(
            "Groq API Key",
            type="password",
            value=os.getenv("GROQ_API_KEY", ""),
            help="Get your free key at: https://console.groq.com"
        )
        
        model = st.selectbox(
            "Model",
            ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "mixtral-8x7b-32768"],
            help="Llama 3.3 is the latest and most capable"
        )
        
        temperature = st.slider(
            "Temperature",
            0.0, 1.0, 0.7, 0.1,
            help="Higher = more creative, Lower = more focused"
        )
        
        max_iterations = st.slider(
            "Max Tool Iterations",
            1, 10, 5,
            help="Maximum number of tool use rounds"
        )
        
        if st.button("🚀 Initialize Agent", type="primary", use_container_width=True):
            if api_key:
                os.environ["GROQ_API_KEY"] = api_key
                
                try:
                    with st.spinner("Initializing AgentForge..."):
                        st.session_state.agent = AgentForge(
                            model=model,
                            session_id=st.session_state.session_id,
                            max_iterations=max_iterations,
                            temperature=temperature
                        )
                    st.success(f"✅ Agent initialized with Groq!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
            else:
                st.error("Please enter your Groq API key")
    
    # Tools Information
    with st.expander("🛠️ Available Tools"):
        st.markdown("""
        **Enabled Tools:**
        
        🔍 **Web Search**  
        Search current information
        
        🧮 **Calculator**  
        Math expressions & functions
        
        🌤️ **Weather**  
        Global weather data
        
        📝 **Notes**  
        Save & retrieve notes
        
        ⏰ **DateTime**  
        Current date & time
        """)
    
    # Session Management
    with st.expander("💾 Session"):
        st.text(f"ID: ...{st.session_state.session_id[-12:]}")
        
        if st.session_state.agent:
            session_info = st.session_state.agent.get_session_info()
            if session_info:
                st.text(f"Messages: {session_info['message_count']}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Clear", use_container_width=True):
                if st.session_state.agent:
                    st.session_state.agent.clear_history()
                st.session_state.messages = []
                st.session_state.stats = {
                    'messages_sent': 0,
                    'tools_used': 0,
                    'searches_made': 0,
                    'notes_saved': 0,
                    'calculations': 0,
                    'weather_checks': 0
                }
                st.rerun()
        
        with col2:
            if st.button("🆕 New", use_container_width=True):
                st.session_state.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                st.session_state.messages = []
                st.session_state.agent = None
                st.session_state.stats = {
                    'messages_sent': 0,
                    'tools_used': 0,
                    'searches_made': 0,
                    'notes_saved': 0,
                    'calculations': 0,
                    'weather_checks': 0
                }
                st.rerun()
    
    st.markdown("---")
    
    # Footer
    st.markdown("""
    <div style='text-align: center; font-size: 12px; color: #666;'>
        <b>AgentForge v1.0</b><br>
        Built with ❤️ using Streamlit
    </div>
    """, unsafe_allow_html=True)

# Main Content
if st.session_state.agent is None:
    # Welcome Page
    st.markdown("""
    <div style='text-align: center; padding: 30px 0;'>
        <h1 style='font-size: 3.5em; margin-bottom: 0;'>🔨 AgentForge</h1>
        <p style='font-size: 1.3em; color: #666; margin-top: 10px;'>
            Build Autonomous AI Agents with Tool Use & Memory
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Features
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class='metric-card'>
            <h2 style='color: #667eea; font-size: 3em; margin: 0;'>🔍</h2>
            <h3>Information Retrieval</h3>
            <p style='color: #666;'>Search web, check weather, get current time and more</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class='metric-card'>
            <h2 style='color: #764ba2; font-size: 3em; margin: 0;'>🧠</h2>
            <h3>Persistent Memory</h3>
            <p style='color: #666;'>Remembers conversations and saves notes for later</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class='metric-card'>
            <h2 style='color: #0ea5e9; font-size: 3em; margin: 0;'>⚡</h2>
            <h3>Autonomous Actions</h3>
            <p style='color: #666;'>Multi-step reasoning and intelligent tool chaining</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Example Prompts
    st.subheader("💡 Try These Examples")
    
    examples = [
        ("🔍 Latest News", "Search for the latest AI news and summarize the top 3 stories"),
        ("🌤️ Weather Compare", "Compare the weather in London, Tokyo, and New York City"),
        ("🧮 Mortgage Calculator", "Calculate monthly payment on a $350,000 loan at 6.5% interest for 30 years"),
        ("📝 Shopping List", "Save a note titled 'Shopping List' with items: milk, eggs, bread, coffee"),
        ("🤖 Multi-Step", "What's today's date, and do I have any saved notes about shopping?")
    ]
    
    col1, col2 = st.columns(2)
    
    for i, (label, prompt) in enumerate(examples):
        with col1 if i % 2 == 0 else col2:
            if st.button(label, key=f"example_{i}", use_container_width=True):
                st.info("👈 Please initialize the agent in the sidebar first!")
    
    st.markdown("---")
    
    # Getting Started
    st.subheader("🚀 Getting Started")
    
    st.markdown("""
    1. **Get a Groq API Key** - Sign up for free at [console.groq.com](https://console.groq.com) (no credit card needed!)
    2. **Configure** - Open the sidebar and enter your API key
    3. **Initialize** - Click "Initialize Agent" to start
    4. **Chat** - Ask questions and watch the agent work!
    
    **Tips:**
    - The agent uses tools automatically - no need to ask
    - It can chain multiple tools together for complex tasks
    - All conversations are saved for context
    - Use the stats panel to track agent activity
    """)

else:
    # Chat Interface
    st.title("💬 Chat with AgentForge")
    
    # Display chat messages
    for msg in st.session_state.messages:
        if msg['type'] == 'user':
            with st.chat_message("user", avatar="👤"):
                st.markdown(msg['content'])
        
        elif msg['type'] == 'assistant':
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(msg['content'])
        
        elif msg['type'] == 'tool_call':
            with st.chat_message("assistant", avatar="🔧"):
                st.markdown(f"""
                <div class="tool-call">
                    <b>🔧 Using Tool:</b> {msg['content']['name']}<br>
                    <b>📋 Arguments:</b> <code>{msg['content']['args']}</code>
                </div>
                """, unsafe_allow_html=True)
        
        elif msg['type'] == 'tool_result':
            with st.chat_message("assistant", avatar="✅"):
                with st.expander("📊 View Tool Result", expanded=False):
                    st.markdown(msg['content'])
    
    # Chat input
    if prompt := st.chat_input("Ask me anything...", key="chat_input"):
        
        # Update stats
        st.session_state.stats['messages_sent'] += 1
        
        # Display user message
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        
        st.session_state.messages.append({
            'type': 'user',
            'content': prompt
        })
        
        # Get agent response
        with st.chat_message("assistant", avatar="🤖"):
            thinking_placeholder = st.empty()
            thinking_placeholder.markdown("🤔 <span class='agent-thinking'>Thinking...</span>", unsafe_allow_html=True)
            
            try:
                for step in st.session_state.agent.chat(prompt):
                    thinking_placeholder.empty()
                    
                    if step['type'] == 'tool_call':
                        # Update stats based on tool
                        st.session_state.stats['tools_used'] += 1
                        tool_name = step['content']['name']
                        
                        if tool_name == 'web_search':
                            st.session_state.stats['searches_made'] += 1
                        elif tool_name == 'save_note':
                            st.session_state.stats['notes_saved'] += 1
                        elif tool_name == 'calculator':
                            st.session_state.stats['calculations'] += 1
                        elif tool_name == 'get_weather':
                            st.session_state.stats['weather_checks'] += 1
                        
                        # Display tool call
                        st.markdown(f"""
                        <div class="tool-call">
                            <b>🔧 Using Tool:</b> {tool_name}<br>
                            <b>📋 Arguments:</b> <code>{step['content']['args']}</code>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.session_state.messages.append({
                            'type': 'tool_call',
                            'content': step['content']
                        })
                    
                    elif step['type'] == 'tool_result':
                        # Display tool result in expander
                        with st.expander("📊 View Tool Result", expanded=False):
                            st.markdown(step['content'])
                        
                        st.session_state.messages.append({
                            'type': 'tool_result',
                            'content': step['content']
                        })
                    
                    elif step['type'] == 'response':
                        st.markdown(step['content'])
                        
                        st.session_state.messages.append({
                            'type': 'assistant',
                            'content': step['content']
                        })
                    
                    elif step['type'] == 'error':
                        st.error(f"❌ {step['content']}")
                        
                        st.session_state.messages.append({
                            'type': 'assistant',
                            'content': f"Error: {step['content']}"
                        })
            
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.info("💡 Try rephrasing your question or check your API key in the sidebar")