import os
import uuid
from typing import List, Tuple
import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import plotly.express as px
import asyncio

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

