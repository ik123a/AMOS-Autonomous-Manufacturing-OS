//! AMOS Edge Agent — ONNX Runtime inference engine for anomaly detection.
//!
//! Loads a pre-trained autoencoder model and runs real-time anomaly scoring
//! on streaming sensor data windows. Provides per-sensor explainability via
//! reconstruction error attribution.

use anyhow::{Context, Result};
use ndarray::Array2;
use onnxruntime::session::{GraphOptimizationLevel, Session, SessionOptions};
use serde::Serialize;
use std::path::Path;
use std::time::Duration;
use tracing::{debug, info, warn};

use crate::config::InferenceConfig;

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
    session: Session,
    input_dim: usize,
    model_name: String,
    threshold: f64,
}

impl InferenceEngine {
    /// Load a pre-trained ONNX autoencoder model.
    pub async fn new(config: &crate::config::InferenceConfig) -> Result<Self> {
        let model_path = Path::new(&config.model_path);
        if !model_path.exists() {
            anyhow::bail!(
                "ONNX model not found at {} — run training first",
                config.model_path
            );
        }

        info!("Loading ONNX model from: {}", config.model_path);

        let mut session_options = SessionOptions::default();
        session_options.set_graph_optimization_level(GraphOptimizationLevel::Level3);
        session_options.set_inter_op_num_threads(config.num_threads as i32);
        session_options.set_intra_op_num_threads(config.num_threads as i32);
        session_options.set_session_timeout(Duration::from_secs(300));

        let session = Session::from_file(&session_options, &config.model_path)
            .context("Failed to load ONNX model")?;

        // Infer input dimension from session input metadata
        let inputs = session.get_inputs().ok();
        let input_dim = inputs
            .and_then(|i| i.input_type().as_tensor())
            .map(|t| t.dims().last().copied().unwrap_or(config.input_size as i64) as usize)
            .unwrap_or(config.input_size);

        let engine = Self {
            session,
            input_dim,
            model_name: config.model_name.clone(),
            threshold: config.anomaly_threshold,
        };

        info!(
            "ONNX engine ready: model={}, input_dim={}, threshold={:.4}",
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
        let input: Array2<f32> = Array2::from_shape_vec((1, self.input_dim), {
            let mut v = Vec::with_capacity(self.input_dim);
            for (i, &val) in values.iter().enumerate() {
                if i < self.input_dim {
                    v.push(val as f32);
                }
            }
            v
        })
        .context("invalid input shape")?;

        let outputs = self.session.run(vec![input.into()])?;
        let exec_time = start.elapsed().as_secs_f64() * 1000.0;

        // Extract output tensor — first output is reconstruction
        let output_tensor = &outputs[0];
        let shape = output_tensor.dimensions();
        let output_dim = shape.last().copied().unwrap_or(self.input_dim as i64) as usize;

        // Get output values
        let mut reconstruction = vec![0.0f32; output_dim];
        output_tensor.copy_to_slice(&mut reconstruction);

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
