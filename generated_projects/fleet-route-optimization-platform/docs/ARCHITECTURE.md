# System Architecture: Fleet Route Optimization Platform

## Overview
Telemetry data is ingested through high-speed WebSocket and REST endpoints into TimescaleDB. A route optimization engine processes order queues and battery levels, dispatching optimized navigation routes to driver interfaces while broadcasting real-time location changes to the operations map.

## Component Boundaries
### Dispatch & Operations Web Console
- Core responsibilities and interactions.
### Telemetry Ingestion Gateway (FastAPI WebSockets)
- Core responsibilities and interactions.
### Time-Series Telematics Store (TimescaleDB)
- Core responsibilities and interactions.
### Routing Optimization Engine (OR-Tools)
- Core responsibilities and interactions.
### Notification & Alert Service
- Core responsibilities and interactions.
### Vehicle Telemetry Simulator / Hardware Connector
- Core responsibilities and interactions.

## Technology Stack Rationale
- **Frontend**: Next.js + React Leaflet / Mapbox GL + Tailwind CSS
- **Backend**: FastAPI + WebSockets + Celery for async route calculation
- **Database**: TimescaleDB (PostgreSQL time-series) + Redis Geo + MinIO for exports
- **AI/ML**: OR-Tools / OSRM routing solver + LightGBM battery degradation estimator
