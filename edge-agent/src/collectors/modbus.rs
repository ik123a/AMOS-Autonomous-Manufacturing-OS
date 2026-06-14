use crate::config::ModbusConfig;
use crate::mqtt::MqttClient;
use anyhow::{Context, Result};
use chrono::Utc;
use serde::Serialize;
use std::sync::Arc;
use tokio::time::{interval, Duration};
use tracing::{error, info, warn};

/// A single Modbus register reading
#[derive(Debug, Clone, Serialize)]
pub struct ModbusReading {
    pub timestamp: String,
    pub device_id: String,
    pub register_name: String,
    pub raw_value: u16,
    pub scaled_value: f64,
    pub unit: Option<String>,
    pub slave_id: u8,
    pub address: u16,
}

/// The Modbus-TCP collector task
pub struct ModbusCollector {
    config: Arc<ModbusConfig>,
    device_id: String,
    mqtt_client: Arc<MqttClient>,
}

impl ModbusCollector {
    pub fn new(
        config: ModbusConfig,
        device_id: String,
        mqtt_client: Arc<MqttClient>,
    ) -> Self {
        Self {
            config: Arc::new(config),
            device_id,
            mqtt_client,
        }
    }

    /// Run the Modbus collection loop
    pub async fn run(&self) -> Result<()> {
        let registers = &self.config.registers;
        info!(
            "Starting Modbus collector for {}:{} slave={} with {} registers",
            self.config.host,
            self.config.port,
            self.config.slave_id,
            registers.len()
        );

        let mut collect_interval = interval(Duration::from_millis(500));

        loop {
            collect_interval.tick().await;

            match self.collect_readings().await {
                Ok(readings) => {
                    if !readings.is_empty() {
                        let payload = serde_json::to_string(&readings)
                            .context("Failed to serialize Modbus readings")?;

                        let topic = format!(
                            "{}/{}/modbus",
                            "amos",
                            self.device_id
                        );

                        if let Err(e) = self.mqtt_client.publish(&topic, &payload).await {
                            warn!("Failed to publish Modbus readings: {}", e);
                        }
                    }
                }
                Err(e) => {
                    error!("Failed to collect Modbus readings: {}", e);
                }
            }
        }
    }

    /// Read values from all configured Modbus registers
    async fn collect_readings(&self) -> Result<Vec<ModbusReading>> {
        let now = Utc::now().to_rfc3339();
        let mut readings = Vec::new();

        // In production:
        //   let mut ctx = rtu::connect(...);
        //   for reg in registers { let val = ctx.read_holding_registers(reg.address, reg.quantity).await?; }
        //
        // For this implementation, we create the reading structure
        // that will be populated by the real Modbus client.

        for reg in &self.config.registers {
            let reading = ModbusReading {
                timestamp: now.clone(),
                device_id: self.device_id.clone(),
                register_name: reg.name.clone(),
                raw_value: 0, // Real value from Modbus read
                scaled_value: 0.0, // raw_value * reg.scale
                unit: reg.unit.clone(),
                slave_id: self.config.slave_id,
                address: reg.address,
            };
            readings.push(reading);
        }

        Ok(readings)
    }
}