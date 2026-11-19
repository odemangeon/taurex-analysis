from dataclasses import dataclass, field
import numpy as np

@dataclass
class SamplingResult:
    samples: np.ndarray
    weights: np.ndarray
    logl: np.ndarray
    names: list[str]
    log_evidence: float
    log_evidence_error: float
    diagnostics: dict = field(default_factory=dict)

    def validate(self):
        self.samples = np.asarray(self.samples)
        self.weights = np.asarray(self.weights, dtype=float)
        self.logl = np.asarray(self.logl)
        if (self.weights.ndim != 1 or self.samples.shape != (len(self.weights), len(self.names))
                or self.logl.shape != self.weights.shape
                or not np.isfinite(self.samples).all()
                or not np.isfinite(self.weights).all() or np.any(self.weights < 0)
                or self.weights.sum() <= 0 or np.isnan(self.logl).any()
                or np.isposinf(self.logl).any()
                or not np.isfinite([self.log_evidence, self.log_evidence_error]).all()
                or self.log_evidence_error < 0):
            raise ValueError('Invalid sampling result')
        self.weights /= self.weights.sum()
        return self
