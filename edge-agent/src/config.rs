use anyhow::{Context, Result};
use serde::Deserialize;
use std::path::Path;

/// Logging configuration
#[derive(Debug, Clone, Deserialize)]
pub struct LoggingConfig {
    /// Log level (trace, debug, info, warn, error)
    #[serde(default = "default_log_level")]
    pub level: String,
}

fn default_log_level() -> String {
    "info".to_string()
}

/// Top-level configuration for the AMOS Edge Agent
#[derive(Debug, Clone, Deserialize)]
pub struct EdgeConfig {
    /// Logging settings
    #[serde(default)]
    pub logging: LoggingConfig,
    /// Unique identifier for this edge device
    pub device_id: String,
    /// Friendly name for the machine/cell
    pub machine_name: Option<String>,
    /// Location string (e.g., "Building A, Line 3")
    pub location: Option<String>,
    /// MQTT broker connection settings
    pub mqtt: MqttConfig,
    /// OPC-UA connection settings (required)
    pub opcua: OpcUaConfig,
    /// Optional Modbus-TCP connection settings
    pub modbus: Option<ModbusConfig>,
    /// ML inference configuration
    pub inference: InferenceConfig,
    /// Data collection interval in milliseconds
    #[serde(default = "default_collection_interval_ms")]
    pub collection_interval_ms: u64,
    /// Health heartbeat interval in seconds
    #[serde(default = "default_heartbeat_interval_secs")]
    pub heartbeat_interval_secs: u64,
}

fn default_collection_interval_ms() -> u64 {
    100
}

fn default_heartbeat_interval_secs() -> u64 {
    30
}

/// MQTT broker configuration
#[derive(Debug, Clone, Deserialize)]
pub struct MqttConfig {
    /// Broker hostname or IP
    pub host: String,
    /// Broker port (default: 8883 for TLS)
    #[serde(default = "default_mqtt_port")]
    pub port: u16,
    /// Client ID for MQTT session
    pub client_id: String,
    /// Username for authentication
    pub username: Option<String>,
    /// Password for authentication
    pub password: Option<String>,
    /// Path to TLS CA certificate
    pub ca_cert_path: Option<String>,
    /// Whether to use TLS
    #[serde(default = "default_true")]
    pub use_tls: bool,
    /// MQTT topic prefix (default: "amos")
    #[serde(default = "default_topic_prefix")]
    pub topic_prefix: String,
    /// Keepalive interval in seconds
    #[serde(default = "default_keepalive_secs")]
    pub keepalive_secs: u64,
}

fn default_mqtt_port() -> u16 {
    8883
}

fn default_true() -> bool {
    true
}

fn default_topic_prefix() -> String {
    "amos".to_string()
}

fn default_keepalive_secs() -> u64 {
    60
}

/// OPC-UA server connection
#[derive(Debug, Clone, Deserialize)]
pub struct OpcUaConfig {
    /// OPC-UA endpoint URL (e.g., "opc.tcp://192.168.1.100:4840")
    pub endpoint: String,
    /// Application name for OPC-UA session
    pub application_name: String,
    /// Security policy (None, Basic128Rsa15, Basic256, Basic256Sha256)
    #[serde(default = "default_security_policy")]
    pub security_policy: String,
    /// Authentication mode (Anonymous, Username, Certificate)
    #[serde(default = "default_auth_mode")]
    pub auth_mode: String,
    /// Username for OPC-UA auth (if auth_mode = Username)
    pub username: Option<String>,
    /// Password for OPC-UA auth
    pub password: Option<String>,
    /// List of variable node IDs to subscribe to
    pub monitored_nodes: Vec<MonitoredNode>,
    /// Reconnect delay in seconds
    #[serde(default = "default_reconnect_delay")]
    pub reconnect_delay_secs: u64,
}

fn default_security_policy() -> String {
    "None".to_string()
}

fn default_auth_mode() -> String {
    "Anonymous".to_string()
}

fn default_reconnect_delay() -> u64 {
    5
}

/// A single OPC-UA node to monitor
#[derive(Debug, Clone, Deserialize)]
pub struct MonitoredNode {
    /// Node ID string (e.g., "ns=2;i=1234")
    pub node_id: String,
    /// Human-readable display name
    pub display_name: String,
    /// Unit of measurement (e.g., "°C", "mm/s")
    pub unit: Option<String>,
    /// Low warning threshold
    pub warning_low: Option<f64>,
    /// High warning threshold
    pub warning_high: Option<f64>,
    /// Critical low threshold
    pub critical_low: Option<f64>,
    /// Critical high threshold
    pub critical_high: Option<f64>,
}

/// Modbus-TCP connection
#[derive(Debug, Clone, Deserialize)]
pub struct ModbusConfig {
    /// Modbus device IP
    pub host: String,
    /// Modbus port (default: 502)
    #[serde(default = "default_modbus_port")]
    pub port: u16,
    /// Slave/Unit ID
    pub slave_id: u8,
    /// List of registers to read
    pub registers: Vec<ModbusRegister>,
}

fn default_modbus_port() -> u16 {
    502
}

/// A Modbus register definition
#[derive(Debug, Clone, Deserialize)]
pub struct ModbusRegister {
    /// Register address (0-indexed)
    pub address: u16,
    /// Number of registers to read
    pub quantity: u16,
    /// Human-readable name
    pub name: String,
    /// Scale factor (value * scale = engineering unit)
    #[serde(default = "default_scale")]
    pub scale: f64,
    /// Unit string
    pub unit: Option<String>,
}

fn default_scale() -> f64 {
    1.0
}

/// ML inference configuration
#[derive(Debug, Clone, Deserialize)]
pub struct InferenceConfig {
    /// Path to ONNX model file
    #[serde(default = "default_model_path")]
    pub model_path: String,
    /// Anomaly threshold (MSE reconstruction error)
    #[serde(default = "default_anomaly_threshold")]
    pub anomaly_threshold: f64,
    /// Number of sensor values in input vector
    #[serde(default = "default_input_size")]
    pub input_size: usize,
    /// Buffer size for sliding window
    #[serde(default = "default_buffer_size")]
    pub buffer_size: usize,
    /// Enable local inference
    #[serde(default = "default_true")]
    pub enabled: bool,
    /// Number of threads for ONNX Runtime
    #[serde(default = "default_num_threads")]
    pub num_threads: usize,
    /// Friendly model name
    #[serde(default)]
    pub model_name: String,
}

fn default_model_path() -> String {
    "/opt/amos/models/anomaly.onnx".to_string()
}

fn default_anomaly_threshold() -> f64 {
    0.05
}

fn default_input_size() -> usize {
    16
}

fn default_buffer_size() -> usize {
    100
}

fn default_num_threads() -> usize {
    4
}

impl EdgeConfig {
    /// Load configuration from a YAML file (alias for from_file for backward compatibility)
    pub fn load(path: impl AsRef<Path>) -> Result<Self> {
        Self::from_file(path)
    }

    /// Load configuration from a YAML file
    pub fn from_file(path: impl AsRef<Path>) -> Result<Self> {
        let content = std::fs::read_to_string(path.as_ref())
            .context(format!("Failed to read config from {:?}", path.as_ref()))?;
        let config: EdgeConfig =
            serde_yaml::from_str(&content).context("Failed to parse configuration YAML")?;
        Ok(config)
    }

    /// Validate required fields
    pub fn validate(&self) -> Result<()> {
        if self.device_id.is_empty() {
            anyhow::bail!("device_id must not be empty");
        }
        if self.mqtt.host.is_empty() {
            anyhow::bail!("mqtt.host must not be empty");
        }
        if self.opcua.endpoint.is_empty() {
            anyhow::bail!("opcua.endpoint must not be empty");
        }
        if self.inference.enabled && self.inference.model_path.is_empty() {
            anyhow::bail!("inference.model_path must be set when inference is enabled");
        }
        info!("Configuration validated successfully");
        Ok(())
    }

    /// Get the MQTT telemetry topic
    pub fn telemetry_topic(&self) -> String {
        format!("{}/{}/telemetry", self.mqtt.topic_prefix, self.device_id)
    }

    /// Get the MQTT health topic
    pub fn health_topic(&self) -> String {
        format!("{}/{}/health", self.mqtt.topic_prefix, self.device_id)
    }

    /// Get the MQTT alert topic
    pub fn alert_topic(&self) -> String {
        format!("{}/{}/alerts", self.mqtt.topic_prefix, self.device_id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_topic_generation() {
        let config = EdgeConfig {
            logging: LoggingConfig {
                level: "info".to_string(),
            },
            device_id: "test-device-01".to_string(),
            machine_name: None,
            location: None,
            mqtt: MqttConfig {
                host: "localhost".to_string(),
                port: 8883,
                client_id: "test".to_string(),
                username: None,
                password: None,
                ca_cert_path: None,
                use_tls: true,
                topic_prefix: "amos".to_string(),
                keepalive_secs: 60,
            },
            opcua: OpcUaConfig {
                endpoint: "opc.tcp://localhost:4840".to_string(),
                application_name: "test".to_string(),
                security_policy: "None".to_string(),
                auth_mode: "Anonymous".to_string(),
                username: None,
                password: None,
                monitored_nodes: vec![],
                reconnect_delay_secs: 5,
            },
            modbus: None,
            inference: InferenceConfig {
                model_path: "/opt/amos/models/anomaly.onnx".to_string(),
                anomaly_threshold: 0.05,
                input_size: 16,
                buffer_size: 100,
                enabled: true,
                num_threads: 4,
                model_name: "anomaly_detector".to_string(),
            },
            collection_interval_ms: 100,
            heartbeat_interval_secs: 30,
        };

        assert_eq!(config.telemetry_topic(), "amos/test-device-01/telemetry");
        assert_eq!(config.health_topic(), "amos/test-device-01/health");
        assert_eq!(config.alert_topic(), "amos/test-device-01/alerts");
    }
}
