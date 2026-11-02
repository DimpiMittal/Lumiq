# Lumiq Implementation Roadmap

This roadmap is based on [PROJECT_AUDIT.md](PROJECT_AUDIT.md). Phases are sequenced to make later AI and analytics claims testable and safe. Do not present planned items as implemented.

| Phase | Priority and dependencies | Scope and expected outcome | Testing and exit criteria |
|---|---|---|---|
| 0. Baseline and safety | P0; complete for verified SQLite/local scope | SQLGlot AST validation includes incomplete-SELECT structure checks; DB read-only settings, SQLite authorizer/deadline, 500-row SQL cap, bounded CSV ingestion, session hardening, generic errors, and escaped frontend rendering are implemented. | `47 passed, 0 failed, 0 errors, 0 skipped` under Lumiq `.venv`; legitimate demo SQL and mocked text-to-SQL workflow pass. PostgreSQL/MySQL live enforcement remains unverified. |
| 1. LLM evaluation and benchmarking | P1; only after Phase 0 SQL tests and a legitimate SQLite flow pass | Create a versioned 50+ case dataset, deterministic fixtures, an evaluation runner, metrics, error analysis, provider comparison hooks, and an evaluation dashboard. No model/prompt tuning until a baseline is recorded. | Reproducible provider/model/config records; SQL generation/execution, result equivalence, unsafe rejection, clarification, and latency metrics. Evaluation creates reports only from actual runs; no fabricated accuracy. |
| 2. Modular service boundaries | P1; after or alongside evaluation harness | Extract config, DB adapters/schema catalog, SQL policy/executor, LLM providers/text-to-SQL orchestration, and route handlers from the monolithic module. Add typed validation and structured redacted logs. | Unit and API tests for each service; existing workflows pass regression tests; no secrets or raw provider/DB errors in client responses. |
| 3. Data profiling and EDA | P1; depends on modular services and bounded data access | Add dataset sampling/profile service: dimensions, inferred types, missing/duplicate/cardinality summaries, numerical/categorical stats, correlations, outlier flags, and suitable chart data. | Unit tests against known fixtures, missing/constant/small columns, categorical imbalance, outliers, and invalid inputs. Document statistical assumptions and suppress inappropriate tests. |
| 4. Supervised predictive analytics | P2; depends on EDA and data suitability | Add target/task selection, leakage-aware preprocessing pipelines, baseline and candidate models, validation, metrics, model artifact metadata/serialization, prediction API and explanations. Start with sklearn; add XGBoost only if validated value warrants dependency. | Deterministic synthetic/fixture tests; verify train-only fitting, split isolation, class imbalance handling, metrics, serialization round-trip, and unsuitable-data refusal. Compare to baseline before surfacing model. |
| 5. Segmentation and RFM | P2; depends on EDA and suitable transaction schema | Build RFM only when customer, transaction date, and monetary value are identifiable; otherwise allow documented feature clustering. Standardize appropriate features, evaluate K-means candidates, describe clusters from computed profiles, and avoid arbitrary personas. | Known synthetic cohort tests; cluster stability/silhouette and degenerate data cases; verify segment summaries derive from cluster statistics. |
| 6. Forecasting | P2; depends on EDA and enough dated observations | Validate frequency/gaps, create chronological/walk-forward baselines, compare suitable forecasting approach, and report forecast intervals only when supported. | Time-ordered validation tests; no random split; compare naïve baseline; evaluate MAE/RMSE and guarded MAPE; reject insufficient or irregular data with explanation. |
| 7. Retrieval of business context | P3; depends on schema catalog/glossary and phase 2 benchmark | Begin with retrieval over structured schema/glossary metadata; introduce embeddings/vector storage only if benchmarked retrieval improves relevant schema selection. Ground generated SQL/insight with retrieved context. | Compare retrieval vs full-schema baseline on labeled benchmark; inspect recall and quality; verify no irrelevant/private context leakage. |
| 8. Trust, UX, and portfolio delivery | P1/P2; incrementally after each service | Add clear evidence/limitations and data provenance, feature/model explanations, EDA and evaluation views, responsive UI, exportable reports, accurate docs, and reproducible setup. | Frontend/API integration tests and manual end-to-end checks for empty/error/loading and privacy states; docs match shipped code. |
| 9. Deployment hardening | P3; after stable interfaces | Add Docker, production server configuration, env validation, health/readiness checks, dependency pinning, upload cleanup, rate/resource limits and deployment guidance. | Container build/start checks, health checks, configuration failure tests and security review. Do not claim production readiness without operational evidence. |

Phase 0 is complete for the verified local SQLite/query-safety scope. PostgreSQL/MySQL read-only behavior has not been integration-tested. See [PROJECT_AUDIT.md](PROJECT_AUDIT.md) and [SECURITY.md](SECURITY.md) for exact results and remaining limitations.

## Initial implementation order

1. Phase 0: safety and baseline verification, because current SQL execution and credential handling make feature expansion unsafe.
2. Phase 1: establish a reproducible text-to-SQL benchmark before changing prompts or models.
3. Phase 2: extract service boundaries without changing the frontend contract.
4. Phase 3: deterministic EDA, then the data-dependent ML, segmentation, and forecasting phases.

## Scope control

Do not implement all requested modules as one change. Each phase should land as a runnable increment, include focused tests, and update documentation with implemented status and actual test/evaluation outputs. ML, RFM, and forecasting should refuse unsuitable data instead of manufacturing a result. RAG/vector infrastructure is conditional on benchmark evidence that it improves the workflow.

## Phase 1 implementation plan (prepared, not started)

### Dependency gate

Phase 0 verification is complete for local SQLite. Phase 1 has **not started**. PostgreSQL/MySQL can remain explicitly unverified if no live servers are available; their limitations must appear in the benchmark report. Do not call providers as part of ordinary tests.

### Work sequence

1. Freeze a deterministic SQLite fixture with known business tables and expected results; version the fixture and dataset.
2. Add at least 50 reviewed cases: basic selects, predicates, aggregation, grouping, sorting, joins, subqueries, CTEs, unions, dates, ambiguity/clarification, unsupported requests, malformed output, unknown tables, and adversarial/mutation attempts.
3. For each case store ID, question, fixture/schema version, difficulty, category, expected behavior, expected result or equivalence check, and whether a provider call is required.
4. Build a runner that can use stubbed model outputs for offline regression and opt-in real provider calls for measured provider comparisons. Record provider/model, prompt version, config hash, elapsed time, parse/validation/execution outcomes, result signature, and error category; never store keys or private data.
5. Calculate generation success, execution success, result equivalence, exact match only where appropriate, invalid SQL rate, unsafe rejection, clarification accuracy, and latency percentiles. Distinguish unsupported/ambiguous cases from ordinary failures.
6. Produce machine-readable JSON/CSV results and a human-readable error-analysis report. Add the evaluation dashboard only after actual runs can populate it; show sample count, run date, and model version alongside every metric.

### Phase 1 acceptance criteria

- Dataset has 50+ reviewed cases and stable IDs.
- Offline runner and regression tests run without external API access.
- Provider runs are opt-in, reproducible, and never fabricate missing outputs.
- Metrics are calculated from recorded cases, with denominator and failure breakdown visible.
- Error analysis identifies the next prompt/schema/security improvements; no claimed accuracy until an actual run completes.
- Changes do not weaken Phase 0 SQL validation or database restrictions.

