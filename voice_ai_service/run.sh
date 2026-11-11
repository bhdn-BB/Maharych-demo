#!/bin/sh
set -eu

cd "$(dirname "$0")/src"
exec uvicorn voice_ai_service.main:app --reload
