# Stage 1: Build the Rust edge agent
FROM rust:1.76-slim-bookworm AS builder

RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    cmake \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy manifests first for dependency caching
COPY Cargo.toml Cargo.lock* ./
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release 2>/dev/null || true

# Now copy the real source
COPY src/ src/
RUN cargo build --release

# Stage 2: Runtime image - minimal Debian
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    libopcua0 \
    && rm -rf /var/lib/apt/lists/*

# Create amos user
RUN useradd -m -s /bin/bash amos

# Copy binary
COPY --from=builder /app/target/release/amos-edge-agent /usr/local/bin/

# Create directories
RUN mkdir -p /etc/amos/certs /opt/amos/models /var/log/amos && \
    chown -R amos:amos /etc/amos /opt/amos /var/log/amos

# Copy default config
COPY config/edge-config.yaml /etc/amos/edge-config.yaml

USER amos
WORKDIR /opt/amos

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD ["/usr/local/bin/amos-edge-agent", "--check-health"]

ENTRYPOINT ["/usr/local/bin/amos-edge-agent"]
CMD ["--config", "/etc/amos/edge-config.yaml"]