# Dockerfile for Hugging Face Inference Endpoints

# 1. Start from an NVIDIA CUDA 12.1.0 image (to match your torch requirement)
# This image is based on Ubuntu 22.04, which uses Python 3.10
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04


# 2. Set the working directory
WORKDIR /app

# 3. Install Python, pip, git, and system libraries
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    libegl1 \
    libopengl0 \
    libglx-mesa0 \
    ffmpeg \
 && rm -rf /var/lib/apt/lists/* \
 && ln -s /usr/bin/python3 /usr/bin/python

# 4. Copy and install all Python requirements
# pip will read the --extra-index-url from inside the file
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy all your project files into the container
# (This includes main.py, api.py, VIBE.py, etc.)
COPY . .

# 6. Create model directories and copy files directly
# This avoids having the 'data' directory in the final image if not needed
RUN mkdir -p /root/.torch/models/ \
 && mkdir -p /root/.torch/config/ \
 && cp /app/data/vibe_data/yolov3.weights /root/.torch/models/yolov3.weights \
 && cp /app/data/yolov3.cfg /root/.torch/config/yolov3.cfg

# 7. Set the command
CMD ["python", "-u", "handler.py"]