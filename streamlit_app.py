#!/usr/bin/env python3
"""
Streamlit web app for olmOCR PDF to Markdown conversion
"""

import streamlit as st
import tempfile
import os
import subprocess
import zipfile
from pathlib import Path
import json
import asyncio
from datetime import datetime
import shutil
import requests
import time

st.set_page_config(page_title="olmOCR PDF to Markdown Converter", layout="wide", page_icon="📄")

# Custom CSS for better styling
st.markdown(
    """
<style>
    .upload-section {
        border: 2px dashed #cccccc;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        margin: 1rem 0;
    }
    .success-box {
        padding: 1rem;
        border-radius: 5px;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        border-radius: 5px;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        border-radius: 5px;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        margin: 1rem 0;
    }
</style>
""",
    unsafe_allow_html=True,
)


# New helper to get workspace directories
def get_workspace_dirs():
    """Return workspace root and subdirs for PDFs and outputs.
    WORKSPACE_DIR can be overridden via env var, defaults to '/workspace'.
    """
    workspace_root = os.environ.get("WORKSPACE_DIR", "/workspace")
    pdf_dir = os.path.join(workspace_root, "pdfs")
    outputs_dir = os.path.join(workspace_root, "outputs")
    # Ensure directories exist
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(outputs_dir, exist_ok=True)
    return workspace_root, pdf_dir, outputs_dir


def check_vllm_server_status(base_url: str) -> bool:
    """Check if vLLM server is accessible"""
    try:
        headers = {}
        # Add API key if available
        vllm_api_key = os.environ.get("VLLM_API_KEY")
        if vllm_api_key:
            headers["Authorization"] = f"Bearer {vllm_api_key}"

        response = requests.get(f"{base_url}/v1/models", headers=headers, timeout=5)
        return response.status_code == 200
    except:
        return False


def run_olmocr_conversion(pdf_files, workspace_dir: str, vllm_base_url: str, **kwargs):
    """Run olmOCR conversion on uploaded PDF files"""

    # Save uploaded files to workspace/pdf directory
    workspace_root, pdf_dir, outputs_dir = get_workspace_dirs()

    pdf_paths = []
    for pdf_file in pdf_files:
        # Save using safe filename under /workspace/pdfs
        pdf_path = os.path.join(pdf_dir, pdf_file.name)
        with open(pdf_path, "wb") as f:
            f.write(pdf_file.getbuffer())
        pdf_paths.append(pdf_path)

    # Build olmOCR command - workspace_dir used for run-specific temp artifacts
    cmd = [
        "python",
        "-m",
        "olmocr.pipeline",
        workspace_dir,
        "--markdown",
        "--pdfs",
        *pdf_paths,
    ]

    # Add vLLM server URL if provided
    if vllm_base_url:
        cmd.extend(["--vllm_base_url", vllm_base_url])

    # Add vLLM API key if available
    vllm_api_key = os.environ.get("VLLM_API_KEY")
    if vllm_api_key:
        cmd.extend(["--vllm_api_key", vllm_api_key])

    # Add additional parameters
    if kwargs.get("target_dim"):
        cmd.extend(["--target_longest_image_dim", str(kwargs["target_dim"])])
    if kwargs.get("apply_filter"):
        cmd.append("--apply_filter")
    if kwargs.get("guided_decoding"):
        cmd.append("--guided_decoding")
    if kwargs.get("workers"):
        cmd.extend(["--workers", str(kwargs["workers"])])
    # ...existing code...
    return cmd, pdf_paths


def main():
    st.title("📄 olmOCR: PDF to Markdown Converter")
    st.markdown("Convert PDF documents to Markdown using visual language models")

    # Get vLLM server URL from environment variable
    vllm_base_url = os.environ.get("VLLM_BASE_URL", "http://vllm-server:30024")
    vllm_api_key = os.environ.get("VLLM_API_KEY")

    # Get workspace directory from environment variable or default to /workspace
    workspace_dir = os.environ.get("WORKSPACE_DIR", "/workspace")

    # Ensure workspace directory exists
    os.makedirs(workspace_dir, exist_ok=True)

    # Sidebar configuration
    st.sidebar.header("⚙️ Configuration")

    # Display workspace directory in sidebar
    st.sidebar.subheader("📁 Workspace")
    st.sidebar.info(f"Working directory: {workspace_dir}")

    # Server status in sidebar
    st.sidebar.subheader("Server Status")
    server_status = check_vllm_server_status(vllm_base_url)
    if server_status:
        st.sidebar.success("✅ vLLM Server: Online")
    else:
        st.sidebar.error("❌ vLLM Server: Offline")

    # API Key status
    if vllm_api_key:
        st.sidebar.success("🔑 API Key: Configured")
    else:
        st.sidebar.warning("🔑 API Key: Not set")
        st.sidebar.info("💡 Set VLLM_API_KEY environment variable if your server requires authentication")

    if st.sidebar.button("🔍 Refresh Server Status"):
        st.rerun()

    st.sidebar.markdown("---")

    # Advanced Settings
    st.sidebar.subheader("Advanced Settings")
    target_dim = st.sidebar.slider("Target Image Dimension", 800, 2000, 1288)
    apply_filter = st.sidebar.checkbox("Apply PDF Filter", value=True)
    guided_decoding = st.sidebar.checkbox("Enable Guided Decoding", value=False)
    workers = st.sidebar.slider("Number of Workers", 1, 20, 10)

    # Main interface
    st.header("📁 Upload PDF Files")

    # File uploader
    uploaded_files = st.file_uploader("Choose PDF files", type=["pdf"], accept_multiple_files=True, help="Upload one or more PDF files to convert to Markdown")

    if uploaded_files:
        st.write(f"📋 **{len(uploaded_files)} file(s) uploaded:**")
        for file in uploaded_files:
            file_size = len(file.getbuffer())
            st.write(f"• {file.name} ({file_size/1024/1024:.2f} MB)")

    # Conversion section
    if uploaded_files:
        st.header("🚀 Convert to Markdown")

        if st.button("Start Conversion", type="primary", use_container_width=True):
            if not check_vllm_server_status(vllm_base_url):
                st.error("❌ vLLM server is not accessible. Please check the server status and ensure it's running.")
                return

            try:
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()

                status_text.text("🔄 Preparing files...")
                progress_bar.progress(10)

                # Run conversion
                cmd, pdf_paths = run_olmocr_conversion(
                    uploaded_files,
                    workspace_dir,
                    vllm_base_url,
                    target_dim=target_dim,
                    apply_filter=apply_filter,
                    guided_decoding=guided_decoding,
                    workers=workers,
                )

                status_text.text("🚀 Running olmOCR conversion...")
                progress_bar.progress(30)

                # Execute conversion
                with st.expander("📋 Conversion Log", expanded=True):
                    log_text = st.empty()
                    # Set up logging to capture detailed output
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, universal_newlines=True)

                    log_lines = []
                    error_count = 0
                    connection_errors = 0

                    # Check if process started successfully
                    if process.stdout is None:
                        st.error("❌ Failed to start conversion process")
                        return

                    while True:
                        output = process.stdout.readline()
                        if output == "" and process.poll() is not None:
                            break
                        if output:
                            line = output.strip()
                            log_lines.append(line)
                            # Count different types of errors for better user feedback
                            if "ERROR" in line or "💥" in line or "❌" in line:
                                error_count += 1
                            if "CONNECTION ERROR" in line or "🔌" in line:
                                connection_errors += 1
                            # Show all log lines in a scrollable textarea
                            formatted_log = []
                            for log_line in log_lines:
                                if any(symbol in log_line for symbol in ["❌", "💥", "💀", "ERROR"]):
                                    formatted_log.append(f"🔥 {log_line}")
                                elif any(symbol in log_line for symbol in ["⚠️", "WARNING"]):
                                    formatted_log.append(f"⚠️ {log_line}")
                                elif any(symbol in log_line for symbol in ["✅", "SUCCESS"]):
                                    formatted_log.append(f"✅ {log_line}")
                                else:
                                    formatted_log.append(log_line)
                            log_text.text_area("Conversion Log (Verbose)", value="\n".join(formatted_log), height=400, disabled=True)
                return_code = process.poll()

                progress_bar.progress(80)
                status_text.text("📝 Processing results...")

                if return_code == 0:
                    # Check for generated markdown files
                    markdown_dir = os.path.join(workspace_dir, "markdown")
                    st.info(f"🔍 Looking for markdown files in: {markdown_dir}")

                    if os.path.exists(markdown_dir):
                        # Find all markdown files
                        markdown_files = []
                        for root, dirs, files in os.walk(markdown_dir):
                            for file in files:
                                if file.endswith(".md"):
                                    markdown_files.append(os.path.join(root, file))

                        st.info(f"📄 Found {len(markdown_files)} markdown files in {markdown_dir}")
                        progress_bar.progress(100)
                        status_text.text("✅ Conversion completed successfully!")

                        if markdown_files:
                            st.success(f"🎉 Successfully converted {len(markdown_files)} PDF file(s) to Markdown!")

                            # Results section
                            st.header("📥 Download Results")

                            if len(markdown_files) == 1:
                                # Single file - show preview and download
                                md_file = markdown_files[0]
                                with open(md_file, "r", encoding="utf-8") as f:
                                    markdown_content = f.read()

                                col1, col2 = st.columns([3, 1])

                                with col1:
                                    st.subheader("📄 Preview")
                                    with st.expander("View Markdown Content", expanded=True):
                                        st.text_area("", value=markdown_content, height=300, disabled=True)

                                with col2:
                                    st.subheader("⬇️ Download")
                                    filename = os.path.basename(md_file)
                                    st.download_button(label=f"Download {filename}", data=markdown_content, file_name=filename, mime="text/markdown")

                            else:
                                # Multiple files - create zip
                                st.subheader("📦 Multiple Files")

                                # Create zip file
                                zip_path = os.path.join(workspace_dir, "markdown_files.zip")
                                with zipfile.ZipFile(zip_path, "w") as zipf:
                                    for md_file in markdown_files:
                                        # Get relative path for zip
                                        rel_path = os.path.relpath(md_file, markdown_dir)
                                        zipf.write(md_file, rel_path)

                                # Offer zip download
                                with open(zip_path, "rb") as f:
                                    zip_data = f.read()

                                st.download_button(
                                    label=f"📁 Download All ({len(markdown_files)} files as ZIP)",
                                    data=zip_data,
                                    file_name="olmocr_markdown_files.zip",
                                    mime="application/zip",
                                )

                                # Show file list
                                with st.expander("📋 Converted Files", expanded=True):
                                    for md_file in markdown_files:
                                        filename = os.path.basename(md_file)
                                        file_size = os.path.getsize(md_file)
                                        st.write(f"• {filename} ({file_size/1024:.1f} KB)")

                        else:
                            st.warning("⚠️ Conversion completed but no markdown files were generated.")

                    else:
                        st.warning(f"⚠️ Conversion completed but no markdown directory was created at: {markdown_dir}")
                        # Let's also check if there are any .md files in the workspace root or other locations
                        st.info("🔍 Searching for markdown files in workspace...")
                        all_md_files = []
                        for root, dirs, files in os.walk(workspace_dir):
                            for file in files:
                                if file.endswith(".md"):
                                    all_md_files.append(os.path.join(root, file))

                        if all_md_files:
                            st.warning(f"❗ Found {len(all_md_files)} markdown files in unexpected locations:")
                            for md_file in all_md_files:
                                rel_path = os.path.relpath(md_file, workspace_dir)
                                st.write(f"• {rel_path}")
                        else:
                            st.error("❌ No markdown files found anywhere in the workspace")

                else:
                    progress_bar.progress(100)
                    status_text.text("❌ Conversion failed")
                    st.error(f"❌ Conversion failed with return code {return_code}")

            except Exception as e:
                st.error(f"❌ An error occurred during conversion: {str(e)}")

    # Footer
    st.markdown("---")
    st.markdown(
        """
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>🔬 Powered by olmOCR • Built with Streamlit</p>
        <p>📖 For more information, visit the <a href='https://github.com/allenai/olmocr' target='_blank'>olmOCR GitHub repository</a></p>
    </div>
    """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
