#!/bin/bash

# Azure App Service startup script for LinkedIn Scraper
# This script installs Chrome and ChromeDriver automatically

echo "🚀 Starting LinkedIn Scraper API setup for Azure..."

# Update package list
apt-get update

# Install Chrome dependencies
echo "📦 Installing Chrome dependencies..."
apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    x11vnc \
    fluxbox \
    dbus-x11

# Install Google Chrome
echo "🌐 Installing Google Chrome..."
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list
apt-get update
apt-get install -y google-chrome-stable

# Get Chrome version and install matching ChromeDriver
echo "🔧 Setting up ChromeDriver..."
CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d. -f1-3)
echo "Chrome version: $CHROME_VERSION"

# Download and install ChromeDriver
CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION%.*}")
echo "ChromeDriver version: $CHROMEDRIVER_VERSION"

wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip"
unzip /tmp/chromedriver.zip -d /tmp/
mv /tmp/chromedriver /usr/local/bin/chromedriver
chmod +x /usr/local/bin/chromedriver

# Verify installation
echo "✅ Verifying installations..."
google-chrome --version
chromedriver --version

# Set up virtual display for headless operation
echo "🖥️ Setting up virtual display..."
export DISPLAY=:99
Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &

# Create output directory
mkdir -p /home/site/wwwroot/output

echo "🎉 Setup complete! Starting FastAPI application..."

# Start the FastAPI application
cd /home/site/wwwroot
uvicorn fastapi_app:app --host 0.0.0.0 --port 8000