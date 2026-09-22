import os
import sys
import uvicorn

if __name__ == "__main__":
    # Ensure current directory is in sys.path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "127.0.0.1")
    reload = os.getenv("RELOAD", "false").lower() in ["true", "1", "yes"]

    print(f"\n========================================================")
    print(f" ROGERS — AI Project Orchestrator (Slice 3: Implementation Engine)")
    print(f" Web Dashboard:    http://{host}:{port}")
    print(f" API Docs:         http://{host}:{port}/docs")
    print(f"--------------------------------------------------------")
    print(f" Status: Server is ACTIVE & listening for browser requests.")
    print(f" Press CTRL+C to stop.")
    print(f"========================================================\n")

    uvicorn.run("backend.app.main:app", host=host, port=port, reload=reload)
