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

# Install supervisord and Cloud SQL Auth Proxy if not already installed
if ! command -v supervisord &> /dev/null; then
  pip install supervisor
fi

# Determine the system's OS and architecture
OS=$(uname -s)
ARCH=$(uname -m)

# Map architecture to Cloud SQL Auth Proxy naming conventions
if [ "$ARCH" = "x86_64" ]; then
  ARCH="amd64"
elif [ "$ARCH" = "arm64" ]; then
  ARCH="arm64"
fi

# Set the download URL based on the OS and architecture
if [ "$OS" = "Linux" ]; then
  PROXY_URL="https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.10.1/cloud-sql-proxy.linux.$ARCH"
elif [ "$OS" = "Darwin" ]; then
  PROXY_URL="https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.10.1/cloud-sql-proxy.darwin.$ARCH"
else
  echo "Unsupported OS: $OS"
  exit 1
fi

# Install Cloud SQL Auth Proxy if not already installed
if ! command -v cloud-sql-proxy &> /dev/null; then
  curl -o /usr/local/bin/cloud-sql-proxy "$PROXY_URL"
  chmod +x /usr/local/bin/cloud-sql-proxy
fi

# Start supervisord with the config (will manage cloud-sql-proxy)
# supervisord -c /workspaces/tsi-data-uploader/.devcontainer/supervisord.conf

echo "Post-create setup complete."
echo "--------------------------------------------------------"
echo "To connect to your database:"
echo "1. Run 'gcloud auth application-default login'"
echo "2. Start the Cloud SQL Auth Proxy when needed:"
echo "   supervisord -c /workspaces/tsi-data-uploader/.devcontainer/supervisord.conf"
echo "   or"
echo "   cloud-sql-proxy durham-weather-466502:us-east1:durham-weather-db --port=5432"
echo "For more information, visit: https://cloud.google.com/sql/docs/mysql/connect-auth-proxy"
echo "--------------------------------------------------------"
