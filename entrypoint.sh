#!/bin/sh
set -e

# Create Streamlit config directory if it doesn't exist
mkdir -p /root/.streamlit

# Create Streamlit config file
cat > /root/.streamlit/config.toml << EOF
[server]
headless = true
port = 8501
enableCORS = true
[browser]
gatherUsageStats = false
EOF

echo "Starting Streamlit..."
echo "Workspace directory: $WORKSPACE_DIR"
echo "Input PDF directory: $INPUT_PDF_DIR"
echo "Output Markdown directory: $OUTPUT_MARKDOWN_DIR"

# Start the Streamlit app
exec streamlit run /app/streamlit_app.py "$@"