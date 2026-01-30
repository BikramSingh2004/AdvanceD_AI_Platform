# AI-Powered Document & Multimedia Q&A Web Application

A full-stack web application that allows users to upload PDF documents, audio, and video files, then interact with an AI-powered chatbot to ask questions, get summaries, and navigate to specific timestamps in media files.

## Features

- **Document Upload**: Support for PDF, audio (MP3, WAV, M4A), and video (MP4, WebM) files
- **AI-Powered Q&A**: Ask questions about uploaded documents using RAG (Retrieval Augmented Generation)
- **Automatic Transcription**: Audio and video files are transcribed using OpenAI Whisper
- **Timestamp Navigation**: Click on timestamps in AI responses to jump to specific parts of media
- **Document Summaries**: Auto-generated summaries for all uploaded content
- **Real-time Streaming**: WebSocket-based streaming for chat responses
- **Vector Search**: Semantic search using FAISS and sentence-transformers

## Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: MongoDB
- **LLM**: Ollama (local inference)
- **Transcription**: OpenAI Whisper (local)
- **Vector Search**: FAISS + sentence-transformers
- **Testing**: pytest with 95%+ coverage

### Frontend
- **Framework**: React + TypeScript
- **Styling**: TailwindCSS
- **Build Tool**: Vite

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **CI/CD**: GitHub Actions

## Project Structure

```
bikram/
├── backend/
│   ├── app/
│   │   ├── api/routes/      # API endpoints
│   │   ├── database/        # MongoDB connection
│   │   ├── models/          # Pydantic models
│   │   ├── services/        # Business logic
│   │   ├── config.py        # Configuration
│   │   └── main.py          # FastAPI app
│   ├── tests/               # Test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── hooks/           # Custom hooks
│   │   ├── api.ts           # API client
│   │   └── App.tsx          # Main app
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .github/workflows/ci.yml
└── README.md
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git
- (Optional) NVIDIA GPU for faster Ollama inference

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd bikram
   ```

2. **Start all services with Docker Compose**
   ```bash
   docker compose up -d
   ```

3. **Pull the Ollama model** (first time only)
   ```bash
   docker exec -it docqa-ollama ollama pull llama3.2
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Development Setup

For local development without Docker:

1. **Backend**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   
   # Start MongoDB (required)
   # Start Ollama and pull model
   ollama pull llama3.2
   
   # Run the server
   uvicorn app.main:app --reload
   ```

2. **Frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## API Documentation

### Upload Endpoints

#### Upload File
```http
POST /api/upload/
Content-Type: multipart/form-data

file: <binary>
```

Response:
```json
{
  "id": "uuid",
  "filename": "document.pdf",
  "file_type": "pdf",
  "file_size": 1024,
  "processed": false,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Check Upload Status
```http
GET /api/upload/status/{document_id}
```

### Document Endpoints

#### List Documents
```http
GET /api/documents/?skip=0&limit=20&file_type=pdf
```

#### Get Document
```http
GET /api/documents/{document_id}
```

#### Get Document Content
```http
GET /api/documents/{document_id}/content
```

#### Get Timestamps (Audio/Video)
```http
GET /api/documents/{document_id}/timestamps
```

#### Delete Document
```http
DELETE /api/documents/{document_id}
```

### Chat Endpoints

#### Send Message
```http
POST /api/chat/
Content-Type: application/json

{
  "document_id": "uuid",
  "message": "What is this document about?",
  "include_timestamps": true
}
```

#### WebSocket Streaming
```
WS /api/chat/stream/{document_id}

Send: {"message": "question", "include_timestamps": true}
Receive: {"token": "...", "done": false}
Final: {"token": "", "done": true, "sources": [...], "timestamps": [...]}
```

#### Get Chat History
```http
GET /api/chat/history/{document_id}
```

#### Clear Chat History
```http
DELETE /api/chat/history/{document_id}
```

## Testing

### Backend Tests
```bash
cd backend
pytest --cov=app --cov-report=term-missing --cov-fail-under=95
```

### Frontend Tests
```bash
cd frontend
npm run lint
npm run build
```

## Environment Variables

### Backend
| Variable | Default | Description |
|----------|---------|-------------|
| `MONGODB_URL` | `mongodb://localhost:27017` | MongoDB connection URL |
| `MONGODB_DB_NAME` | `document_qa` | Database name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `llama3.2` | LLM model to use |
| `UPLOAD_DIR` | `uploads` | File upload directory |
| `MAX_FILE_SIZE` | `104857600` | Max upload size (100MB) |
| `WHISPER_MODEL` | `base` | Whisper model size |

## Deployment

### Docker Compose (Recommended)
```bash
docker compose -f docker-compose.yml up -d
```

### Manual Deployment

1. Deploy MongoDB (Atlas or self-hosted)
2. Deploy Ollama with GPU support
3. Deploy backend with environment variables
4. Deploy frontend with API proxy configuration

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│   MongoDB   │
│   (React)   │     │  (FastAPI)  │     │             │
└─────────────┘     └──────┬──────┘     └─────────────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
        ┌─────────┐ ┌─────────┐ ┌─────────┐
        │ Whisper │ │  FAISS  │ │ Ollama  │
        │ (Local) │ │ (Local) │ │  (LLM)  │
        └─────────┘ └─────────┘ └─────────┘
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License.
