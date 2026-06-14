FROM python:3.11-slim

WORKDIR /app

# Install system deps for ONNX Runtime
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["python", "train_autoencoder.py"]