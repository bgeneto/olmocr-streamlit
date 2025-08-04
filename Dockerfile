FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    fonts-crosextra-caladea \
    fonts-crosextra-carlito \
    gsfonts \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir streamlit pandas numpy requests

# Create app directory
WORKDIR /app

# Copy Streamlit app
COPY streamlit_app.py /app/

# Create entrypoint script
RUN echo '#!/bin/sh\n\
 STREAMLIT_SERVER_PORT=${STREAMLIT_BROWSER_SERVER_PORT:-8501}\n\
 echo "Starting Streamlit on port $STREAMLIT_SERVER_PORT"\n\
 exec streamlit run /app/streamlit_app.py --browser.gatherUsageStats false --server.port $STREAMLIT_SERVER_PORT "$@"\n' > /app/entrypoint.sh && \
 chmod +x /app/entrypoint.sh

# Streamlit configuration via config file instead of command line (source id="1")
RUN mkdir -p /root/.streamlit && \
    echo "[server]\nheadless = true\nenableCORS = false" > /root/.streamlit/config.toml

# Use the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]