import pandas as pd

def calculate_confusion_metrics(tp, fp, tn, fn):
    tp, fp, tn, fn = int(tp), int(fp), int(tn), int(fn)
    total = tp + fp + tn + fn
    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0
    accuracy = (tp + tn) / total if total else 0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) else 0
    fpr = fp / (fp + tn) if (fp + tn) else 0
    fnr = fn / (fn + tp) if (fn + tp) else 0
    return {
        "Precision": precision,
        "Recall": recall,
        "Accuracy": accuracy,
        "F1 Score": f1,
        "False Positive Rate": fpr,
        "False Negative Rate": fnr,
    }

def metrics_to_dataframe(metrics):
    return pd.DataFrame([
        {"Metric": k, "Score": round(v, 4), "Percent": round(v * 100, 2)}
        for k, v in metrics.items()
    ])

def build_equivalence_partition_table(min_value, max_value):
    min_value, max_value = float(min_value), float(max_value)
    return pd.DataFrame([
        {"Partition": "Invalid - Below Minimum", "Input Range": f"x < {min_value}", "Representative Value": min_value - 1, "Expected Result": "Reject / Error"},
        {"Partition": "Valid Range", "Input Range": f"{min_value} <= x <= {max_value}", "Representative Value": (min_value + max_value) / 2, "Expected Result": "Accept"},
        {"Partition": "Invalid - Above Maximum", "Input Range": f"x > {max_value}", "Representative Value": max_value + 1, "Expected Result": "Reject / Error"},
    ])

def build_boundary_value_table(min_value, max_value):
    min_value, max_value = float(min_value), float(max_value)
    values = [min_value - 1, min_value, min_value + 1, max_value - 1, max_value, max_value + 1]
    positions = ["Min - 1", "Min", "Min + 1", "Max - 1", "Max", "Max + 1"]
    rows = []
    for pos, v in zip(positions, values):
        rows.append({
            "Position": pos,
            "Boundary Value": v,
            "Expected Result": "Valid" if min_value <= v <= max_value else "Invalid",
        })
    return pd.DataFrame(rows)