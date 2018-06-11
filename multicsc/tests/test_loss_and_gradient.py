import pytest
import numpy as np
from scipy import optimize


from multicsc.utils import construct_X_multi
from multicsc.utils.whitening import whitening
from multicsc.loss_and_gradient import compute_X_and_objective_multi
from multicsc.loss_and_gradient import gradient_d
from multicsc.loss_and_gradient import gradient_zi

from multicsc.tests.helper_functions import gradient_checker

from multicsc.utils import get_D


def _gradient_zi(X, Z, D, loss, loss_params, flatten=False):
    return gradient_zi(X[0], Z[0], D, loss=loss, flatten=flatten,
                       loss_params=loss_params)


def _construct_X(X, Z, D, loss, loss_params):
    return construct_X_multi(Z, D, n_channels=X.shape[1])


def _objective(X, Z, D, loss, loss_params):
    return compute_X_and_objective_multi(X, Z, D, feasible_evaluation=False,
                                         loss=loss,
                                         loss_params=loss_params)


def _gradient_d(X, Z, D, loss, loss_params, flatten=False):
    return gradient_d(D, X, Z, loss=loss, flatten=flatten,
                      loss_params=loss_params)


@pytest.mark.parametrize('loss', ['l2', 'dtw', 'whitening'])
@pytest.mark.parametrize('func', [
    _construct_X, _gradient_zi, _objective, _gradient_d])
def test_consistency(loss, func):
    """Check that the result are the same for the full rank D and rank 1 uv.
    """
    n_trials, n_channels, n_times = 5, 3, 100
    n_atoms, n_times_atom = 10, 15

    loss_params = dict(gamma=.01)

    n_times_valid = n_times - n_times_atom + 1

    X = np.random.randn(n_trials, n_channels, n_times)
    Z = np.random.randn(n_trials, n_atoms, n_times_valid)

    uv = np.random.randn(n_atoms, n_channels + n_times_atom)
    D = get_D(uv, n_channels)

    if loss == "whitening":
        loss_params['ar_model'], X = whitening(X)

    val_D = func(X, Z, D, loss, loss_params=loss_params)
    val_uv = func(X, Z, uv, loss, loss_params=loss_params)
    assert np.allclose(val_D, val_uv)


@pytest.mark.parametrize('loss', ['l2', 'dtw', 'whitening'])
def test_gradients(loss):
    """Check that the gradients have the correct shape.
    """
    n_trials, n_channels, n_times = 5, 3, 100
    n_atoms, n_times_atom = 10, 15

    n_checks = 5
    if loss == "dtw":
        n_checks = 1

    loss_params = dict(gamma=.01)

    n_times_valid = n_times - n_times_atom + 1

    X = np.random.randn(n_trials, n_channels, n_times)
    Z = np.random.randn(n_trials, n_atoms, n_times_valid)

    uv = np.random.randn(n_atoms, n_channels + n_times_atom)
    D = get_D(uv, n_channels)
    if loss == "whitening":
        loss_params['ar_model'], X = whitening(X)

    # Test gradient D
    assert D.shape == _gradient_d(X, Z, D, loss, loss_params=loss_params).shape

    def pobj(ds):
        return _objective(X, Z, ds.reshape(n_atoms, n_channels, -1), loss,
                          loss_params=loss_params)

    def grad(ds):
        return _gradient_d(X, Z, ds, loss=loss, flatten=True,
                           loss_params=loss_params)

    gradient_checker(pobj, grad, np.prod(D.shape), n_checks=n_checks,
                     grad_name="gradient D for loss '{}'".format(loss),
                     rtol=1e-4)

    # Test gradient Z
    assert Z[0].shape == _gradient_zi(
        X, Z, D, loss, loss_params=loss_params).shape

    def pobj(zs):
        return _objective(X[:1], zs.reshape(1, n_atoms, -1), D, loss,
                          loss_params=loss_params)

    def grad(zs):
        return gradient_zi(X[0], zs, D, loss=loss, flatten=True,
                           loss_params=loss_params)

    gradient_checker(pobj, grad, n_atoms * n_times_valid, n_checks=n_checks,
                     debug=True, grad_name="gradient Z for loss '{}'"
                     .format(loss), rtol=1e-4)
