from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="cullinan-ai API",
    description="cullinan-ai is an engineering solution designed to address: 'generate the image of me by using local ai model. i train the base ai model with my images and then it produce my image with the prompt'. It couples a responsive client interface with a robust, scalable backend API and targeted intelligence services to streamline user workflows and deliver real-time actionable outcomes.",
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
    return {"status": "healthy", "service": "cullinan-ai"}

@app.get("/api/info")
async def info():
    return {
        "name": "cullinan-ai",
        "architecture": "A modular layered architecture separating presentation, API routing, business domain services, and persistence. Client applications communicate over REST/JSON with JWT authentication. Data access is managed through an ORM with transaction support, while background workers handle heavy tasks."
    }
