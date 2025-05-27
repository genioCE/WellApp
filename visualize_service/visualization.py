import os
import uuid
from typing import List, Tuple
import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import plotly.express as px
import asyncio

async def generate_visualization(embedding: List[float], method: str = "pca", dimensions: int = 2) -> Tuple[str, str]:
    if dimensions not in (2, 3):
        raise ValueError("dimensions must be 2 or 3")
    if method not in ("pca", "tsne"):
        raise ValueError("method must be 'pca' or 'tsne'")

    async def _create_plot() -> str:
        X = np.array(embedding).reshape(1, -1)
        if method == "tsne":
            reducer = TSNE(n_components=dimensions)
        else:
            reducer = PCA(n_components=dimensions)
        reduced = reducer.fit_transform(X)
        if dimensions == 3:
            fig = px.scatter_3d(x=reduced[:,0], y=reduced[:,1], z=reduced[:,2])
        else:
            fig = px.scatter(x=reduced[:,0], y=reduced[:,1])
        os.makedirs("visualizations", exist_ok=True)
        file_id = f"{uuid.uuid4()}.html"
        path = os.path.join("visualizations", file_id)
        fig.write_html(path)
        return path

    path = await asyncio.to_thread(_create_plot)
    return path, f"{method.upper()}_{dimensions}D"
