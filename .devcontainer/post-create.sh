#!/bin/bash
# This script is executed after the container is created.

echo "Starting post-create setup..."

# Install Google Cloud CLI
echo "Installing Google Cloud CLI..."
sudo apt-get update && sudo apt-get install -y lsb-release apt-transport-https ca-certificates gnupg

echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list

curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -

sudo apt-get update && sudo apt-get install -y google-cloud-cli

# Install Python dependencies
echo "Installing Python dependencies from requirements.txt..."
pip install --user -r requirements.txt
if [ -f "requirements-dev.txt" ]; then
    pip install --user -r requirements-dev.txt
fi

echo "Post-create setup complete."
echo "--------------------------------------------------------"
echo "To connect to your database:"
echo "1. Run 'gcloud auth application-default login'"
echo "2. Start the Cloud SQL Auth Proxy in a terminal."
echo "   Example: cloud-sql-proxy --address 0.0.0.0 durham-weather-466502:us-central1:durham-weather-db"
echo "--------------------------------------------------------"
