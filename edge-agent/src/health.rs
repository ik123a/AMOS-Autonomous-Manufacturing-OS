use anyhow::Result;
use chrono::Utc;
use serde::Serialize;
use sysinfo::{Disks, Networks, System};
use tracing::info;

/// System health status
#[derive(Debug, Clone, Serialize)]
pub struct HealthStatus {
    pub timestamp: String,
    pub device_id: String,
    pub status: String, // "healthy", "degraded", "critical"
    pub uptime_seconds: u64,
    pub cpu_usage_percent: f32,
    pub memory_usage_percent: f64,
    pub memory_used_bytes: u64,
    pub memory_total_bytes: u64,
    pub disk_usage_percent: f64,
    pub network_rx_bytes: u64,
    pub network_tx_bytes: u64,
    pub opcua_connected: bool,
    pub mqtt_connected: bool,
    pub model_loaded: bool,
    pub temperature_celsius: Option<f64>,
}

/// System health monitor
pub struct HealthMonitor {
    device_id: String,
    system: System,
    disks: Disks,
    networks: Networks,
    start_time: chrono::DateTime<Utc>,
    opcua_connected: bool,
    mqtt_connected: bool,
    model_loaded: bool,
}

impl HealthMonitor {
    pub fn new(device_id: &str) -> Self {
        let mut system = System::new();
        system.refresh_all();

        Self {
            device_id: device_id.to_string(),
            system,
            disks: Disks::new_with_refreshed_list(),
            networks: Networks::new_with_refreshed_list(),
            start_time: Utc::now(),
            opcua_connected: false,
            mqtt_connected: false,
            model_loaded: false,
        }
    }

    /// Update connection status (called by other modules)
    pub fn update_connection_status(&mut self, opcua: bool, mqtt: bool) {
        self.opcua_connected = opcua;
        self.mqtt_connected = mqtt;
    }

    /// Update model status
    pub fn update_model_status(&mut self, loaded: bool) {
        self.model_loaded = loaded;
    }

    /// Collect current health metrics
    pub fn collect(&mut self) -> HealthStatus {
        self.system.refresh_cpu();
        self.system.refresh_memory();
        self.disks.refresh();
        self.networks.refresh();

        let uptime = (Utc::now() - self.start_time).num_seconds() as u64;

        // CPU: average across all cores
        let cpu_usage = self.system.global_cpu_usage();

        // Memory
        let mem_total = self.system.total_memory();
        let mem_used = self.system.used_memory();
        let mem_pct = if mem_total > 0 {
            (mem_used as f64 / mem_total as f64) * 100.0
        } else {
            0.0
        };

        // Disk: use first disk
        let disk_pct = self.disks.first().map_or(0.0, |d| {
            let total = d.total_space();
            let available = d.available_space();
            if total > 0 {
                ((total - available) as f64 / total as f64) * 100.0
            } else {
                0.0
            }
        });

        // Network
        let (rx_bytes, tx_bytes) = self
            .networks
            .iter()
            .fold((0u64, 0u64), |(rx, tx), (_, data)| {
                (rx + data.total_received(), tx + data.total_transmitted())
            });

        // Determine overall status
        let status = {
            let mut issues = Vec::new();
            if !self.opcua_connected {
                issues.push("OPC-UA disconnected");
            }
            if !self.mqtt_connected {
                issues.push("MQTT disconnected");
            }
            if !self.model_loaded {
                issues.push("Model not loaded");
            }
            if cpu_usage > 90.0 {
                issues.push("CPU overloaded");
            }
            if mem_pct > 90.0 {
                issues.push("Memory overloaded");
            }

            if issues.is_empty() {
                "healthy".to_string()
            } else if issues.len() <= 2 {
                format!("degraded: {}", issues.join(", "))
            } else {
                format!("critical: {}", issues.join(", "))
            }
        };

        let health = HealthStatus {
            timestamp: Utc::now().to_rfc3339(),
            device_id: self.device_id.clone(),
            status,
            uptime_seconds: uptime,
            cpu_usage_percent: cpu_usage,
            memory_usage_percent: mem_pct,
            memory_used_bytes: mem_used,
            memory_total_bytes: mem_total,
            disk_usage_percent: disk_pct,
            network_rx_bytes: rx_bytes,
            network_tx_bytes: tx_bytes,
            opcua_connected: self.opcua_connected,
            mqtt_connected: self.mqtt_connected,
            model_loaded: self.model_loaded,
            temperature_celsius: None, // Would come from hardware sensors
        };

        info!(
            "Health: cpu={:.1}% mem={:.1}% status={}",
            cpu_usage, mem_pct, health.status
        );

        health
    }
}

/// Publish health status to MQTT broker at regular intervals.
pub async fn publish_health_loop(
    mqtt: std::sync::Arc<tokio::sync::Mutex<crate::mqtt::MqttClient>>,
    device_id: String,
    interval_secs: u64,
) {
    let mut monitor = HealthMonitor::new(&device_id);

    loop {
        tokio::time::sleep(tokio::time::Duration::from_secs(interval_secs)).await;

        let health = monitor.collect();
        let payload = serde_json::to_string(&health).unwrap_or_default();

        let topic = format!("amos/{}/health", device_id);
        let mqtt = mqtt.lock().await;
        if let Err(e) = mqtt.publish("health", &payload).await {
            tracing::warn!("Failed to publish health: {}", e);
        }
    }
}