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
use tracing_subscriber::EnvFilter;

use config::EdgeConfig;
use collectors::opcua::OpcUaCollector;
use collectors::modbus::ModbusCollector;
use mqtt::MqttClient;
use inference::InferenceEngine;
use health::HealthMonitor;

/// AMOS Edge Agent — Industrial IoT data ingestion and ML inference
#[derive(Parser, Debug)]
#[command(name = "amos-edge-agent", version, about)]
struct Args {
    /// Path to configuration file
    #[arg(short = 'c', long, default_value = "/etc/amos/edge-config.yaml")]
    config: String,
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| EnvFilter::new("amos_edge_agent=info")),
        )
        .with_target(true)
        .init();

    info!("AMOS Edge Agent starting...");

    // Parse CLI arguments
    let args = Args::parse();

    // Load configuration
    let config = EdgeConfig::from_file(&args.config)
        .expect("Failed to load configuration");
    info!("Configuration loaded for device: {}", config.device_id);

    // Connect to MQTT broker
    let mqtt_client = Arc::new(
        MqttClient::new(
            &config.mqtt.host,
            config.mqtt.port,
            &config.mqtt.client_id,
            config.mqtt.username.as_deref(),
            config.mqtt.password.as_deref(),
            config.mqtt.use_tls,
            config.mqtt.ca_cert_path.as_deref(),
        )
        .await
        .expect("Failed to connect to MQTT broker"),
    );
    info!("Connected to MQTT broker at {}:{}", config.mqtt.host, config.mqtt.port);

    // Initialize the inference engine
    // In production, this loads the actual ONNX model
    let inference = Arc::new(InferenceEngine::new(
        &config.inference.model_path,
        config.inference.anomaly_threshold,
        config.inference.input_size,
        config.inference.buffer_size,
        config.inference.enabled,
        &config.device_id,
    ));

    // Initialize health monitor
    let mut health_monitor = HealthMonitor::new(&config.device_id);

    // Start OPC-UA collector
    let opcua_config = config.clone();
    let opcua_mqtt = mqtt_client.clone();
    let opcua_handle = tokio::spawn(async move {
        let collector = OpcUaCollector::new(opcua_config, opcua_mqtt);
        if let Err(e) = collector.run().await {
            error!("OPC-UA collector exited with error: {}", e);
        }
    });

    // Start Modbus collector (if configured)
    let modbus_handle = if let Some(modbus_cfg) = config.modbus.clone() {
        let modbus_mqtt = mqtt_client.clone();
        let device_id = config.device_id.clone();
        Some(tokio::spawn(async move {
            let collector = ModbusCollector::new(modbus_cfg, device_id, modbus_mqtt);
            if let Err(e) = collector.run().await {
                error!("Modbus collector exited with error: {}", e);
            }
        }))
    } else {
        None
    };

    // Main health publishing loop
    let health_device_id = config.device_id.clone();
    let health_mqtt = mqtt_client.clone();
    let health_interval = config.heartbeat_interval_secs;
    let health_handle = tokio::spawn(async move {
        let mut interval = tokio::time::interval(tokio::time::Duration::from_secs(health_interval));
        loop {
            interval.tick().await;
            // In a real implementation, health_monitor would be shared state
            // For now, publish a simple heartbeat
            let health = serde_json::json!({
                "timestamp": chrono::Utc::now().to_rfc3339(),
                "device_id": health_device_id,
                "status": "running",
            });
            if let Err(e) = health_mqtt
                .publish(
                    &format!("{}/{}/health", "amos", health_device_id),
                    &health.to_string(),
                )
                .await
            {
                warn!("Failed to publish health: {}", e);
            }
        }
    });

    // Wait for shutdown signal
    info!("AMOS Edge Agent is running. Waiting for shutdown signal...");

    match signal::ctrl_c().await {
        Ok(()) => {
            info!("Shutdown signal received. Gracefully shutting down...");
        }
        Err(e) => {
            error!("Failed to listen for shutdown signal: {}", e);
        }
    }

    // Cancel all collector tasks
    opcua_handle.abort();
    if let Some(handle) = modbus_handle {
        handle.abort();
    }
    health_handle.abort();

    // Disconnect MQTT
    mqtt_client.disconnect().await?;

    info!("AMOS Edge Agent shutdown complete.");
    Ok(())
}