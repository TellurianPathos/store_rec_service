#!/bin/bash

# Setup script for the recommendation system
# This script will create a virtual environment and install dependencies

set -e  # Exit on error

echo "Setting up recommendation system environment..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
required_version="3.9"
if [[ $(echo -e "$python_version\n$required_version" | sort -V | head -n1) != "$required_version" ]]; then
    echo "Python version $python_version is not supported. Please use Python 3.9 or higher."
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv .venv

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Train model if needed
if [ ! -f "ml_models/content_model.pkl" ]; then
    echo "Training recommendation model..."
    python scripts/train_model.py
fi

echo "Setup complete! You can now run the application with:"
echo "source .venv/bin/activate"
echo "uvicorn app.main:app --reload"
