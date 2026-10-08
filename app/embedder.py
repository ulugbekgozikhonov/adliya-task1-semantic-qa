"""bge-m3 orqali matnni vektorga aylantirish.

Model og'ir (~2.2 GB), shuning uchun bir marta yuklanadi va qayta ishlatiladi.
Matn har doim avval normalize() dan o'tadi: indekslashda ham, qidirishda ham.
"""

from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.text import normalize


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer(
        settings.embed_model, device="cpu", local_files_only=settings.hf_offline
    )


def dimension() -> int:
    return get_model().get_embedding_dimension()


def embed(texts: list[str], batch_size: int = 32, show_progress: bool = False) -> np.ndarray:
    return get_model().encode(
        [normalize(t) for t in texts],
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=show_progress,
    )


def embed_one(text: str) -> np.ndarray:
    return embed([text])[0]
