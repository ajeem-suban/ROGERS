# System Architecture: Tamil AI Document Intelligence

## Overview
The system follows a decoupled, event-driven architecture. The React single-page frontend communicates with the FastAPI gateway via REST and Server-Sent Events. Ingested documents are stored in object storage, while an asynchronous OCR worker pool extracts text and coordinates. Extracted text chunks are vectorized and indexed in pgvector. When a query is submitted, the RAG engine performs hybrid dense-sparse semantic retrieval and streams context-grounded responses back to the user.

## Component Boundaries
### Web Presentation Layer (React + Vite client)
- Core responsibilities and interactions.
### API Gateway & Auth Service (FastAPI)
- Core responsibilities and interactions.
### Asynchronous Document Processing Queue (Redis + Celery)
- Core responsibilities and interactions.
### Tamil OCR & Text Normalization Engine (Tesseract/EasyOCR)
- Core responsibilities and interactions.
### Vector Store & Hybrid Retrieval Engine (pgvector / Qdrant)
- Core responsibilities and interactions.
### RAG Orchestration & Prompt Synthesis Service
- Core responsibilities and interactions.
### Relational Metadata & Audit Store (PostgreSQL)
- Core responsibilities and interactions.
### Document File Store (S3 / MinIO)
- Core responsibilities and interactions.

## Technology Stack Rationale
- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS + Lucide Icons
- **Backend**: FastAPI (Python 3.11+) + Uvicorn + Pydantic v2 + Celery worker queue
- **Database**: PostgreSQL 16 + pgvector (or Qdrant) + Redis for task caching
- **AI/ML**: Tesseract OCR (Tamil traineddata) / EasyOCR + IndicBERT / BGE-M3 embeddings + Llama 3 / Mistral via Ollama or Groq
