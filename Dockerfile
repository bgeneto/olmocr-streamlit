FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    fonts-crosextra-caladea \
    fonts-crosextra-carlito \
    gsfonts \
    wget \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir streamlit pandas numpy requests

# Create app directory
WORKDIR /app

# Copy application files
COPY ./streamlit_app.py /app/
COPY ./entrypoint.sh /app/

# Ensure proper permissions and line endings
RUN chmod +x /app/entrypoint.sh && \
    dos2unix /app/entrypoint.sh 2>/dev/null || echo "dos2unix not installed, but continuing..." && \
    cat /app/entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]