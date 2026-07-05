"""SG-supervised current surrogate (the working forward model)."""

from .iv_surrogate import (
    SymlogTransform,
    Normalizer,
    IVSurrogateConfig,
    IVSurrogate,
    make_features,
    build_sg_dataset,
    train_surrogate,
    SurrogatePrediction,
    SurrogateEnsemble,
)
from .adapters import (
    SurrogateForwardAdapter,
    SurrogateEnsembleAdapter,
    save_surrogate_ensemble,
    load_surrogate_ensemble,
    load_forward_ensemble,
)

__all__ = [
    "SymlogTransform",
    "Normalizer",
    "IVSurrogateConfig",
    "IVSurrogate",
    "make_features",
    "build_sg_dataset",
    "train_surrogate",
    "SurrogatePrediction",
    "SurrogateEnsemble",
    "SurrogateForwardAdapter",
    "SurrogateEnsembleAdapter",
    "save_surrogate_ensemble",
    "load_surrogate_ensemble",
    "load_forward_ensemble",
]
