#!/bin/sh
set -e

# Ensure port variables are set with defaults if not provided
STREAMLIT_PORT=${STREAMLIT_BROWSER_SERVER_PORT:-8501}

# Create Streamlit config directory if it doesn't exist
mkdir -p /root/.streamlit

# Create Streamlit config file with proper port setting
cat > /root/.streamlit/config.toml << EOF
[server]
headless = true
port = $STREAMLIT_PORT
enableCORS = false
[browser]
gatherUsageStats = false
EOF

echo "Starting Streamlit on port $STREAMLIT_PORT"
echo "Workspace directory: $WORKSPACE_DIR"
echo "Input PDF directory: $INPUT_PDF_DIR"
echo "Output Markdown directory: $OUTPUT_MARKDOWN_DIR"

# Start the Streamlit app
exec streamlit run /app/streamlit_app.py "$@"