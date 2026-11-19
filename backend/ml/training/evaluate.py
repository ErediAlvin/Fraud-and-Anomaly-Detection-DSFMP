"""Offline metrics; undefined values remain null rather than fabricated zeros."""
import argparse
import json
from pathlib import Path
import numpy as np
from sklearn.metrics import confusion_matrix, roc_auc_score, average_precision_score


def metrics(labels, scores, threshold):
    y = np.asarray(labels)
    s = np.asarray(scores, dtype=float)
    if not len(y) or not np.isfinite(s).all() or not set(y).issubset({0, 1}):
        raise ValueError('Finite scores and nonempty binary labels required')
    if len(y) != len(s) or not 0 <= threshold <= 1:
        raise ValueError('Invalid lengths or threshold')
    tn, fp, fn, tp = map(int, confusion_matrix(y, s >= threshold, labels=[0, 1]).ravel())
    divide = lambda a, b: a / b if b else None
    return dict(count=len(y), prevalence=float(y.mean()), threshold=threshold,
                precision=divide(tp, tp+fp), recall=divide(tp, tp+fn),
                f1=divide(2*tp, 2*tp+fp+fn), false_positive_rate=divide(fp, fp+tn),
                roc_auc=float(roc_auc_score(y, s)) if len(set(y)) == 2 else None,
                average_precision=float(average_precision_score(y, s)) if y.sum() else None,
                alert_rate=float((s >= threshold).mean()),
                confusion_matrix=dict(tn=tn, fp=fp, fn=fn, tp=tp),
                undefined_policy='null indicates insufficient denominator/classes')


def main():
    parser = argparse.ArgumentParser(description='Evaluate exported scores without retraining or deserializing models')
    parser.add_argument('--scores', required=True, help='CSV containing is_fraud and anomaly_score')
    parser.add_argument('--threshold', required=True, type=float)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    import pandas as pd
    frame = pd.read_csv(args.scores)
    Path(args.output).write_text(json.dumps(metrics(frame.is_fraud, frame.anomaly_score, args.threshold), indent=2, allow_nan=False))

if __name__ == '__main__':
    main()
