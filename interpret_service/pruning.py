from typing import List, Tuple, Optional
import numpy as np
from loguru import logger
from sklearn.decomposition import PCA

MAX_RECURSION_DEPTH = 10

def recursive_prune(values: List[float], threshold: float, depth: int = 0) -> List[float]:
    if depth >= MAX_RECURSION_DEPTH:
        logger.warning("Maximum recursion depth reached during pruning")
        return values

    filtered = [v for v in values if abs(v) >= threshold]
    if len(filtered) == len(values):
        return filtered
    return recursive_prune(filtered, threshold, depth + 1)

def prune_embedding(values: List[float], threshold: float, reduce_dim: Optional[int] = None) -> Tuple[List[float], dict]:
    original_len = len(values)
    pruned = recursive_prune(values, threshold)

    details = {
        "original_size": original_len,
        "pruned_size": len(pruned),
        "percentage_reduced": round(100 * (1 - len(pruned) / original_len), 2)
    }

    if reduce_dim and reduce_dim < len(pruned):
        try:
            pca = PCA(n_components=reduce_dim)
            pca_result = pca.fit_transform(np.array(pruned).reshape(1, -1))
            pruned = pca_result.flatten().tolist()
            details["reduced_size"] = len(pruned)
        except Exception as e:
            logger.error(f"PCA reduction failed: {e}")
            details["pca_error"] = str(e)

    logger.info("Pruning completed", details=details)

    return pruned, details
