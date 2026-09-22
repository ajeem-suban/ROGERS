from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Tamil Document AI Suite API",
    description="Tamil Document AI Suite is an intelligent Tamil-language document processing and retrieval platform. It ingests scanned documents and PDFs, extracts high-accuracy Tamil and English text using specialized OCR, indexes textual chunks into a semantic vector store, and enables users to perform natural language question answering grounded directly in document context via Retrieval-Augmented Generation (RAG).",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "Tamil Document AI Suite"}

@app.get("/api/info")
async def info():
    return {
        "name": "Tamil Document AI Suite",
        "architecture": "The system follows a decoupled, event-driven architecture. The React single-page frontend communicates with the FastAPI gateway via REST and Server-Sent Events. Ingested documents are stored in object storage, while an asynchronous OCR worker pool extracts text and coordinates. Extracted text chunks are vectorized and indexed in pgvector. When a query is submitted, the RAG engine performs hybrid dense-sparse semantic retrieval and streams context-grounded responses back to the user."
    }
