#!/usr/bin/env bash
# Render build script — runs before every deploy
set -o errexit

echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

echo "🗄️  Database tables are created on startup (see lifespan in main.py)"
echo "✅ Build complete"
