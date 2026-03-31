import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import io
import base64
from datetime import datetime
from pathlib import Path

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import docx
except ImportError:
    docx = None

try:
    import openpyxl
except ImportError:
    openpyxl = None

import csv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
@st.cache_resource
def get_openai_client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

client = get_openai_client()

# Page config
st.set_page_config(
    page_title="BIM-CHATBOT",
    page_icon="🏗️",
    layout="wide"
)

# Chat history file management
HISTORY_DIR = Path("chat_histories")
HISTORY_DIR.mkdir(exist_ok=True)

def save_conversation(name, messages):
    """Save a conversation to a JSON file."""
    filepath = HISTORY_DIR / f"{name}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({"name": name, "messages": messages, "saved_at": datetime.now().isoformat()}, f, indent=2)

def load_conversation(name):
    """Load a conversation from a JSON file."""
    filepath = HISTORY_DIR / f"{name}.json"
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["messages"]

def list_conversations():
    """List all saved conversations."""
    convos = []
    for f in sorted(HISTORY_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        with open(f, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        convos.append({"name": f.stem, "saved_at": data.get("saved_at", "")})
    return convos

def delete_conversation(name):
    """Delete a saved conversation."""
    filepath = HISTORY_DIR / f"{name}.json"
    filepath.unlink(missing_ok=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "documents" not in st.session_state:
    st.session_state.documents = []
if "current_chat_name" not in st.session_state:
    st.session_state.current_chat_name = None
if "images" not in st.session_state:
    st.session_state.images = []
if "selected_model" not in st.session_state:
    st.session_state.selected_model = "gpt-4o"

# Available models
MODELS = {
    "GPT-4o (Best accuracy)": "gpt-4o",
    "GPT-4o Mini (Fast & cheap)": "gpt-4o-mini",
    "GPT-4 Turbo": "gpt-4-turbo",
    "GPT-4": "gpt-4",
    "GPT-3.5 Turbo (Budget)": "gpt-3.5-turbo",
    "o1 (Advanced reasoning)": "o1",
    "o1-mini (Fast reasoning)": "o1-mini",
    "o3-mini (Latest reasoning)": "o3-mini",
}

# Sidebar
with st.sidebar:
    # --- New Chat ---
    st.title("🏗️ BIM-CHATBOT")

    # --- Model Selector ---
    selected_label = st.selectbox(
        "🧠 AI Model",
        options=list(MODELS.keys()),
        index=list(MODELS.values()).index(st.session_state.selected_model),
        help="Choose the AI model. Better models cost more but are more accurate."
    )
    st.session_state.selected_model = MODELS[selected_label]

    if st.button("➕ New Chat", use_container_width=True):
        # Auto-save current chat before starting new one
        if st.session_state.messages:
            auto_name = datetime.now().strftime("Chat %Y-%m-%d %H:%M")
            if st.session_state.current_chat_name:
                auto_name = st.session_state.current_chat_name
            save_conversation(auto_name, st.session_state.messages)
        st.session_state.messages = []
        st.session_state.current_chat_name = None
        st.rerun()

    # --- Chat History ---
    st.divider()
    st.subheader("💬 Chat History")
    conversations = list_conversations()
    if conversations:
        for convo in conversations:
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(f"📄 {convo['name']}", key=f"load_{convo['name']}", use_container_width=True):
                    st.session_state.messages = load_conversation(convo["name"])
                    st.session_state.current_chat_name = convo["name"]
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"del_{convo['name']}"):
                    delete_conversation(convo["name"])
                    if st.session_state.current_chat_name == convo["name"]:
                        st.session_state.current_chat_name = None
                    st.rerun()
    else:
        st.caption("No saved chats yet.")

    # --- Save Current Chat ---
    st.divider()
    save_name = st.text_input("Save chat as:", value=st.session_state.current_chat_name or "")
    if st.button("💾 Save Chat", use_container_width=True):
        if save_name and st.session_state.messages:
            save_conversation(save_name, st.session_state.messages)
            st.session_state.current_chat_name = save_name
            st.success(f"✓ Saved: {save_name}")
            st.rerun()

    # --- Document Upload ---
    st.divider()
    st.subheader("📁 Document Upload")
    uploaded_file = st.file_uploader(
        "Upload any file",
        type=['txt', 'md', 'pdf', 'docx', 'doc', 'csv', 'xlsx', 'xls', 'json', 'xml', 'html', 'py', 'js', 'ts', 'java', 'c', 'cpp', 'h', 'css', 'sql', 'yaml', 'yml', 'toml', 'ini', 'cfg', 'log', 'rtf', 'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg'],
        help="Upload documents or images for the AI to reference"
    )
    
    if uploaded_file is not None:
        content = None
        fname = uploaded_file.name.lower()
        
        try:
            if fname.endswith('.pdf'):
                if PyPDF2:
                    reader = PyPDF2.PdfReader(uploaded_file)
                    content = "".join(page.extract_text() or "" for page in reader.pages)
                else:
                    st.warning("Install PyPDF2 to read PDFs: pip install PyPDF2")
            elif fname.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')):
                img_bytes = uploaded_file.read()
                b64 = base64.b64encode(img_bytes).decode('utf-8')
                ext = fname.rsplit('.', 1)[-1]
                mime = f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}"
                img_data = {"name": uploaded_file.name, "b64": b64, "mime": mime}
                if img_data not in st.session_state.images:
                    st.session_state.images.append(img_data)
                    st.success(f"✓ Image added: {uploaded_file.name}")
                    st.image(img_bytes, caption=uploaded_file.name, width=200)
                content = None  # Images handled separately
            elif fname.endswith('.svg'):
                content = uploaded_file.read().decode('utf-8', errors='replace')
            elif fname.endswith('.docx'):
                if docx:
                    doc_file = docx.Document(uploaded_file)
                    content = "\n".join(p.text for p in doc_file.paragraphs)
                else:
                    st.warning("Install python-docx to read Word files: pip install python-docx")
            elif fname.endswith(('.xlsx', '.xls')):
                if openpyxl:
                    wb = openpyxl.load_workbook(uploaded_file, data_only=True)
                    sheets_text = []
                    for sheet_name in wb.sheetnames:
                        ws = wb[sheet_name]
                        sheets_text.append(f"--- Sheet: {sheet_name} ---")
                        for row in ws.iter_rows(values_only=True):
                            sheets_text.append("\t".join(str(cell) if cell is not None else "" for cell in row))
                    content = "\n".join(sheets_text)
                else:
                    st.warning("Install openpyxl to read Excel files: pip install openpyxl")
            elif fname.endswith('.csv'):
                text = uploaded_file.read().decode('utf-8', errors='replace')
                content = text
            elif fname.endswith('.json'):
                raw = uploaded_file.read().decode('utf-8', errors='replace')
                data = json.loads(raw)
                content = json.dumps(data, indent=2)
            else:
                # Try to read as plain text
                content = uploaded_file.read().decode('utf-8', errors='replace')
        except Exception as e:
            st.error(f"Error reading {uploaded_file.name}: {e}")
        
        if content and content.strip():
            if content not in st.session_state.documents:
                st.session_state.documents.append(content)
                st.success(f"✓ Added: {uploaded_file.name}")
        elif content is not None and not content.strip():
            st.warning(f"No readable text found in {uploaded_file.name}")
    
    st.write(f"**Documents loaded:** {len(st.session_state.documents)}")
    st.write(f"**Images loaded:** {len(st.session_state.images)}")
    
    if st.button("🗑️ Clear Documents"):
        st.session_state.documents = []
        st.session_state.images = []
        st.rerun()
    
    # --- Token Usage ---
    st.divider()
    st.write("**Token Usage**")
    total_chars = sum(len(msg["content"]) for msg in st.session_state.messages)
    st.metric("Estimated Tokens", f"~{total_chars // 4}")

# Main chat interface
st.title("🏗️ BIM-CHATBOT")
st.caption("Your intelligent BIM assistant powered by document retrieval")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Retrieve relevant context from documents
def retrieve_context(query: str, top_k: int = 2) -> str:
    if not st.session_state.documents:
        return ""
    
    query_words = set(query.lower().split())
    scored_docs = []
    
    for doc in st.session_state.documents:
        doc_words = set(doc.lower().split())
        score = len(query_words & doc_words)
        scored_docs.append((score, doc))
    
    scored_docs.sort(reverse=True, key=lambda x: x[0])
    relevant = [doc for score, doc in scored_docs[:top_k] if score > 0]
    
    return "\n\n".join(relevant) if relevant else ""

# Chat input
if prompt := st.chat_input("Ask me anything..."):
    # Retrieve context from documents
    context = retrieve_context(prompt)
    
    # Build message with context
    if context:
        enhanced_prompt = f"Context from documents:\n{context}\n\nUser question: {prompt}"
        display_prompt = prompt  # Show original to user
    else:
        enhanced_prompt = prompt
        display_prompt = prompt
    
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": enhanced_prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(display_prompt)
    
    # Get AI response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            # Build messages with system prompt including current date/time
            now = datetime.now()
            system_msg = {
                "role": "system",
                "content": (
                    f"You are BIM-CHATBOT, an expert-level AI assistant that prioritizes ACCURACY above all else. "
                    f"The current date and time is {now.strftime('%A, %B %d, %Y at %I:%M %p')}.\n\n"
                    f"CORE RULES:\n"
                    f"- ACCURACY IS YOUR #1 PRIORITY. Never guess or make up information.\n"
                    f"- If you are not 100% sure about something, say so honestly.\n"
                    f"- Always think through your answer carefully before responding.\n\n"
                    f"MATH INSTRUCTIONS:\n"
                    f"- ALWAYS solve math problems step by step with clear labels (Step 1, Step 2, etc.).\n"
                    f"- Show ALL work — do not skip steps.\n"
                    f"- Double-check every calculation before giving your final answer.\n"
                    f"- State the FINAL ANSWER in bold on its own line.\n"
                    f"- Explain WHY each step works so the user learns.\n"
                    f"- For word problems, identify what is given, what is asked, then solve.\n"
                    f"- Use proper mathematical notation and formatting.\n\n"
                    f"ENGLISH / GRAMMAR / WRITING:\n"
                    f"- Provide grammatically perfect responses.\n"
                    f"- When correcting grammar, explain the rule behind the correction.\n"
                    f"- For essays or writing help, follow proper structure (intro, body, conclusion).\n"
                    f"- When asked about vocabulary, give clear definitions, synonyms, and example sentences.\n"
                    f"- For literature questions, cite specific evidence from the text.\n\n"
                    f"SCIENCE / HISTORY / GENERAL KNOWLEDGE:\n"
                    f"- Provide factual, well-sourced information.\n"
                    f"- Use specific dates, names, and data — not vague statements.\n"
                    f"- Distinguish between established facts and theories/opinions.\n"
                    f"- If a topic is debated, present multiple perspectives fairly.\n\n"
                    f"FORMATTING:\n"
                    f"- Use headers, bullet points, and bold text for readability.\n"
                    f"- Keep explanations clear and well-organized.\n"
                    f"- Adapt your explanation depth to the complexity of the question."
                )
            }
            api_messages = [system_msg] + st.session_state.messages

            # If images are uploaded, attach them to the last user message for vision
            if st.session_state.images:
                # Build multimodal content for the last user message
                last_user_idx = None
                for i in range(len(api_messages) - 1, -1, -1):
                    if api_messages[i]["role"] == "user":
                        last_user_idx = i
                        break
                if last_user_idx is not None:
                    text_content = api_messages[last_user_idx]["content"]
                    multimodal_content = [{"type": "text", "text": text_content}]
                    for img in st.session_state.images:
                        multimodal_content.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:{img['mime']};base64,{img['b64']}"}
                        })
                    api_messages[last_user_idx] = {"role": "user", "content": multimodal_content}

            # Stream response for ChatGPT-like effect
            use_model = st.session_state.selected_model
            # o1/o3 models don't support streaming or temperature
            is_reasoning = use_model.startswith(("o1", "o3"))

            if is_reasoning:
                response = client.chat.completions.create(
                    model=use_model,
                    messages=api_messages,
                    max_completion_tokens=4000,
                )
                full_response = response.choices[0].message.content
                message_placeholder.markdown(full_response)
            else:
                stream = client.chat.completions.create(
                    model=use_model,
                    messages=api_messages,
                    temperature=0.1,
                    max_tokens=4000,
                    stream=True
                )
                
                full_response = ""
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        full_response += chunk.choices[0].delta.content
                        message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
            
            # Add assistant response to history
            st.session_state.messages.append({"role": "assistant", "content": full_response})

            # Auto-save after each response
            if st.session_state.current_chat_name:
                save_conversation(st.session_state.current_chat_name, st.session_state.messages)
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.info("💡 Make sure your API key is valid in the .env file")
