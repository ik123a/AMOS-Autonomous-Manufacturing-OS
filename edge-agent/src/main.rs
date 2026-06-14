pub mod config;
pub mod mqtt;
pub mod collectors;
pub mod inference;
pub mod health;

use anyhow::Result;
use clap::Parser;
use std::sync::Arc;
use tokio::signal;
use tracing::{error, info, warn};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

use crate::collectors::{modbus::ModbusCollector, opcua::OpcUaCollector};
use crate::config::EdgeConfig;
use crate::health::publish_health_loop;
use crate::inference::InferenceEngine;
use crate::mqtt::MqttClient;

const VERSION: &str = env!("CARGO_PKG_VERSION");

#[tokio::main]
async fn main() -> Result<()> {
    // Parse CLI args
    let cli = Cli::parse();
    let config = EdgeConfig::load(&cli.config)?;
    config.validate();

    // Init logging
    init_tracing(&config);
    info!("AMOS Edge Agent v{} starting up...", VERSION);
    info!("Device: {} @ {}", config.device_id, config.location);

    // Shared state
    let shared = Arc::new(SharedState::default());

    // ── MQTT ──────────────────────────────────────────────────────────────────
    let mqtt = MqttClient::new(&config.mqtt).await?;
    let mqtt = Arc::new(tokio::sync::Mutex::new(mqtt));

    // ── Inference Engine ─────────────────────────────────────────────────────
    let inference = if config.inference.enabled {
        let eng = InferenceEngine::new(&config.inference).await?;
        info!("ONNX inference enabled — {} sensor channels", eng.input_dim());
        Some(eng)
    } else {
        warn!("ML inference DISABLED — running in passthrough mode");
        None
    };

    // ── OPC-UA Collector ──────────────────────────────────────────────────────
    let opcua_handles: Vec<_> = config
        .monitoring
        .opcua_nodes
        .iter()
        .filter(|n| n.enabled)
        .map(|node| {
            let config = config.clone();
            let mqtt = mqtt.clone();
            let shared = shared.clone();
            let inference = inference.clone();
            tokio::spawn(async move {
                let collector = OpcUaCollector::new(&config, node);
                collector.run(mqtt, shared, inference).await
            })
        })
        .collect();

    // ── Modbus Collector ──────────────────────────────────────────────────────
    let modbus_handles: Vec<_> = config
        .monitoring
        .modbus_registers
        .iter()
        .filter(|r| r.enabled)
        .map(|reg| {
            let config = config.clone();
            let mqtt = mqtt.clone();
            let shared = shared.clone();
            let inference = inference.clone();
            tokio::spawn(async move {
                let collector = ModbusCollector::new(&config, reg);
                collector.run(mqtt, shared, inference).await
            })
        })
        .collect();

    // ── Health Publisher ───────────────────────────────────────────────────────
    let health_mqtt = mqtt.clone();
    let health_device_id = config.device_id.clone();
    let health_interval = config.monitoring.health_interval_secs;
    let health_handle = tokio::spawn(async move {
        publish_health_loop(health_mqtt, health_device_id, health_interval).await
    });

    // ── Shutdown ───────────────────────────────────────────────────────────────
    info!("All collectors started — listening for shutdown signal...");

    tokio::select! {
        _ = signal::ctrl_c() => {
            info!("SIGINT received — shutting down gracefully");
        }
        _ = signal::SIGTERM => {
            info!("SIGTERM received — shutting down gracefully");
        }
    }

    // Cancel all tasks
    for h in opcua_handles { let _ = h.abort(); }
    for h in modbus_handles { let _ = h.abort(); }
    let _ = health_handle.abort();

    info!("AMOS Edge Agent v{} stopped cleanly", VERSION);
    Ok(())
}

fn init_tracing(config: &EdgeConfig) {
    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new(&config.logging.level));
    tracing_subscriber::registry()
        .with(filter)
        .with(tracing_subscriber::fmt::layer().with_target(true))
        .init();
}

#[derive(Parser, Debug)]
#[command(name = "amos-edge-agent", version = VERSION)]
struct Cli {
    #[arg(long, default_value = "/etc/amos/edge-config.yaml")]
    config: String,
}

#[derive(Default)]
pub struct SharedState {
    pub readings: std::sync::Mutex<Vec<crate::mqtt::SensorReading>>,
    pub errors: std::sync::Mutex<Vec<String>>,
}