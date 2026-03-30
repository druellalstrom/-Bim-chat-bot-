import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
from datetime import datetime

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

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "documents" not in st.session_state:
    st.session_state.documents = []

# Sidebar for document upload
with st.sidebar:
    st.title("📁 Document Upload")
    st.write("Upload documents to enhance AI responses with RAG")
    
    uploaded_file = st.file_uploader(
        "Choose a text file",
        type=['txt', 'md'],
        help="Upload documents for the AI to reference"
    )
    
    if uploaded_file is not None:
        content = uploaded_file.read().decode('utf-8')
        if content not in st.session_state.documents:
            st.session_state.documents.append(content)
            st.success(f"✓ Added: {uploaded_file.name}")
    
    st.write(f"**Documents loaded:** {len(st.session_state.documents)}")
    
    if st.button("🗑️ Clear Documents"):
        st.session_state.documents = []
        st.rerun()
    
    if st.button("🔄 Clear Chat History"):
        st.session_state.messages = []
        st.rerun()
    
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
                "content": f"You are BIM-CHATBOT, a helpful and knowledgeable assistant. "
                           f"The current date and time is {now.strftime('%A, %B %d, %Y at %I:%M %p')}. "
                           f"Always use this when answering questions about dates, times, days, or schedules. "
                           f"Provide accurate, up-to-date information."
            }
            api_messages = [system_msg] + st.session_state.messages

            # Stream response for ChatGPT-like effect
            stream = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=api_messages,
                temperature=0.7,
                max_tokens=1000,
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
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.info("💡 Make sure your API key is valid in the .env file")
