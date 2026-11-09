# Use the official Python image
FROM python:3.11-slim

# HF Spaces run as a non-root user (uid 1000)
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

# Install system dependencies (required for some Python packages)
USER root
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Fix ownership of the app directory so the user can write the FAISS database
RUN chown -R user:user $HOME/app

# Switch back to the non-root user
USER user

# Copy the requirements file and install dependencies
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
# Add pillow_avif_plugin to ensure webp/avif support
RUN pip install --no-cache-dir pillow-avif-plugin

# Copy the current directory contents into the container
COPY --chown=user . $HOME/app

# Ensure correct FAISS index storage path
ENV FAISS_INDEX_PATH="$HOME/app/memory_bank.index"

# Create a start script to ensure Uvicorn bounds to the port expected by Hugging Face Spaces (7860)
RUN echo '#!/bin/bash\n\
    uvicorn main:app --host 0.0.0.0 --port 7860\n\
    ' > start.sh && chmod +x start.sh

# Expose port (Hugging Face Spaces default Docker port is 7860)
EXPOSE 7860

# Command to run the application
CMD ["./start.sh"]
