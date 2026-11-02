# Machine Learning Pipeline Status

## Current status

No conventional machine-learning training, model evaluation, serialization, prediction API, segmentation, or forecasting pipeline is currently implemented. Lumiq calls hosted pretrained LLMs for text-to-SQL and summaries; that is not model training.

## Planned design

Start with a deterministic dataset suitability/profile stage. A supervised workflow should define the prediction target, guard against leakage, split data before fitting preprocessors, compare a simple baseline with candidate estimators, use task-appropriate validation and metrics, serialize the full preprocessing/model pipeline with metadata, and explain unsupported or poor-quality cases rather than training automatically.

Time-series evaluation must preserve chronology and use walk-forward validation. Segmentation should use RFM only when customer, transaction-time, and monetary fields are supported by the dataset; cluster interpretation must be computed from cluster profiles, not assigned arbitrary personas. Forecasting and segmentation should be added only after suitable fixtures and tests exist.

No model performance numbers are available. Do not claim ML features until implemented and tested.
