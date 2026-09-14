from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Fleet Route Optimization Platform API",
    description="Fleet Route Optimization Platform is a real-time fleet telematics and route optimization system designed for delivery operations. It aggregates live vehicle GPS telemetry, analyzes battery consumption and topography, computes dynamic multi-stop routes, and surfaces driver dispatch metrics through a responsive web and mobile operations console.",
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
    return {"status": "healthy", "service": "Fleet Route Optimization Platform"}

@app.get("/api/info")
async def info():
    return {
        "name": "Fleet Route Optimization Platform",
        "architecture": "Telemetry data is ingested through high-speed WebSocket and REST endpoints into TimescaleDB. A route optimization engine processes order queues and battery levels, dispatching optimized navigation routes to driver interfaces while broadcasting real-time location changes to the operations map."
    }
