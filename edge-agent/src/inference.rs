use anyhow::{Context, Result};
use chrono::Utc;
use serde::Serialize;
use std::sync::Arc;
use tokio::sync::Mutex;
use tracing::{error, info, warn};

/// Anomaly detection result from the inference engine
#[derive(Debug, Clone, Serialize)]
pub struct AnomalyResult {
    pub timestamp: String,
    pub device_id: String,
    pub anomaly_score: f64,
    pub threshold: f64,
    pub is_anomaly: bool,
    pub reconstruction_error: Vec<f64>,
    pub sensor_contributions: Vec<SensorContribution>,
}

/// Per-sensor contribution to the anomaly score (for explainability)
#[derive(Debug, Clone, Serialize)]
pub struct SensorContribution {
    pub sensor_name: String,
    pub value: f64,
    pub expected_value: f64,
    pub error: f64,
    pub contribution_pct: f64,
}

/// The ONNX Runtime inference engine for the autoencoder
pub struct InferenceEngine {
    model_path: String,
    threshold: f64,
    input_size: usize,
    buffer_size: usize,
    enabled: bool,
    device_id: String,
    // Sliding window buffer of recent readings
    buffer: Arc<Mutex<Vec<f64>>>,
}

impl InferenceEngine {
    pub fn new(
        model_path: &str,
        threshold: f64,
        input_size: usize,
        buffer_size: usize,
        enabled: bool,
        device_id: &str,
    ) -> Self {
        Self {
            model_path: model_path.to_string(),
            threshold,
            input_size,
            buffer_size,
            enabled,
            device_id: device_id.to_string(),
            buffer: Arc::new(Mutex::new(Vec::with_capacity(buffer_size))),
        }
    }

    /// Add a sensor value to the sliding window buffer
    pub async fn add_reading(&self, value: f64) -> usize {
        let mut buf = self.buffer.lock().await;
        buf.push(value);
        let len = buf.len();
        // Trim buffer if exceeding max size
        while buf.len() > self.buffer_size {
            buf.remove(0);
        }
        len
    }

    /// Get the current buffer of sensor readings
    pub async fn get_buffer(&self) -> Vec<f64> {
        self.buffer.lock().await.clone()
    }

    /// Run inference on the current buffer
    /// Returns the anomaly score (MSE reconstruction error)
    pub async fn infer(&self, input_vector: &[f64]) -> Result<AnomalyResult> {
        if !self.enabled {
            return Ok(AnomalyResult {
                timestamp: Utc::now().to_rfc3339(),
                device_id: self.device_id.clone(),
                anomaly_score: 0.0,
                threshold: self.threshold,
                is_anomaly: false,
                reconstruction_error: vec![0.0; input_vector.len()],
                sensor_contributions: vec![],
            });
        }

        let _input_len = input_vector.len();
        if _input_len != self.input_size {
            // Pad or truncate to expected size
            let mut adjusted = input_vector.to_vec();
            if adjusted.len() < self.input_size {
                adjusted.resize(self.input_size, 0.0);
            } else {
                adjusted.truncate(self.input_size);
            }
            return self.run_model(&adjusted).await;
        }

        self.run_model(input_vector).await
    }

    /// Execute the ONNX model
    async fn run_model(&self, input_vector: &[f64]) -> Result<AnomalyResult> {
        // In production, this uses the `ort` crate to load and run an ONNX model:
        //
        //   let session = ort::Session::builder()
        //       .with_model_from_file(&self.model_path)?;
        //
        //   let input_tensor = ort::inputs! {
        //       "sensor_input" => ort::ndarray::Array2::from_shape_vec(
        //           (1, self.input_size),
        //           input_vector.to_vec()
        //       )?
        //   }?;
        //
        //   let outputs = session.run(input_tensor)?;
        //   let reconstructed: ort::ndarray::Array2<f32> = outputs[0].try_extract()?;
        //
        //   // MSE = mean((input - reconstruction)^2)
        //   let mse = reconstructed
        //       .iter()
        //       .zip(input_vector.iter())
        //       .map(|(r, i)| (r - *i as f32).powi(2) as f64)
        //       .sum::<f64>()
        //       / self.input_size as f64;

        // For this implementation, simulate inference with a mock score
        let mse = self.mock_inference(input_vector);
        let is_anomaly = mse > self.threshold;

        // Compute per-sensor reconstruction errors
        let reconstruction_error: Vec<f64> = input_vector
            .iter()
            .map(|v| {
                // Simulate reconstruction: near-identity for normal, shifted for anomalies
                let rec = v * (1.0 - self.threshold * (if is_anomaly { 5.0 } else { 0.1 }));
                (v - rec).powi(2)
            })
            .collect();

        let total_error: f64 = reconstruction_error.iter().sum();
        let sensor_contributions: Vec<SensorContribution> = reconstruction_error
            .iter()
            .enumerate()
            .map(|(i, err)| SensorContribution {
                sensor_name: format!("sensor_{}", i),
                value: input_vector[i],
                expected_value: input_vector[i] * (1.0 - 0.1 * self.threshold),
                error: *err,
                contribution_pct: if total_error > 0.0 {
                    (err / total_error) * 100.0
                } else {
                    0.0
                },
            })
            .collect();

        if is_anomaly {
            warn!(
                "ANOMALY DETECTED: score={:.6}, threshold={:.6}",
                mse, self.threshold
            );
        }

        Ok(AnomalyResult {
            timestamp: Utc::now().to_rfc3339(),
            device_id: self.device_id.clone(),
            anomaly_score: mse,
            threshold: self.threshold,
            is_anomaly,
            reconstruction_error,
            sensor_contributions,
        })
    }

    /// Mock inference for prototype — replaces real ONNX model execution
    fn mock_inference(&self, input_vector: &[f64]) -> f64 {
        // Simulate anomaly detection:
        // - Normal operation: low MSE (~0.001-0.01)
        // - Anomalous: high MSE based on deviation from "normal" pattern

        // Simulate a learned "normal" pattern (mean of healthy training data)
        let normal_pattern: Vec<f64> = (0..self.input_size)
            .map(|i| 50.0 + 10.0 * (i as f64 / self.input_size as f64 * std::f64::consts::PI).sin())
            .collect();

        // Calculate MSE against expected normal pattern
        let mse: f64 = input_vector
            .iter()
            .zip(normal_pattern.iter())
            .map(|(actual, expected)| (actual - expected).powi(2))
            .sum::<f64>()
            / self.input_size as f64;

        // Add noise floor
        mse + 0.001
    }

    /// Reset the internal buffer
    pub async fn reset_buffer(&self) {
        let mut buf = self.buffer.lock().await;
        buf.clear();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_inference_normal() {
        let engine = InferenceEngine::new(
            "/opt/amos/models/anomaly.onnx",
            0.05,
            16,
            100,
            true,
            "test-device",
        );

        // Create a "normal" input vector
        let input: Vec<f64> = (0..16)
            .map(|i| 50.0 + 10.0 * (i as f64 / 16.0 * std::f64::consts::PI).sin())
            .collect();

        let result = engine.infer(&input).await.unwrap();
        assert!(!result.is_anomaly);
        assert!(result.anomaly_score < 0.05);
    }
}