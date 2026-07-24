"""Text -> embedding vector, via a small open-source model that runs on
CPU. Loading the model is the slow part (a few seconds, once per
process) — encoding individual pieces of text after that is fast, which
is why this wraps a single loaded model instance rather than reloading
per call.

all-MiniLM-L6-v2 produces 384-dimensional vectors. That number matters
downstream: every embedding we store must have come from the same
model, since vectors from two different models aren't comparable to
each other at all — cosine similarity between them would be meaningless
noise, not a real signal. If we ever upgrade the model, every stored
embedding needs re-computing, not just new ones going forward.
"""

from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"


class Embedder:
    def __init__(self) -> None:
        self._model = SentenceTransformer(MODEL_NAME)

    def embed(self, text: str) -> list[float]:
        # normalize_embeddings scales every vector to unit length. Once
        # vectors are unit length, cosine similarity (the angle between
        # two vectors) reduces to a plain dot product — cheaper to
        # compute, and it's what storage.py's search assumes.
        vector = self._model.encode(text, normalize_embeddings=True)
        return vector.tolist()
