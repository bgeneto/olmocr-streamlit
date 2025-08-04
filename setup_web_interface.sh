#!/bin/bash

# olmOCR Web Interface Setup Script
# This script helps you get started with the olmOCR web interface

set -e

echo "🚀 olmOCR Web Interface Setup"
echo "============================="

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check NVIDIA Docker (if GPU available)
if command -v nvidia-smi &> /dev/null; then
    echo "🎮 GPU detected!"
    if ! docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi &> /dev/null; then
        echo "⚠️  nvidia-docker2 not properly configured. GPU acceleration may not work."
        echo "   Visit: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
    else
        echo "✅ nvidia-docker2 is working!"
    fi
else
    echo "⚠️  No GPU detected. olmOCR will be very slow without GPU acceleration."
fi

echo "✅ Prerequisites check completed!"
echo ""

# Create workspace directory
echo "📁 Creating workspace directory..."
mkdir -p workspace models
echo "✅ Workspace created!"
echo ""

# Build and start services
echo "🏗️  Building and starting services..."
echo "   This may take 5-10 minutes on first run..."

docker-compose up -d --build

echo "✅ Services started!"
echo ""

# Wait for vLLM server to be ready
echo "⏳ Waiting for vLLM server to load model..."
echo "   This can take 5-10 minutes depending on your internet connection and GPU..."

max_attempts=60
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -s -f http://localhost:30024/v1/models > /dev/null 2>&1; then
        echo "✅ vLLM server is ready!"
        break
    fi

    echo "   Attempt $((attempt + 1))/$max_attempts - Still loading..."
    sleep 10
    attempt=$((attempt + 1))
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ vLLM server failed to start within expected time."
    echo "   Check logs with: docker-compose logs vllm-server"
    exit 1
fi

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "📱 Access the web interface at: http://localhost:8501"
echo "🔧 vLLM server API at: http://localhost:30024"
echo ""
echo "📊 Monitor services:"
echo "   docker-compose logs -f          # All logs"
echo "   docker-compose logs vllm-server # vLLM server logs"
echo "   docker-compose logs streamlit-app # Streamlit app logs"
echo ""
echo "🛑 Stop services:"
echo "   docker-compose down"
echo ""
echo "💡 For troubleshooting, see WEB_INTERFACE_README.md"
