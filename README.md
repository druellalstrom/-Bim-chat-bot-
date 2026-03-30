# AI Chat System with RAG

A simple, efficient chat system that integrates OpenAI's API with Retrieval-Augmented Generation (RAG) capabilities.

## Features

- **Conversation History**: Maintains full chat context across messages
- **RAG Pipeline**: Retrieves relevant information from uploaded documents
- **File Attachment Support**: Add documents to enhance AI responses
- **Efficient Design**: Token usage tracking and optimized API calls
- **Persistent Storage**: Save and load chat history

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your OpenAI API key:
```bash
export OPENAI_API_KEY='your-api-key-here'
```

Or pass it directly when initializing the ChatSystem.

## Usage

### Option 1: Web Interface (Recommended - ChatGPT-like)
```bash
streamlit run app.py
```
Opens in your browser with a modern chat interface!

### Option 2: Terminal Interface
```bash
python chat_system.py
```

### Commands

- `/add <file>` - Add a document to the knowledge base
- `/save` - Save conversation history to JSON
- `/load` - Load previous conversation history
- `/clear` - Clear current conversation
- `/tokens` - Show estimated token usage
- `/quit` - Exit the program

### Example Session

```
You: /add sample_document.txt
✓ Added document: sample_document.txt

You: What are some Python best practices?
Assistant: Based on the document, here are key Python best practices...

You: /tokens
Estimated tokens used: ~245

You: /save
✓ History saved to chat_history.json
```

## Design Explanation

### 1. Chat History Management
- Stores all messages in `conversation_history` list
- Each message includes role (user/assistant) and content
- Full history sent to API for context awareness

### 2. Efficiency Optimizations
- Token limit set to 500 per response
- Simple keyword-based retrieval (no heavy embeddings)
- Only relevant document chunks included in context
- History can be cleared to reduce token usage

### 3. RAG Pipeline
- Documents stored in `document_store`
- Keyword overlap scoring for relevance
- Top-k retrieval (default: 2 most relevant docs)
- Context injected into user message before API call

### 4. File Attachment
- `/add` command loads text files
- Content stored in memory for quick retrieval
- Supports multiple documents

## Architecture

```
User Input → Retrieve Context → Enhance Message → OpenAI API → Response
                ↓                                                    ↓
          Document Store                                  Conversation History
```

## Key Learnings & Challenges

### Challenges
1. **Balancing context vs tokens**: Too much history increases costs
2. **Simple retrieval**: Keyword matching isn't perfect but is efficient
3. **File encoding**: Need to handle different text encodings

### Solutions
1. Token tracking and max_tokens limit
2. Top-k retrieval to limit context size
3. UTF-8 encoding with error handling

## Future Improvements

- Use embeddings (OpenAI embeddings API) for better retrieval
- Implement sliding window for very long conversations
- Add support for PDF, DOCX files
- Web interface with Streamlit or Flask
- Semantic chunking for large documents
