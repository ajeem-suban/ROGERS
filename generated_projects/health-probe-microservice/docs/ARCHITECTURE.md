# System Architecture: Health Probe Microservice

## Overview
A modular layered architecture separating presentation, API routing, business domain services, and persistence. Client applications communicate over REST/JSON with JWT authentication. Data access is managed through an ORM with transaction support, while background workers handle heavy tasks.

## Component Boundaries
### Client Web Application
- Core responsibilities and interactions.
### FastAPI REST Application Layer
- Core responsibilities and interactions.
### Authentication & Security Middleware
- Core responsibilities and interactions.
### Core Business Logic Services
- Core responsibilities and interactions.
### Relational Database (PostgreSQL/SQLite)
- Core responsibilities and interactions.
### Cache & Task Queue (Redis)
- Core responsibilities and interactions.

## Technology Stack Rationale
- **Frontend**: React + TypeScript + Vite + Tailwind CSS
- **Backend**: FastAPI + Python + SQLAlchemy + Alembic
- **Database**: PostgreSQL + Redis for session caching
- **AI/ML**: OpenAI / Ollama / Groq Llama 3 for intelligent processing
