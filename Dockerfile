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

# Streamlit configuration
RUN mkdir -p /root/.streamlit && \
    echo "[server]\nheadless = true\nport = $STREAMLIT_BROWSER_SERVER_PORT\nenableCORS = false" > /root/.streamlit/config.toml

# Expose port
EXPOSE ${STREAMLIT_BROWSER_SERVER_PORT}

# Run Streamlit
CMD ["streamlit", "run", "streamlit_app.py", "--server.port", "${STREAMLIT_BROWSER_SERVER_PORT}"]