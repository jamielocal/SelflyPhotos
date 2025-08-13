#!/bin/bash

# Check if the directory already exists
if [ -d "selflyphotos" ]; then
  echo "The 'selflyphotos' directory already exists. Skipping git clone."
  cd selflyphotos/selfly
else
  # Clone the repository
  echo "Cloning the repository..."
  git clone https://github.com/jamielocal/selflyphotos
  cd selflyphotos/selfly
fi

# Create and activate a virtual environment
echo "Creating and activating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install Flask, requests, Pillow

# Run the application
echo "Starting the application..."
python3 app.py
