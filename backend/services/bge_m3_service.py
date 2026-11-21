import logging
import threading

logger = logging.getLogger(__name__)

MODEL_NAME = "BAAI/bge-m3"

_model = None
_model_lock = threading.Lock()


def get_bge_m3_model():
    """Thread-safe lazy initialization for the BGE-M3 embedding model.
    Deferred import of FlagEmbedding prevents 18+ seconds of PyTorch/HF import lag at server boot.
    """
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                logger.info("Importing FlagEmbedding and loading BGE-M3 model weights...")
                from FlagEmbedding import BGEM3FlagModel

                try:
                    # Fast local path: bypass remote HuggingFace hub network checks
                    _model = BGEM3FlagModel(
                        MODEL_NAME,
                        use_fp16=True,
                        return_dense=True,
                        return_sparse=True,
                        return_colbert_vecs=False,
                        local_files_only=True,
                    )
                except Exception:
                    _model = BGEM3FlagModel(
                        MODEL_NAME,
                        use_fp16=True,
                        return_dense=True,
                        return_sparse=True,
                        return_colbert_vecs=False,
                    )
    return _model


def __getattr__(name: str):
    if name == "model":
        return get_bge_m3_model()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def encode_text(text: str):
    model = get_bge_m3_model()
    result = model.encode([text], batch_size=1)

    dense = result["dense_vecs"][0]
    sparse = result["lexical_weights"][0]

    return {
        "dense": dense,
        "sparse": sparse,
    }


def encode_texts(texts):
    if not texts:
        return {
            "dense": [],
            "sparse": [],
        }

    model = get_bge_m3_model()
    # Batch size 16 keeps peak activation memory well under RTX 3050 VRAM limits
    result = model.encode(texts, batch_size=16)

    dense = result["dense_vecs"]
    sparse = result["lexical_weights"]

    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass

    return {
        "dense": dense,
        "sparse": sparse,
    }
