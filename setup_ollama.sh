#!/bin/bash
# Complete Ollama setup script for GPU node

echo "🤖 Setting up Ollama on GPU node..."

# Check if we're on a GPU node
HOSTNAME=$(hostname)
echo "Running on: $HOSTNAME"

# Find or download ollama binary
OLLAMA_BIN="$HOME/ollama"

if [ ! -f "$OLLAMA_BIN" ]; then
    echo "📥 Downloading Ollama..."
    # Use the official install script to get the binary
    curl -fsSL https://ollama.ai/install.sh | sh -s -- --install-dir="$HOME" --binary-name="ollama"
    
    if [ -f "$OLLAMA_BIN" ]; then
        chmod +x "$OLLAMA_BIN"
        echo "✓ Ollama downloaded to $OLLAMA_BIN"
    else
        echo "❌ Failed to install Ollama"
        # Try manual download as fallback
        echo "Trying alternative download method..."
        curl -L https://ollama.ai/download/ollama-linux-amd64 -o "$OLLAMA_BIN"
        
        if file "$OLLAMA_BIN" 2>/dev/null | grep -q "executable"; then
            chmod +x "$OLLAMA_BIN"
            echo "✓ Ollama downloaded to $OLLAMA_BIN"
        else
            rm -f "$OLLAMA_BIN"
            exit 1
        fi
    fi
else
    echo "✓ Ollama binary found at $OLLAMA_BIN"
fi

# Create ollama directory for keys
mkdir -p ~/.ollama

# Generate SSH key if it doesn't exist
if [ ! -f ~/.ollama/id_ed25519 ]; then
    echo "🔑 Generating SSH key for Ollama..."
    ssh-keygen -t ed25519 -f ~/.ollama/id_ed25519 -N "" -q
    echo "✓ SSH key created"
fi

# Check if Ollama server is already running
if pgrep -f "ollama serve" > /dev/null; then
    OLLAMA_PID=$(pgrep -f "ollama serve")
    echo "✓ Ollama server already running (PID: $OLLAMA_PID)"
else
    # Start Ollama server listening on all interfaces
    echo "🚀 Starting Ollama server..."
    export OLLAMA_HOST=0.0.0.0:11434
    nohup "$OLLAMA_BIN" serve > ~/ollama.log 2>&1 &
    OLLAMA_PID=$!
    echo "✓ Ollama server started with PID: $OLLAMA_PID"
    
    # Wait for server to start
    echo "⏳ Waiting for server to initialize..."
    sleep 5
fi

# Check if llama2 model is installed
echo "📦 Checking for llama2 model..."
if "$OLLAMA_BIN" list 2>/dev/null | grep -q "llama2"; then
    echo "✓ llama2 model already installed"
else
    echo "📥 Pulling llama2 model (this will take 5-10 minutes, ~3.8GB)..."
    "$OLLAMA_BIN" pull llama2
    
    if [ $? -eq 0 ]; then
        echo "✓ llama2 model installed successfully"
    else
        echo "❌ Failed to pull llama2 model"
        exit 1
    fi
fi

echo ""
echo "=================================================="
echo "✅ Ollama setup complete!"
echo "=================================================="
echo "Server: http://$HOSTNAME:11434"
echo "Listening on all interfaces (0.0.0.0:11434)"
echo ""
echo "Installed models:"
"$OLLAMA_BIN" list
echo ""
echo "To stop Ollama: kill $OLLAMA_PID"
echo "To view logs: tail -f ~/ollama.log"
echo ""
