//! AMOS Edge Agent — MQTT client with TLS support via rumqttc.

use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use rumqttc::{AsyncClient, Event, MqttOptions, Packet, QoS, Transport};
use serde::Serialize;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::Mutex;
use tracing::{debug, error, info, warn};

use crate::config::MqttConfig;

#[derive(Debug, Clone, Serialize)]
pub struct SensorReading {
    pub timestamp: DateTime<Utc>,
    #[serde(rename = "device_id")]
    pub device_id: String,
    #[serde(rename = "machine_name")]
    pub machine_name: String,
    pub location: String,
    pub readings: Vec<Reading>,
}

#[derive(Debug, Clone, Serialize)]
pub struct Reading {
    #[serde(rename = "sensor_name")]
    pub sensor_name: String,
    pub value: f64,
    pub unit: String,
    pub quality: String,
}

/// MQTT client wrapper with reconnection and message publishing.
pub struct MqttClient {
    client: AsyncClient,
    topic_prefix: String,
}

impl MqttClient {
    /// Connect to the MQTT broker with TLS.
    pub async fn new(config: &MqttConfig) -> Result<Self> {
        let mut mqttoptions = MqttOptions::new(
            &config.client_id,
            &config.host,
            config.port,
        );
        mqttoptions.set_keep_alive(Duration::from_secs(config.keepalive_secs));

        // TLS configuration
        if config.use_tls {
            mqttoptions.set_transport(Transport::tls_with_default_config());
        } else {
            mqttoptions.set_transport(Transport::clear());
        }

        let (client, mut eventloop) = AsyncClient::new(mqttoptions, 100);

        // Spawn background connection handler with reconnection
        let host = config.host.clone();
        let port = config.port;
        let use_tls = config.use_tls;
        let client_id = config.client_id.clone();
        tokio::spawn(async move {
            loop {
                match eventloop.poll().await {
                    Ok(Event::Incoming(Packet::PingResp)) => {
                        debug!("MQTT ping response from {}:{}", host, port);
                    }
                    Ok(Event::Incoming(Packet::ConnAck(_))) => {
                        info!("Connected to MQTT broker {}:{}", host, port);
                    }
                    Ok(Event::Incoming(i)) => {
                        debug!("MQTT incoming: {:?}", i);
                    }
                    Ok(Event::Outgoing(_)) => {}
                    Err(e) => {
                        error!("MQTT connection error: {}. Reconnecting in 5s...", e);
                        tokio::time::sleep(Duration::from_secs(5)).await;
                        // Reconnection is automatic via AsyncClient
                    }
                }
            }
        });

        info!(
            "MQTT client configured: {}:{} (TLS={}, topic_prefix={})",
            config.host, config.port, config.use_tls, config.topic_prefix
        );

        Ok(Self {
            client,
            topic_prefix: config.topic_prefix.clone(),
        })
    }

    /// Publish sensor telemetry to the cloud.
    pub async fn publish_reading(&self, reading: &SensorReading) -> Result<()> {
        let topic = format!("{}/telemetry", self.topic_prefix);
        let payload = serde_json::to_string(reading)
            .context("serialize sensor reading")?;

        self.client
            .publish(&topic, QoS::AtLeastOnce, false, payload.as_bytes())
            .await
            .context("mqtt publish")
            .map_err(Into::into)
    }

    /// Publish a raw JSON payload to a topic.
    pub async fn publish(&self, topic_suffix: &str, payload: &str) -> Result<()> {
        let topic = format!("{}/{}", self.topic_prefix, topic_suffix);
        self.client
            .publish(&topic, QoS::AtLeastOnce, false, payload.as_bytes())
            .await
            .context("mqtt publish")
            .map_err(Into::into)
    }
}