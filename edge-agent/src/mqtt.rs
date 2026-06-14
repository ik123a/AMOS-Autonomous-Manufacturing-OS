use anyhow::{Context, Result};
use rumqttc::{AsyncClient, Event, MqttOptions, Packet, Publish, QoS, Transport};
use serde::Serialize;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::Mutex;
use tokio::task;
use tracing::{error, info, warn};

/// High-level MQTT client wrapper with reconnection support
pub struct MqttClient {
    client: AsyncClient,
    /// Event loop handle — must be polled
    _event_loop: task::JoinHandle<()>,
    connected: Arc<Mutex<bool>>,
}

impl MqttClient {
    /// Create and connect a new MQTT client
    pub async fn new(
        host: &str,
        port: u16,
        client_id: &str,
        username: Option<&str>,
        password: Option<&str>,
        use_tls: bool,
        ca_cert_path: Option<&str>,
    ) -> Result<Self> {
        let mut mqtt_options = MqttOptions::new(client_id, host, port);
        mqtt_options
            .set_keep_alive(Duration::from_secs(30))
            .set_clean_session(true);

        if let Some(user) = username {
            if let Some(pass) = password {
                mqtt_options.set_credentials(user, pass);
            }
        }

        // TLS configuration
        if use_tls {
            let transport = if let Some(ca_path) = ca_cert_path {
                let ca = std::fs::read(ca_path)
                    .context(format!("Failed to read CA certificate from {}", ca_path))?;
                let ca_cert = rustls_pemfile::certs(&mut ca.as_slice())
                    .collect::<Result<Vec<_>, _>>()
                    .context("Failed to parse CA certificate")?;
                let mut root_store = rustls::RootCertStore::empty();
                for cert in ca_cert {
                    root_store.add(cert).context("Failed to add CA cert")?;
                }
                let tls_config = rustls::ClientConfig::builder()
                    .with_root_certificates(root_store)
                    .with_no_client_auth();
                Transport::tls_with_config(tls_config.into())
            } else {
                // Use webpki-roots for standard CA verification
                Transport::tls_with_defaults().expect("Failed to configure default TLS");
            };
            mqtt_options.set_transport(transport);
        }

        let (client, mut event_loop) = AsyncClient::new(mqtt_options, 100);
        let connected = Arc::new(Mutex::new(false));
        let connected_clone = connected.clone();

        // Spawn event loop to maintain connection and process events
        let _event_loop = task::spawn(async move {
            loop {
                match event_loop.poll().await {
                    Ok(Event::Incoming(Packet::ConnAck(_))) => {
                        info!("MQTT connected successfully");
                        *connected_clone.lock().await = true;
                    }
                    Ok(Event::Incoming(Packet::Publish(p))) => {
                        // Handle incoming messages if needed
                        trace!("Received MQTT message on {}: {:?}", p.topic, p.payload);
                    }
                    Ok(Event::Outgoing(_)) => {}
                    Err(e) => {
                        error!("MQTT event loop error: {:?}", e);
                        *connected_clone.lock().await = false;
                        // Reconnect is automatic via rumqttc
                        tokio::time::sleep(Duration::from_secs(5)).await;
                    }
                    _ => {}
                }
            }
        });

        info!("MQTT client created for {}:{}", host, port);
        Ok(Self {
            client,
            _event_loop,
            connected,
        })
    }

    /// Publish a message to a topic with QoS 1 (at least once)
    pub async fn publish(&self, topic: &str, payload: &str) -> Result<()> {
        self.client
            .publish(topic, QoS::AtLeastOnce, false, payload.as_bytes())
            .await
            .context(format!("Failed to publish to topic {}", topic))?;
        Ok(())
    }

    /// Publish a serializable struct as JSON
    pub async fn publish_json<T: Serialize>(
        &self,
        topic: &str,
        data: &T,
    ) -> Result<()> {
        let payload = serde_json::to_string(data)
            .context("Failed to serialize payload")?;
        self.publish(topic, &payload).await
    }

    /// Subscribe to a topic with QoS 1
    pub async fn subscribe(&self, topic: &str) -> Result<()> {
        self.client
            .subscribe(topic, QoS::AtLeastOnce)
            .await
            .context(format!("Failed to subscribe to {}", topic))?;
        info!("Subscribed to MQTT topic: {}", topic);
        Ok(())
    }

    /// Check if the client is currently connected
    pub async fn is_connected(&self) -> bool {
        *self.connected.lock().await
    }

    /// Disconnect cleanly (graceful shutdown)
    pub async fn disconnect(&self) -> Result<()> {
        self.client
            .disconnect()
            .await
            .context("Failed to disconnect MQTT")?;
        info!("MQTT disconnected");
        Ok(())
    }
}