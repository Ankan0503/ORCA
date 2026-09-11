"""Entrypoint script to launch the ORCA-Core master backend."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn

CORE_DIR = Path(__file__).resolve().parent
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ORCA-Core Unified FastAPI Backend")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8100, help="Port to listen on (default: 8100)")
    parser.add_argument("--reload", action="store_true", default=True, help="Enable auto-reload")
    args = parser.parse_args()

    print(f"==================================================")
    print(f"  ORCA-Core Unified Multi-Agent Intelligence Engine")
    print(f"  Listening at: http://{args.host}:{args.port}")
    print(f"  API Docs at:  http://{args.host}:{args.port}/docs")
    print(f"==================================================")

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
