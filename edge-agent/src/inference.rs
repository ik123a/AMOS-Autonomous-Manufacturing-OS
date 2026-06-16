//! AMOS Edge Agent — Pure-Rust ONNX inference engine for anomaly detection.
//!
//! Loads a pre-trained autoencoder model using tract-onnx and runs real-time
//! anomaly scoring on streaming sensor data windows. Provides per-sensor explainability
//! via reconstruction error attribution.

use anyhow::{Context, Result};
use ndarray::Array2;
use serde::Serialize;
use std::path::Path;
use tracing::{debug, info};
use tract_onnx::prelude::*;

pub type RunnableModel =
    SimplePlan<TypedFact, Box<dyn TypedOp>, Graph<TypedFact, Box<dyn TypedOp>>>;

/// Per-channel anomaly result with explainability data.
#[derive(Debug, Clone, Serialize)]
pub struct AnomalyResult {
    /// Overall anomaly score [0.0, 1.0] — reconstruction error normalized.
    pub anomaly_score: f64,
    /// Whether this window is flagged as anomalous.
    pub is_anomaly: bool,
    /// The decision threshold used.
    pub threshold: f64,
    /// Per-sensor reconstruction errors (for explainability).
    pub feature_errors: Vec<f64>,
    /// Model name.
    pub model_name: String,
    /// ONNX inference execution time in milliseconds.
    pub execution_time_ms: f64,
}

impl AnomalyResult {
    /// Returns the top N sensors contributing to the anomaly score.
    pub fn top_contributors(&self, n: usize) -> Vec<(&str, f64)> {
        let mut indexed: Vec<(usize, f64)> = self.feature_errors.iter().enumerate().collect();
        indexed.sort_by(|a, b| b.1.partial_cmp(a.1).unwrap());
        indexed
            .into_iter()
            .take(n)
            .map(|(i, v)| (SENSOR_LABELS.get(i).copied().unwrap_or("unknown"), *v))
            .collect()
    }
}

// Sensor labels aligned with training feature order
const SENSOR_LABELS: &[&str] = &[
    "Spindle_Temperature",
    "Spindle_Vibration",
    "Spindle_Torque",
    "Coolant_Flow",
    "Cutting_Speed",
    "Feed_Rate",
];

/// ONNX-based anomaly detection engine using a deep autoencoder.
/// Uses reconstruction error: high error = anomalous behavior.
pub struct InferenceEngine {
    model: RunnableModel,
    input_dim: usize,
    model_name: String,
    threshold: f64,
}

impl InferenceEngine {
    /// Load a pre-trained ONNX autoencoder model using tract-onnx.
    pub async fn new(config: &crate::config::InferenceConfig) -> Result<Self> {
        let model_path = Path::new(&config.model_path);
        if !model_path.exists() {
            anyhow::bail!(
                "ONNX model not found at {} — run training first",
                config.model_path
            );
        }

        info!("Loading ONNX model from: {}", config.model_path);

        let model = tract_onnx::onnx()
            .model_for_path(model_path)
            .context("Failed to load ONNX model via tract")?
            .into_optimized()
            .context("Failed to optimize model")?
            .into_runnable()
            .context("Failed to compile runnable model")?;

        let input_dim = config.input_size;

        let engine = Self {
            model,
            input_dim,
            model_name: config.model_name.clone(),
            threshold: config.anomaly_threshold,
        };

        info!(
            "ONNX engine (tract-onnx) ready: model={}, input_dim={}, threshold={:.4}",
            engine.model_name, engine.input_dim, engine.threshold
        );

        Ok(engine)
    }

    /// Current feature/input dimension.
    pub fn input_dim(&self) -> usize {
        self.input_dim
    }

    /// Run anomaly detection on a single sensor reading window.
    /// `values` must have exactly self.input_dim() elements.
    pub fn detect(&self, values: &[f64]) -> Result<AnomalyResult> {
        let start = std::time::Instant::now();

        // Build input tensor [1, input_dim] as f32
        let mut input_data = ndarray::Array2::<f32>::zeros((1, self.input_dim));
        for (i, &val) in values.iter().enumerate() {
            if i < self.input_dim {
                input_data[[0, i]] = val as f32;
            }
        }
        let input_tensor: Tensor = input_data.into();

        // Run model through tract-onnx
        let outputs = self.model.run(tvec!(input_tensor))?;
        let exec_time = start.elapsed().as_secs_f64() * 1000.0;

        // Extract output tensor — first output is reconstruction
        let output_tensor = &outputs[0];
        let shape = output_tensor.shape();
        let output_dim = shape.last().copied().unwrap_or(self.input_dim);

        // Get output values
        let reconstruction: &[f32] = output_tensor.as_slice::<f32>()?;

        // Compute per-feature reconstruction error (|input - output|)
        let feature_errors: Vec<f64> = values
            .iter()
            .zip(reconstruction.iter())
            .map(|(i, o)| (i - *o as f64).abs())
            .collect();

        // Overall score: mean reconstruction error
        let anomaly_score = feature_errors.iter().sum::<f64>() / feature_errors.len() as f64;
        let is_anomaly = anomaly_score > self.threshold;

        debug!(
            "Anomaly score: {:.4f} (threshold={:.4f}, exec={:.2f}ms)",
            anomaly_score, self.threshold, exec_time
        );

        Ok(AnomalyResult {
            anomaly_score,
            is_anomaly,
            threshold: self.threshold,
            feature_errors,
            model_name: self.model_name.clone(),
            execution_time_ms: exec_time,
        })
    }

    /// Run inference on a batch of windows (for backfill / historical analysis).
    #[allow(dead_code)]
    pub fn detect_batch(&self, batch: &[[f64]]) -> Result<Vec<AnomalyResult>> {
        batch.iter().map(|window| self.detect(window)).collect()
    }
}
