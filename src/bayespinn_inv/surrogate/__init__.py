"""SG-supervised current surrogate (the working forward model)."""

from .adapters import (
    SurrogateEnsembleAdapter,
    SurrogateForwardAdapter,
    load_forward_ensemble,
    load_surrogate_ensemble,
    save_surrogate_ensemble,
)
from .iv_surrogate import (
    IVSurrogate,
    IVSurrogateConfig,
    Normalizer,
    SurrogateEnsemble,
    SurrogatePrediction,
    SymlogTransform,
    build_sg_dataset,
    make_features,
    train_surrogate,
)

__all__ = [
    "IVSurrogate",
    "IVSurrogateConfig",
    "Normalizer",
    "SurrogateEnsemble",
    "SurrogateEnsembleAdapter",
    "SurrogateForwardAdapter",
    "SurrogatePrediction",
    "SymlogTransform",
    "build_sg_dataset",
    "load_forward_ensemble",
    "load_surrogate_ensemble",
    "make_features",
    "save_surrogate_ensemble",
    "train_surrogate",
]
