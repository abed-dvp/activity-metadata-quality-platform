from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class BinaryMetrics:
    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int
    precision: float
    recall: float
    f1: float

    def to_dict(self) -> dict:
        return asdict(self)


def _safe_divide(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def binary_metrics(y_true: list[int], y_pred: list[int]) -> BinaryMetrics:
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")

    tp = sum(t == 1 and p == 1 for t, p in zip(y_true, y_pred))
    fp = sum(t == 0 and p == 1 for t, p in zip(y_true, y_pred))
    fn = sum(t == 1 and p == 0 for t, p in zip(y_true, y_pred))
    tn = sum(t == 0 and p == 0 for t, p in zip(y_true, y_pred))

    precision = _safe_divide(tp, tp + fp)
    recall = _safe_divide(tp, tp + fn)
    f1 = _safe_divide(2 * precision * recall, precision + recall)

    return BinaryMetrics(tp, fp, fn, tn, precision, recall, f1)
