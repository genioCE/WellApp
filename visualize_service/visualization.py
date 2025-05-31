import os
import uuid
from typing import List, Tuple
import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import plotly.express as px
from loguru import logger
import asyncio
import traceback

<<<<<<< HEAD
VIS_DIR = "visualizations"
os.makedirs(VIS_DIR, exist_ok=True)

def dimensionality_reduction(embedding_array, method, dimensions):
    if method.lower() == "pca":
        reducer = PCA(n_components=dimensions)
    elif method.lower() == "tsne":
        reducer = TSNE(n_components=dimensions, perplexity=30)
    else:
        raise ValueError(f"Unsupported visualization method: {method}")

    reduced_embedding = reducer.fit_transform(embedding_array)
    return reduced_embedding

def create_plot(reduced_embedding, method, dimensions):
    if dimensions == 3:
        fig = px.scatter_3d(
            x=reduced_embedding[:, 0],
            y=reduced_embedding[:, 1],
            z=reduced_embedding[:, 2],
            title=f"{method.upper()} 3D Visualization"
        )
    elif dimensions == 2:
        fig = px.scatter(
            x=reduced_embedding[:, 0],
            y=reduced_embedding[:, 1],
            title=f"{method.upper()} 2D Visualization"
        )
    else:
        raise ValueError("Visualization only supports 2D or 3D dimensions")

    file_id = f"{uuid.uuid4()}.html"
    path = os.path.join(VIS_DIR, file_id)
    fig.write_html(path)
    return path

async def generate_visualization(
    embedding: List[float], method: str = "pca", dimensions: int = 2
) -> Tuple[str, str]:
    try:
        embedding_array = np.array(embedding).reshape(1, -1)

        # PCA/TSNE require at least 2 samples. Handle single embedding gracefully.
        if embedding_array.shape[0] < 2:
            # Duplicate embedding with small noise to allow PCA/TSNE
            noise = np.random.normal(0, 1e-4, embedding_array.shape)
            embedding_array = np.vstack([embedding_array, embedding_array + noise])

        reduced_embedding = await asyncio.to_thread(
            dimensionality_reduction, embedding_array, method, dimensions
        )

        path = await asyncio.to_thread(
            create_plot, reduced_embedding, method, dimensions
        )

        vis_type = f"{method.upper()} {dimensions}D Scatter Plot"
        logger.info(
            "Visualization created successfully",
            method=method, dimensions=dimensions, path=path
        )

        return path, vis_type

    except Exception as e:
        detailed_traceback = traceback.format_exc()
        logger.error(f"Visualization Exception: {str(e)}")
        logger.error(f"Traceback: {detailed_traceback}")
        raise
=======
async def generate_visualization(embedding: List[float], method: str = "pca", dimensions: int = 2):
    def _create_plot():
        import plotly.graph_objects as go

        X = np.array(embedding).flatten()
        fig = go.Figure([go.Bar(y=X)])
        os.makedirs("visualizations", exist_ok=True)
        file_id = f"{uuid.uuid4()}.html"
        path = os.path.join("visualizations", file_id)
        fig.write_html(path)
        return path

    path = await asyncio.to_thread(_create_plot)
    return path, "Bar Plot - Single Embedding"

>>>>>>> ceb7c6450b733fa1b750d1d5ec6570ee242452ab
