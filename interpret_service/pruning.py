from typing import List, Tuple
import numpy as np


def recursive_prune(values: List[float], threshold: float) -> List[float]:
    filtered = [v for v in values if abs(v) >= threshold]
    if len(filtered) == len(values):
        return filtered
    return recursive_prune(filtered, threshold)


def prune_embedding(values: List[float], threshold: float, reduce_dim: int | None = None) -> Tuple[List[float], dict]:
    original_len = len(values)
    pruned = recursive_prune(values, threshold)
    details = {
        "original_size": original_len,
        "pruned_size": len(pruned),
    }

    if reduce_dim and reduce_dim < len(pruned):
        from sklearn.decomposition import PCA
        pca = PCA(n_components=reduce_dim)
        pca_result = pca.fit_transform(np.array(pruned).reshape(1, -1))
        pruned = pca_result.flatten().tolist()
        details["reduced_size"] = len(pruned)

    details["percentage_reduced"] = 100 * (1 - len(pruned) / original_len)
    return pruned, details
