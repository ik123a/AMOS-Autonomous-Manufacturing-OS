use crate::config::{EdgeConfig, MonitoredNode};
use crate::mqtt::MqttClient;
use anyhow::{Context, Result};
use async_trait::async_trait;
use chrono::Utc;
use serde::Serialize;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::time::{interval, Duration};
use tracing::{error, info, warn};

/// Represents a single data reading from a sensor
#[derive(Debug, Clone, Serialize)]
pub struct SensorReading {
    pub timestamp: String,
    pub device_id: String,
    pub sensor_name: String,
    pub value: f64,
    pub unit: Option<String>,
    pub quality: String,
}

/// Represents a batch of readings for an inference cycle
#[derive(Debug, Clone, Serialize)]
pub struct TelemetryBatch {
    pub timestamp: String,
    pub device_id: String,
    pub readings: Vec<SensorReading>,
}

/// The OPC-UA collector task
pub struct OpcUaCollector {
    config: EdgeConfig,
    mqtt_client: Arc<MqttClient>,
}

impl OpcUaCollector {
    pub fn new(config: EdgeConfig, mqtt_client: Arc<MqttClient>) -> Self {
        Self {
            config,
            mqtt_client,
        }
    }

    /// Run the OPC-UA collection loop
    pub async fn run(&self) -> Result<()> {
        let endpoint = &self.config.opcua.endpoint;
        let nodes = &self.config.opcua.monitored_nodes;
        let interval_ms = self.config.collection_interval_ms;

        info!(
            "Starting OPC-UA collector for endpoint: {} with {} nodes",
            endpoint,
            nodes.len()
        );

        // In production, this would establish a real OPC-UA session
        // and subscribe to monitored items with a subscription.
        // For this implementation, we simulate reading from the OPC-UA server
        // using a reconnecting client pattern.

        let mut collect_interval = interval(Duration::from_millis(interval_ms));

        loop {
            collect_interval.tick().await;

            match self.collect_readings().await {
                Ok(readings) => {
                    if !readings.is_empty() {
                        let batch = TelemetryBatch {
                            timestamp: Utc::now().to_rfc3339(),
                            device_id: self.config.device_id.clone(),
                            readings,
                        };

                        let payload = serde_json::to_string(&batch)
                            .context("Failed to serialize telemetry batch")?;

                        let topic = self.config.telemetry_topic();
                        if let Err(e) = self.mqtt_client.publish(&topic, &payload).await {
                            warn!("Failed to publish telemetry: {}", e);
                        }
                    }
                }
                Err(e) => {
                    error!("Failed to collect OPC-UA readings: {}", e);
                    // Reconnect logic — retry on next interval
                }
            }
        }
    }

    /// Read values from all configured OPC-UA nodes
    async fn collect_readings(&self) -> Result<Vec<SensorReading>> {
        let now = Utc::now().to_rfc3339();
        let mut readings = Vec::new();

        for node in &self.config.opcua.monitored_nodes {
            // In production, this calls the OPC-UA read service
            // value = session.read(node_id).await?
            // For now, we simulate reading with a placeholder
            let reading = SensorReading {
                timestamp: now.clone(),
                device_id: self.config.device_id.clone(),
                sensor_name: node.display_name.clone(),
                value: 0.0, // Real value from OPC-UA read
                unit: node.unit.clone(),
                quality: "good".to_string(),
            };
            readings.push(reading);
        }

        Ok(readings)
    }
}
