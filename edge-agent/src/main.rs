pub mod collectors;
pub mod config;
pub mod health;
pub mod inference;
pub mod mqtt;

use anyhow::Result;
use clap::Parser;
use std::sync::Arc;
use tokio::signal;
use tracing::{error, info, warn};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

use crate::collectors::{modbus::ModbusCollector, opcua::OpcUaCollector};
use crate::config::EdgeConfig;
use crate::health::publish_health_loop;
use crate::mqtt::MqttClient;

const VERSION: &str = env!("CARGO_PKG_VERSION");

#[tokio::main]
async fn main() -> Result<()> {
    // Parse CLI args
    let cli = Cli::parse();
    let config = EdgeConfig::from_file(&cli.config)?;
    config.validate();

    // Init logging
    init_tracing(&config.logging.level);
    info!("AMOS Edge Agent v{} starting up...", VERSION);
    info!(
        "Device: {} @ {}",
        config.device_id,
        config.location.as_deref().unwrap_or("unknown")
    );

    // Shared state (reserved for future per-device state)
    let _shared = Arc::new(());

    // ── MQTT ──────────────────────────────────────────────────────────────────
    let mqtt = MqttClient::new(&config.mqtt).await?;
    let mqtt = Arc::new(tokio::sync::Mutex::new(mqtt));

    // ── Inference Engine ──────────────────────────────────────────────────────
    let inference = if config.inference.enabled {
        let eng = InferenceEngine::new(&config.inference).await?;
        info!(
            "ONNX inference enabled — {} input dims, threshold={:.4}",
            eng.input_dim(),
            config.inference.anomaly_threshold
        );
        Some(eng)
    } else {
        warn!("ML inference DISABLED — running in passthrough mode");
        None
    };

    // ── OPC-UA Collector — one per endpoint, handles all nodes ───────────────
    let opcua_endpoint = config.opcua.endpoint.clone();
    let opcua_nodes_count = config.opcua.monitored_nodes.len();
    let mqtt_for_opcua = mqtt.clone();
    let device_id_opcua = config.device_id.clone();
    let config_opcua = config.clone();
    let opcua_handle = tokio::spawn(async move {
        let collector = OpcUaCollector::new(config_opcua, mqtt_for_opcua);
        info!(
            "Starting OPC-UA collector: {} ({} nodes)",
            opcua_endpoint, opcua_nodes_count
        );
        collector.run().await
    });

    // ── Modbus Collector — one per ModbusConfig, handles all registers ───────
    let modbus_handle = if let Some(ref modbus_cfg) = config.modbus {
        let mqtt_for_modbus = mqtt.clone();
        let device_id_modbus = config.device_id.clone();
        let config_modbus = config.clone();
        Some(tokio::spawn(async move {
            let collector = ModbusCollector::new(config_modbus, device_id_modbus, mqtt_for_modbus);
            collector.run().await
        }))
    } else {
        info!("No Modbus devices configured — skipping");
        None
    };

    // ── Health Publisher ───────────────────────────────────────────────────────
    let health_mqtt = mqtt.clone();
    let health_device_id = config.device_id.clone();
    let health_interval = config.heartbeat_interval_secs;
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
    let _ = opcua_handle.abort();
    if let Some(h) = modbus_handle {
        let _ = h.abort();
    }
    let _ = health_handle.abort();

    info!("AMOS Edge Agent v{} stopped cleanly", VERSION);
    Ok(())
}

fn init_tracing(level: &str) {
    let filter = EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new(level));
    tracing_subscriber::registry()
        .with(filter)
        .with(tracing_subscriber::fmt::layer().with_target(true))
        .init();
}

#[derive(Parser, Debug)]
#[command(name = "amos-edge-agent", version = VERSION)]
struct Cli {
    /// Path to the edge configuration YAML file
    #[arg(long, default_value = "/etc/amos/edge-config.yaml")]
    config: String,
}
