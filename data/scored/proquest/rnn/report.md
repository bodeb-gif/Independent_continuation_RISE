# ProQuest GRU experiment

Held-out equal-article average-precision gap, GRU ensemble minus history logistic: +0.0876. Descriptive five-year block interval: [-0.1912, +0.2102]. The held-out result is reported as observed; it is not used to choose a different architecture.

| model | average_precision | roc_auc | brier_score | log_loss | balanced_accuracy | positive_prevalence |
| --- | --- | --- | --- | --- | --- | --- |
| logistic_metadata | 0.5788 | 0.6784 | 0.2183 | 0.6291 | 0.6429 | 0.4088 |
| logistic_metadata_history | 0.5958 | 0.6344 | 0.2364 | 0.6922 | 0.6106 | 0.4088 |
| constant_train_prevalence | 0.4088 | 0.5000 | 0.2437 | 0.6806 | 0.5000 | 0.4088 |
| gru_seed_11 | 0.6471 | 0.7249 | 0.2047 | 0.5918 | 0.6245 | 0.4088 |
| gru_seed_29 | 0.6989 | 0.7899 | 0.1842 | 0.5469 | 0.6854 | 0.4088 |
| gru_seed_47 | 0.6746 | 0.7306 | 0.2042 | 0.5926 | 0.6510 | 0.4088 |
| gru_ensemble | 0.6833 | 0.7614 | 0.1929 | 0.5651 | 0.6605 | 0.4088 |

## Methods and limits

Target: whether an eligible annual machine-verified ProQuest claim matches the first report's deterministic outcome rule. 174,808 benchmark-scored claims are eligible. Pre-1919 NBER-proxy scores are excluded; they depend on retrospectively dated recession states with unavailable real-time label dates.

The GRU receives the previous 12 complete calendar months of national forecast distributions across four topics. Each topic supplies five normalized direction shares, log claim count, and an observed-coverage indicator. The current publication month is excluded. Context includes readable verified claims regardless of whether a future outcome can be scored. Log claim counts describe this sampled export, not newspaper attention or population article denominators.

Current-claim inputs are topic, paper family, voice, hedging category, predicted direction, horizon basis, and numeric horizon. No quote text, speaker identities, realized outcomes, past hit rates, crisis annotations, verifier prose, NBER state, or macro reference value enters the model. A one-layer 24-unit GRU feeds a 32-unit head with 15% dropout. Three preset seeds are averaged; none is selected by test performance.

Training publications precede 1985, validation publications span 1985–1994, and the final test spans 1995–2010. Training and validation labels are purged unless their endpoint plus a conservative three-month release allowance precedes the next split. All scalers, category vocabularies and logistic baselines are fitted on training data only. Validation log loss selects neural epochs. Earlier test-period forecast labels may enter later test histories, as they would become available in sequential use; test outcome labels never do.

Every article receives equal total training weight; equal-article evaluation is primary and claim-weighted metrics are exported too. Logistic metadata plus flattened history is the main sequence-free baseline and receives the same past context. This comparison does not isolate recurrence from neural nonlinearity; a matched feed-forward neural control remains a future experiment. The constant baseline predicts the training correctness prevalence. Average precision summarizes the precision-recall curve; its no-skill reference is the evaluated subset prevalence. Brier score and log loss assess probability quality.

This is one exploratory chronological holdout, not proof of durable forecasting skill. The four test publication blocks share overlapping outcome horizons and few business cycles. Frozen reference outcomes are revised historical series; the release allowance does not establish true vintage availability. Machine-verification and outcome matching still require human validation. Market claims remain a broad-stock-price proxy, and stripped exports cannot support definitive quote deduplication.

Rebuild: python src/proquest_rnn.py after installing requirements-proquest-rnn.txt. Checkpoints, train-only preprocessing, split assignments, predictions, histories, source hashes and exact settings are saved alongside this report. Library references: https://docs.pytorch.org/docs/stable/generated/torch.nn.GRU.html and https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html.
