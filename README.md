# olmocr streamlit application

This application provides a user-friendly interface for converting PDF documents to Markdown format using the olmocr toolkit.

## Features

- Upload multiple PDF files for batch processing
- Real-time processing status tracking
- Side-by-side comparison of original PDFs and converted Markdown
- Download converted Markdown files

## Requirements

- NVIDIA GPU with at least 20 GB of VRAM (source id="1")
- Docker and Docker Compose
- NVIDIA Container Toolkit

## Setup

1. Create a `.env` file based on the provided template
2. Adjust configuration parameters as needed
3. Run `docker-compose up --build` to start the application

## Usage

1. Access the Streamlit app at `http://localhost:8501`
2. Navigate to "Upload PDFs" to add your documents
3. Check "Processing Status" to monitor conversion progress
4. View results in the "View Results" section when processing is complete

## Configuration

The application uses VLLM Forwarded arguments as environment variables (source id="1"):
- `GPU_MEMORY_UTILIZATION`: Fraction of VRAM vLLM may pre-allocate for KV-cache
- `MAX_MODEL_LEN`: Upper bound (tokens) vLLM will allocate KV-cache for
- `TENSOR_PARALLEL_SIZE`: Tensor parallel size for vLLM
- `DATA_PARALLEL_SIZE`: Data parallel size for vLLM
- `PORT`: Port to use for the VLLM server

Additional olmocr pipeline parameters are also configurable (source id="1"):
- `PAGES_PER_GROUP`: Target number of PDF pages per work item group
- `MAX_PAGE_RETRIES`: Max number of times to retry rendering a page
- `MAX_PAGE_ERROR_RATE`: Rate of allowable failed pages in a document
- `WORKERS`: Number of workers to run at a time