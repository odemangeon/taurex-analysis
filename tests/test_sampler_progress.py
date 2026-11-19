import numpy as np
from taurex_analysis.retrieval.samplers.nestle import run


def test_progress_is_visible_and_can_be_disabled(capsys):
    class Problem:
        names=['x']
        def prior_transform(self,u):return 4*u-2
        def log_likelihood(self,x):return -float(np.sum(x*x))
    settings={'nlive':20,'tol':.5}
    visible=run(Problem(),settings,42)
    output=capsys.readouterr().out
    assert 'initializing live points' in output
    assert 'it=' in output and 'logz=' in output
    assert 'Nestle completed' in output
    quiet=run(Problem(),dict(settings,progress=False),42)
    assert capsys.readouterr().out==''
    np.testing.assert_array_equal(visible.samples,quiet.samples)
    np.testing.assert_array_equal(visible.weights,quiet.weights)
