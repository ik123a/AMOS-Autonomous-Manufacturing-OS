# Contributing to AMOS

Thank you for your interest in contributing to AMOS!

## Quick Start

```bash
# Clone the repository
git clone https://github.com/ik123a/AMOS-Autonomous-Manufacturing-OS.git
cd AMOS-Autonomous-Manufacturing-OS

# Edge Agent (requires Rust 1.76+)
cd edge-agent && cargo build --release
./target/release/amos-edge-agent --config config/edge-config.yaml

# Cloud Stack (requires Docker)
cd ../cloud-core && docker-compose up -d

# Dashboard (requires Node 20+)
cd ../dashboard && npm install && npm run dev
```

## Development Setup

### Prerequisites
- Rust 1.76+ (for edge agent)
- Python 3.11+ (for cloud services)
- Node.js 20+ (for dashboard)
- Docker & Docker Compose (for local cloud stack)
- Kubernetes 1.28+ (for production)

### Recommended Tools
- VSCode with rust-analyzer, ESLint, Prettier
- Docker Desktop for local container testing
- kubectl for K8s deployments

## Code Style

| Language | Style | Command |
|----------|-------|---------|
| Rust | rustfmt + clippy | cargo fmt && cargo clippy -- -D warnings |
| Python | PEP 8, max 120 chars | flake8 . --max-line-length=120 --ignore=E501,W503 |
| TypeScript | ESLint + Prettier | npm run lint (in dashboard/) |

## Commit Message Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add federated learning aggregation endpoint
fix: resolve MQTT reconnection race condition
docs: update API reference for alert service
refactor: split ingestion service into producer/consumer
test: add integration tests for OPC-UA collector
chore: update MLflow Docker image version
```

## Pull Request Process

1. Fork the repository and create a feature branch from main
2. Make your changes with tests (unit tests required for new functions)
3. Run the full lint suite: cargo clippy && flake8 . && npm run lint
4. Ensure all existing tests pass
5. Open a PR with a clear description linking any related issues
6. Request review from a maintainer
7. Address feedback and squash-merge when approved

## Testing

```bash
# Edge agent unit tests
cargo test --manifest-path=edge-agent/Cargo.toml

# Cloud services
pip install pytest httpx
pytest cloud-core/*/tests/ -v

# Dashboard
cd dashboard && npm test

# Full integration (requires Docker)
docker-compose -f cloud-core/docker-compose.yml up -d
# Then run edge agent against the local stack
```

## Architecture Decisions

For significant architectural changes, please open an issue first to discuss the proposed changes. This allows us to align on the approach before you invest significant time writing code.

See docs/architecture.md for the full system design.