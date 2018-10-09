# Authors: Mainak Jas <mainak.jas@telecom-paristech.fr>
#          Tom Dupre La Tour <tom.duprelatour@telecom-paristech.fr>
#          Umut Simsekli <umut.simsekli@telecom-paristech.fr>
#          Alexandre Gramfort <alexandre.gramfort@telecom-paristech.fr>

import numpy as np

from .utils import construct_X, check_random_state
from .learn_d_z import learn_d_z
from .update_d import update_d_block
from .update_w import estimate_phi_mh


def learn_d_z_weighted(X, n_atoms, n_times_atom, func_d=update_d_block,
                       reg=0.1, alpha=1.9, n_iter_global=10, init_tau=False,
                       n_iter_optim=10, n_iter_mcmc=10, n_burnin_mcmc=0,
                       random_state=None, n_jobs=1, solver_z='l-bfgs',
                       solver_d_kwargs=dict(), solver_z_kwargs=dict(),
                       ds_init=None, verbose=0, callback=None):
    """Univariate Convolutional Sparse Coding with an alpha-stable distribution

    Parameters
    ----------
    X : array, shape (n_trials, n_times)
        The data on which to perform CSC.
    n_atoms : int
        The number of atoms to learn.
    n_times_atom : int
        The support of the atom.
    func_d : callable
        The function to update the atoms.
    reg : float
        The regularization parameter
    alpha : float in [0, 2[:
        Parameter of the alpha-stable noise distribution.
    n_iter_global : int
        The number of iteration of the Expectation-Maximisation outer loop.
    init_tau : boolean
        If True, use a heuristic to initialize the weights tau.
    n_iter_optim : int
        The number of iteration of the Maximisation step (weighted CSC).
    n_iter_mcmc : int
        The number of iteration of the Expectation step (MCMC).
    n_burnin_mcmc : int
        The number of iteration unused by the MCMC algorithm.
    random_state : int | None
        The random state.
    n_jobs : int
        The number of parallel jobs.
    solver_z : str
        The solver to use for the z update. Options are
        'l-bfgs' (default) | 'ista' | 'fista'
    solver_d_kwargs : dict
        Additional keyword arguments to provide to update_d
    solver_z_kwargs : dict
        Additional keyword arguments to pass to update_z
    ds_init : array, shape (n_atoms, n_times_atom)
        The initialization for the atoms.
    verbose : int
        The verbosity level.
    callback : func
        A callback function called at the end of each loop of the
        coordinate descent.

    Returns
    -------
    d_hat : array, shape (n_atoms, n_times_atom)
        The estimated atoms.
    z_hat : array, shape (n_atoms, n_trials, n_times - n_times_atom + 1)
        The sparse activation matrix.
    tau : array, shape (n_trials, n_times)
        Weights estimated by the Expectation-Maximisation algorithm.
    """

    n_trials, n_times = X.shape

    if init_tau:
        phi = np.tile(np.std(X, axis=1)[:, None] ** 2, X.shape[1])
        tau = 1 / phi
    else:
        # assume gaussian to start with
        phi = np.full(shape=(n_trials, n_times), fill_value=2)
        tau = np.full(shape=(n_trials, n_times), fill_value=0.5)

    rng = check_random_state(random_state)
    d_hat = ds_init
    # Run the MCEM algorithm
    for ii in range(n_iter_global):

        # Optimize d and z wrt the new weights
        pobj, times, d_hat, z_hat = learn_d_z(
            X, n_atoms, n_times_atom, func_d, reg=reg, n_iter=n_iter_optim,
            random_state=rng, sample_weights=2 * tau, ds_init=d_hat,
            solver_d_kwargs=solver_d_kwargs, solver_z_kwargs=solver_z_kwargs,
            verbose=verbose, solver_z=solver_z, n_jobs=n_jobs,
            callback=callback)

        # Estimate the expectation via MCMC
        X_hat = construct_X(z_hat, d_hat)
        phi, tau, loglk_mcmc = estimate_phi_mh(
            X, X_hat, alpha, phi, n_iter_mcmc, n_burnin_mcmc, random_state=rng,
            return_loglk=True, verbose=verbose)

        if verbose > 0:
            print("Global Iter: %d\t" % ii)

    return d_hat, z_hat, tau
