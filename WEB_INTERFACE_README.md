# olmOCR Web Interface

This setup provides a web-based interface for olmOCR PDF to Markdown conversion using Docker Compose.

## Features

- **Web Interface**: User-friendly Streamlit app for uploading PDFs and downloading Markdown files
- **Persistent vLLM Server**: Separate vLLM server container that stays loaded with the model
- **No Startup Delays**: Avoid model loading time on each conversion
- **Batch Processing**: Upload multiple PDFs at once
- **Real-time Progress**: Live conversion logs and progress tracking
- **Download Options**: Single file download or ZIP for multiple files

## Quick Start

### Prerequisites

- Docker and Docker Compose
- NVIDIA GPU with CUDA support
- nvidia-docker2 installed

### 1. Start the Services

```bash
# Clone the repository
git clone https://github.com/allenai/olmocr.git
cd olmocr

# Start both vLLM server and Streamlit app
docker-compose up -d
```

### 2. Access the Web Interface

Open your browser and navigate to: http://localhost:8501

### 3. Wait for Model Loading

The vLLM server needs time to download and load the model (5-10 minutes on first run). You can monitor the progress:

```bash
# Check vLLM server logs
docker-compose logs -f vllm-server

# Check when server is ready
curl http://localhost:30024/v1/models
```

### 4. Convert PDFs

1. Upload PDF files using the web interface
2. Configure conversion settings in the sidebar
3. Click "Start Conversion"
4. Download the generated Markdown files

## Configuration

### vLLM Server Settings

Edit `docker-compose.yml` to customize the vLLM server:

```yaml
services:
  vllm-server:
    command: >
      --model allenai/olmOCR-7B-0725-FP8
      --port 8000
      --tensor-parallel-size 1
      --gpu-memory-utilization 0.9
      --max-model-len 16384
```

### Streamlit App Settings

The Streamlit app can be configured through environment variables:

```yaml
services:
  streamlit-app:
    environment:
      - VLLM_DEFAULT_URL=http://vllm-server:8000
      - MAX_FILE_SIZE=100MB
```

## Advanced Usage

### Using External vLLM Server

If you already have a vLLM server running elsewhere:

1. Update the vLLM server URL in the Streamlit interface
2. Or set it as default in `streamlit_app.py`:

```python
vllm_base_url = st.sidebar.text_input(
    "vLLM Server URL",
    value="http://your-external-server:30024",  # Change this
    help="URL of the running vLLM server"
)
```

### Command Line Usage with External Server

You can also use the command line with an external vLLM server:

```bash
python -m olmocr.pipeline ./workspace \
  --markdown \
  --pdfs document.pdf \
  --vllm_base_url http://localhost:30024
```

### Development Mode

For development, you can run the services separately:

```bash
# Start only vLLM server
docker-compose up vllm-server

# Run Streamlit app locally
pip install streamlit
streamlit run streamlit_app.py
```

## Troubleshooting

### Common Issues

1. **GPU Memory Issues**
   ```bash
   # Reduce GPU memory utilization
   # Edit docker-compose.yml:
   --gpu-memory-utilization 0.7
   ```

2. **Model Loading Timeout**
   ```bash
   # Check vLLM server logs
   docker-compose logs vllm-server

   # Increase healthcheck timeout in docker-compose.yml
   start_period: 600s  # 10 minutes
   ```

3. **Port Conflicts**
   ```bash
   # Change ports in docker-compose.yml
   ports:
     - "8502:8501"  # Streamlit
     - "30025:8000" # vLLM
   ```

4. **File Upload Issues**
   ```bash
   # Increase Streamlit file upload limit
   # Add to streamlit_app.py:
   st.set_option('server.maxUploadSize', 200)  # 200MB
   ```

### Logs and Monitoring

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f vllm-server
docker-compose logs -f streamlit-app

# Check service status
docker-compose ps

# Check resource usage
docker stats
```

### Performance Tuning

1. **Multi-GPU Setup**
   ```yaml
   # In docker-compose.yml
   environment:
     - CUDA_VISIBLE_DEVICES=0,1
   command: >
     --tensor-parallel-size 2
   ```

2. **Memory Optimization**
   ```yaml
   command: >
     --gpu-memory-utilization 0.8
     --max-model-len 8192
   ```

3. **Worker Configuration**
   ```python
   # In Streamlit app sidebar
   workers = st.sidebar.slider("Number of Workers", 1, 20, 5)
   ```

## API Endpoints

The vLLM server exposes standard OpenAI-compatible endpoints:

- `GET /v1/models` - List available models
- `POST /v1/chat/completions` - Chat completions (used by olmOCR)
- `GET /health` - Health check

## File Structure

```
olmocr/
├── docker-compose.yml          # Docker Compose configuration
├── Dockerfile.streamlit        # Streamlit app Dockerfile
├── streamlit_app.py           # Web interface
├── olmocr/
│   └── pipeline.py            # Modified pipeline with external vLLM support
├── workspace/                 # Conversion workspace (mounted)
└── models/                    # Model cache (mounted)
```

## Security Considerations

- The web interface runs on all interfaces (0.0.0.0) by default
- For production use, consider adding authentication
- Limit file upload sizes and types
- Run behind a reverse proxy with HTTPS

## License

This project follows the same license as the main olmOCR repository.
