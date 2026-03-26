#!/bin/bash
# Script para lanzar las pruebas de Marco AI

echo "🚀 Lanzando pruebas unitarias de Marco AI..."
export SECRET_KEY="monkey"
export GOOGLE_CLIENT_ID="mock_id"
export GOOGLE_CLIENT_SECRET="mock_secret"
export FRONTEND_URL="http://localhost:3000"
export GROQ_API_KEY="mock_groq"
export OPENROUTER_API_KEY="mock_openrouter"
export GOOGLE_API_KEY="mock_google"

export PYTHONPATH=$(pwd)
/home/marco/.local/bin/pytest -v tests/
