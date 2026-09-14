"""Public numerical reference extracted from the frozen September 3 evaluator. Documentary fixtures and source-file manifests omitted. Numeric classifier and policy routines are unchanged in meaning."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import platform
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable
import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
LABELS = ('ACCEPT', 'QUALIFY', 'SIMULATED', 'NARRATIVE', 'QUARANTINE')
LABEL_INDEX = {name: index for index, name in enumerate(LABELS)}
FEATURES = ('source_authority', 'direct_observation', 'reproducibility', 'independent_corroboration', 'provenance_completeness', 'explicit_simulation_label', 'narrative_symbolism', 'contradiction_score', 'hazard_score', 'ambiguity_score', 'numeric_specificity', 'tamper_score', 'authority_consent', 'uncertainty_disclosed', 'mechanism_defined', 'metadata_integrity', 'unsupported_existence_claim')
F = {name: index for index, name in enumerate(FEATURES)}
CLASS_PRIOR = np.asarray([0.19, 0.24, 0.18, 0.16, 0.23], dtype=float)
CLASS_MEANS = np.asarray([[0.83, 0.86, 0.78, 0.73, 0.86, 0.03, 0.03, 0.07, 0.16, 0.09, 0.65, 0.02, 0.82, 0.75, 0.79, 0.92, 0.04], [0.6, 0.43, 0.45, 0.3, 0.66, 0.1, 0.08, 0.2, 0.25, 0.45, 0.66, 0.03, 0.68, 0.55, 0.51, 0.8, 0.15], [0.45, 0.15, 0.74, 0.12, 0.82, 0.91, 0.2, 0.1, 0.2, 0.2, 0.72, 0.02, 0.78, 0.88, 0.68, 0.91, 0.05], [0.25, 0.07, 0.18, 0.05, 0.48, 0.2, 0.91, 0.15, 0.25, 0.53, 0.58, 0.04, 0.45, 0.31, 0.15, 0.7, 0.45], [0.24, 0.12, 0.2, 0.08, 0.27, 0.12, 0.28, 0.76, 0.69, 0.7, 0.72, 0.4, 0.19, 0.21, 0.24, 0.48, 0.75]], dtype=float)
SEEDS = (104729, 130363, 169087, 224737, 275015, 350377, 425623, 500009, 600011, 700001, 800011, 900001)
SPLIT_SIZES = {'BUILD': 4200, 'CAL': 1600, 'SELECT': 1800, 'HELDOUT': 3600}
FINAL_HELDOUT_OFFSET = 173

@dataclass(frozen=True)
class Dataset:
    x: np.ndarray
    y: np.ndarray
    stress: np.ndarray

def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def _make_dataset(seed: int, n: int, split_offset: int) -> Dataset:
    rng = np.random.default_rng(seed + split_offset)
    y = rng.choice(len(LABELS), size=n, p=CLASS_PRIOR)
    shared_noise = rng.normal(0.0, 0.075, size=(n, 1))
    independent_noise = rng.normal(0.0, 0.145, size=(n, len(FEATURES)))
    x = np.clip(CLASS_MEANS[y] + shared_noise + independent_noise, 0.0, 1.0)
    stress = np.full(n, 'ordinary', dtype='U32')
    order = rng.permutation(n)
    cursor = 0

    def choose(count: int, allowed: Iterable[int]) -> np.ndarray:
        nonlocal cursor
        allowed_set = set(allowed)
        found: list[int] = []
        while cursor < n and len(found) < count:
            idx = int(order[cursor])
            cursor += 1
            if int(y[idx]) in allowed_set and stress[idx] == 'ordinary':
                found.append(idx)
        return np.asarray(found, dtype=int)
    count = max(1, n // 32)
    idx = choose(count, [1, 2, 3, 4])
    stress[idx] = 'pseudo_precision'
    x[idx, F['numeric_specificity']] = np.maximum(x[idx, F['numeric_specificity']], 0.96)
    x[idx, F['source_authority']] = np.maximum(x[idx, F['source_authority']], 0.63)
    idx = choose(count, [1, 3, 4])
    stress[idx] = 'decoy'
    x[idx, F['source_authority']] = np.maximum(x[idx, F['source_authority']], 0.8)
    x[idx, F['numeric_specificity']] = np.maximum(x[idx, F['numeric_specificity']], 0.88)
    x[idx, F['metadata_integrity']] = np.maximum(x[idx, F['metadata_integrity']], 0.8)
    x[idx, F['direct_observation']] = np.minimum(x[idx, F['direct_observation']], 0.22)
    x[idx, F['independent_corroboration']] = np.minimum(x[idx, F['independent_corroboration']], 0.18)
    idx = choose(count, [1, 3, 4])
    stress[idx] = 'ambiguous'
    x[idx, F['ambiguity_score']] = np.maximum(x[idx, F['ambiguity_score']], 0.88)
    x[idx, F['provenance_completeness']] = np.minimum(x[idx, F['provenance_completeness']], 0.56)
    idx = choose(count, [4])
    stress[idx] = 'blocked'
    x[idx, F['hazard_score']] = np.maximum(x[idx, F['hazard_score']], 0.94)
    x[idx, F['authority_consent']] = np.minimum(x[idx, F['authority_consent']], 0.06)
    idx = choose(count, [4])
    stress[idx] = 'contradiction'
    x[idx, F['contradiction_score']] = np.maximum(x[idx, F['contradiction_score']], 0.95)
    x[idx, F['source_authority']] = np.maximum(x[idx, F['source_authority']], 0.68)
    x[idx, F['direct_observation']] = np.maximum(x[idx, F['direct_observation']], 0.48)
    idx = choose(count, [2])
    stress[idx] = 'unlabeled_simulation'
    x[idx, F['explicit_simulation_label']] = np.minimum(x[idx, F['explicit_simulation_label']], 0.34)
    x[idx, F['narrative_symbolism']] = np.maximum(x[idx, F['narrative_symbolism']], 0.48)
    x[idx, F['reproducibility']] = np.maximum(x[idx, F['reproducibility']], 0.76)
    x[idx, F['provenance_completeness']] = np.maximum(x[idx, F['provenance_completeness']], 0.82)
    idx = choose(count, [0])
    stress[idx] = 'sparse_valid'
    x[idx, F['direct_observation']] = np.minimum(x[idx, F['direct_observation']], 0.67)
    x[idx, F['independent_corroboration']] = np.minimum(x[idx, F['independent_corroboration']], 0.53)
    x[idx, F['provenance_completeness']] = np.minimum(x[idx, F['provenance_completeness']], 0.76)
    idx = choose(count, [4])
    stress[idx] = 'tampered'
    x[idx, F['tamper_score']] = np.maximum(x[idx, F['tamper_score']], 0.96)
    x[idx, F['metadata_integrity']] = np.minimum(x[idx, F['metadata_integrity']], 0.2)
    return Dataset(x=x.astype(np.float64), y=y.astype(np.int64), stress=stress)

def _baseline_probabilities(x: np.ndarray) -> np.ndarray:
    evidence = np.mean(x[:, [F['source_authority'], F['direct_observation'], F['reproducibility'], F['independent_corroboration'], F['provenance_completeness'], F['metadata_integrity']]], axis=1)
    logits = np.column_stack([3.6 * evidence + 1.15 * x[:, F['numeric_specificity']] - 0.8 * x[:, F['contradiction_score']], 1.7 + 1.2 * x[:, F['provenance_completeness']] + 0.9 * x[:, F['ambiguity_score']], 0.7 + 3.4 * x[:, F['explicit_simulation_label']], 0.6 + 3.3 * x[:, F['narrative_symbolism']], 0.7 + 1.7 * x[:, F['contradiction_score']] + 1.5 * x[:, F['hazard_score']] + 1.5 * x[:, F['tamper_score']] + 0.8 * x[:, F['unsupported_existence_claim']]])
    return _softmax(logits)

def _temperature_scale(probabilities: np.ndarray, temperature: float) -> np.ndarray:
    logits = np.log(np.clip(probabilities, 1e-12, 1.0)) / temperature
    return _softmax(logits)

def _fit_temperature(probabilities: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    candidates = np.geomspace(0.4, 3.0, 181)
    best_temperature = 1.0
    best_nll = math.inf
    for temperature in candidates:
        scaled = _temperature_scale(probabilities, float(temperature))
        nll = float(-np.mean(np.log(np.clip(scaled[np.arange(len(y)), y], 1e-12, 1.0))))
        if nll < best_nll:
            best_nll = nll
            best_temperature = float(temperature)
    return (best_temperature, best_nll)

def _evidence_score(x: np.ndarray) -> np.ndarray:
    return np.mean(x[:, [F['direct_observation'], F['reproducibility'], F['independent_corroboration'], F['provenance_completeness'], F['metadata_integrity']]], axis=1)

def _apply_logic_gates(probabilities: np.ndarray, x: np.ndarray, minimum_confidence: float, accept_evidence_gate: float) -> np.ndarray:
    predictions = np.argmax(probabilities, axis=1).astype(np.int64)
    confidence = np.max(probabilities, axis=1)
    evidence = _evidence_score(x)
    accept = LABEL_INDEX['ACCEPT']
    qualify = LABEL_INDEX['QUALIFY']
    simulated = LABEL_INDEX['SIMULATED']
    narrative = LABEL_INDEX['NARRATIVE']
    quarantine = LABEL_INDEX['QUARANTINE']
    contradiction_block = (x[:, F['contradiction_score']] >= 0.9) | (x[:, F['contradiction_score']] >= 0.66) & (x[:, F['independent_corroboration']] < 0.6)
    tamper_block = x[:, F['tamper_score']] >= 0.72
    hazardous_without_consent = (x[:, F['hazard_score']] >= 0.72) & (x[:, F['authority_consent']] < 0.48)
    unsupported_existence = (x[:, F['unsupported_existence_claim']] >= 0.68) & (x[:, F['direct_observation']] < 0.45)
    predictions[contradiction_block | tamper_block | hazardous_without_consent | unsupported_existence] = quarantine
    not_quarantined = predictions != quarantine
    explicit_sim = (x[:, F['explicit_simulation_label']] >= 0.62) & (x[:, F['direct_observation']] < 0.78) & (x[:, F['narrative_symbolism']] < 0.72) & not_quarantined
    predictions[explicit_sim] = simulated
    explicit_narrative = (x[:, F['narrative_symbolism']] >= 0.66) & (x[:, F['direct_observation']] < 0.72) & (predictions != quarantine) & ~explicit_sim
    predictions[explicit_narrative] = narrative
    weak_accept = (predictions == accept) & ((evidence < accept_evidence_gate) | (x[:, F['direct_observation']] < 0.6) | (x[:, F['independent_corroboration']] < 0.42) | (x[:, F['provenance_completeness']] < 0.58))
    predictions[weak_accept] = qualify
    uncertain = (confidence < minimum_confidence) & (predictions != qualify)
    predictions[uncertain] = quarantine
    return predictions

def _select_policy(probabilities: np.ndarray, x: np.ndarray, y: np.ndarray) -> dict[str, float]:
    best: dict[str, float] | None = None
    for minimum_confidence in (0.3, 0.36, 0.42, 0.48, 0.54, 0.6):
        for accept_evidence_gate in (0.54, 0.58, 0.62, 0.66, 0.7):
            pred = _apply_logic_gates(probabilities, x, minimum_confidence, accept_evidence_gate)
            accuracy = float(accuracy_score(y, pred))
            macro_f1 = float(f1_score(y, pred, average='macro', zero_division=0))
            false_promotion = float(np.mean((y != LABEL_INDEX['ACCEPT']) & (pred == LABEL_INDEX['ACCEPT'])))
            accept_recall = float(np.mean(pred[y == LABEL_INDEX['ACCEPT']] == LABEL_INDEX['ACCEPT']))
            usable_coverage = float(np.mean(pred != LABEL_INDEX['QUARANTINE']))
            utility = accuracy + 0.25 * macro_f1 + 0.12 * accept_recall + 0.04 * usable_coverage - 5.0 * false_promotion
            candidate = {'minimum_confidence': float(minimum_confidence), 'accept_evidence_gate': float(accept_evidence_gate), 'selection_utility': float(utility), 'selection_false_factual_promotion': false_promotion}
            if best is None or candidate['selection_utility'] > best['selection_utility']:
                best = candidate
    assert best is not None
    return best

def _expected_calibration_error(probabilities: np.ndarray, y: np.ndarray, bins: int=15) -> float:
    confidence = np.max(probabilities, axis=1)
    pred = np.argmax(probabilities, axis=1)
    correct = pred == y
    result = 0.0
    edges = np.linspace(0.0, 1.0, bins + 1)
    for lower, upper in zip(edges[:-1], edges[1:]):
        mask = (confidence > lower) & (confidence <= upper)
        if np.any(mask):
            result += float(np.mean(mask)) * abs(float(np.mean(correct[mask])) - float(np.mean(confidence[mask])))
    return result

def _slice_rate(pred: np.ndarray, stress: np.ndarray, name: str, target: int) -> float | None:
    mask = stress == name
    if not np.any(mask):
        return None
    return float(np.mean(pred[mask] == target))

def _metrics(probabilities: np.ndarray, pred: np.ndarray, data: Dataset) -> dict[str, Any]:
    y = data.y
    one_hot = np.eye(len(LABELS), dtype=float)[y]
    precision, recall, f1, support = precision_recall_fscore_support(y, pred, labels=np.arange(len(LABELS)), zero_division=0)
    stress_mask = data.stress != 'ordinary'
    non_accept = y != LABEL_INDEX['ACCEPT']
    contradiction_mask = data.stress == 'contradiction'
    tamper_mask = data.stress == 'tampered'
    simulated_mask = y == LABEL_INDEX['SIMULATED']
    narrative_mask = y == LABEL_INDEX['NARRATIVE']
    quarantine_mask = y == LABEL_INDEX['QUARANTINE']
    decisive_mask = ~quarantine_mask
    q_pred = pred == LABEL_INDEX['QUARANTINE']
    quarantine_precision = float(np.mean(quarantine_mask[q_pred])) if np.any(q_pred) else 0.0
    return {'accuracy': float(accuracy_score(y, pred)), 'macro_f1': float(f1_score(y, pred, average='macro', zero_division=0)), 'multiclass_brier': float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1))), 'normalized_multiclass_brier': float(0.5 * np.mean(np.sum((probabilities - one_hot) ** 2, axis=1))), 'ece_15_bin': _expected_calibration_error(probabilities, y, bins=15), 'usable_coverage': float(np.mean(pred != LABEL_INDEX['QUARANTINE'])), 'clean_decidable_coverage': float(np.mean(pred[decisive_mask] != LABEL_INDEX['QUARANTINE'])), 'false_factual_promotion_rate': float(np.mean(non_accept & (pred == LABEL_INDEX['ACCEPT']))), 'accept_recall': float(np.mean(pred[y == LABEL_INDEX['ACCEPT']] == LABEL_INDEX['ACCEPT'])), 'simulation_exact_label_retention': float(np.mean(pred[simulated_mask] == LABEL_INDEX['SIMULATED'])), 'simulation_to_fact_violation_rate': float(np.mean(pred[simulated_mask] == LABEL_INDEX['ACCEPT'])), 'narrative_to_fact_violation_rate': float(np.mean(pred[narrative_mask] == LABEL_INDEX['ACCEPT'])), 'quarantine_recall': float(np.mean(pred[quarantine_mask] == LABEL_INDEX['QUARANTINE'])), 'quarantine_precision': quarantine_precision, 'contradiction_detection_recall': float(np.mean(pred[contradiction_mask] == LABEL_INDEX['QUARANTINE'])), 'tamper_detection_recall': float(np.mean(pred[tamper_mask] == LABEL_INDEX['QUARANTINE'])), 'ambiguous_acceptance_rate': float(np.mean(pred[data.stress == 'ambiguous'] == LABEL_INDEX['ACCEPT'])), 'decoy_acceptance_rate': float(np.mean(pred[data.stress == 'decoy'] == LABEL_INDEX['ACCEPT'])), 'blocked_acceptance_rate': float(np.mean(pred[data.stress == 'blocked'] == LABEL_INDEX['ACCEPT'])), 'stress_slice_accuracy': float(accuracy_score(y[stress_mask], pred[stress_mask])), 'per_class': {LABELS[i]: {'precision': float(precision[i]), 'recall': float(recall[i]), 'f1': float(f1[i]), 'support': int(support[i])} for i in range(len(LABELS))}, 'confusion_matrix': confusion_matrix(y, pred, labels=np.arange(len(LABELS))).astype(int).tolist()}

def _summary(values: list[float]) -> dict[str, float]:
    arr = np.asarray(values, dtype=float)
    return {'mean': float(np.mean(arr)), 'ci95_low': float(np.quantile(arr, 0.025)), 'ci95_high': float(np.quantile(arr, 0.975)), 'min': float(np.min(arr)), 'max': float(np.max(arr))}

def _aggregate(runs: list[dict[str, Any]], key: str) -> dict[str, dict[str, float]]:
    metric_names = ['accuracy', 'macro_f1', 'multiclass_brier', 'normalized_multiclass_brier', 'ece_15_bin', 'usable_coverage', 'clean_decidable_coverage', 'false_factual_promotion_rate', 'accept_recall', 'simulation_exact_label_retention', 'simulation_to_fact_violation_rate', 'narrative_to_fact_violation_rate', 'quarantine_recall', 'quarantine_precision', 'contradiction_detection_recall', 'tamper_detection_recall', 'ambiguous_acceptance_rate', 'decoy_acceptance_rate', 'blocked_acceptance_rate', 'stress_slice_accuracy']
    return {metric: _summary([float(run[key][metric]) for run in runs]) for metric in metric_names}

def _json_digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()
