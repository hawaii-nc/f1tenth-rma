"""
Linear probes: how much grip information does a representation carry?

Used for H1 ("ẑ decodes grip with R² ≥ 0.7"), E3 (decoded-grip trajectory
after a step change) and E5 (where along encoder → history → φ the grip
signal is lost). Plain-numpy ridge regression with k-fold cross-validated
R², so no scikit-learn dependency.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class LinearProbe:
    weights: np.ndarray
    bias: float
    mean: np.ndarray
    std: np.ndarray

    def predict(self, X: np.ndarray) -> np.ndarray:
        Xs = (np.asarray(X, dtype=np.float64) - self.mean) / self.std
        return Xs @ self.weights + self.bias


def fit_ridge(X: np.ndarray, y: np.ndarray, alpha: float = 1e-3) -> LinearProbe:
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    mean = X.mean(axis=0)
    std = X.std(axis=0) + 1e-8
    Xs = (X - mean) / std
    y_mean = y.mean()
    A = Xs.T @ Xs + alpha * len(Xs) * np.eye(Xs.shape[1])
    w = np.linalg.solve(A, Xs.T @ (y - y_mean))
    return LinearProbe(weights=w, bias=float(y_mean), mean=mean, std=std)


def r2_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=np.float64)
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    return float(1.0 - ss_res / ss_tot) if ss_tot > 0 else float('nan')


def cv_r2(X: np.ndarray, y: np.ndarray, k: int = 5, alpha: float = 1e-3,
          groups: Optional[np.ndarray] = None, seed: int = 0) -> float:
    """
    k-fold cross-validated R². Pass `groups` (e.g. episode ids) so samples
    from one episode never sit on both sides of a split: otherwise the
    probe can memorise episodes and R² is inflated.
    """
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    rng = np.random.default_rng(seed)
    if groups is None:
        groups = np.arange(len(y))
    uniq = rng.permutation(np.unique(groups))
    folds = np.array_split(uniq, k)
    preds = np.empty_like(y)
    for f in folds:
        test = np.isin(groups, f)
        probe = fit_ridge(X[~test], y[~test], alpha)
        preds[test] = probe.predict(X[test])
    return r2_score(y, preds)
