#!/usr/bin/env bash
cd "$(dirname "$0")"
python3 -m uvicorn backend:app --reload --host 127.0.0.1 --port 8000
