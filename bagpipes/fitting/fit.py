from __future__ import print_function, division, absolute_import

import numpy as np
import os
import time
import warnings
import deepdish as dd

from copy import deepcopy

try:
    import pymultinest as pmn

except (ImportError, RuntimeError, SystemExit) as e:
    print("Bagpipes: PyMultiNest import failed, fitting will be unavailable.")

from .. import utils
from .. import plotting

from .fitted_model import fitted_model
from .posterior import posterior


class fit(object):
    """ Top-level class for fitting models to observational data.
    Interfaces with MultiNest to sample from the posterior distribution
    of a fitted_model object. Performs loading and saving of results.

    Parameters
    ----------

    galaxy : bagpipes.galaxy
        A galaxy object containing the photomeric and/or spectroscopic
        data you wish to fit.

    fit_instructions : dict
        A dictionary containing instructions on the kind of model which
        should be fitted to the data.

    run : string - optional
        The subfolder into which outputs will be saved, useful e.g. for
        fitting more than one model configuration to the same data.
    """

    def __init__(self, galaxy, fit_instructions, run="."):

        self.run = run
        self.galaxy = galaxy

        # A dictionary containing properties of the model to be saved.
        self.results = {"fit_instructions": deepcopy(fit_instructions)}

        # Set up the model which is to be fitted to the data.
        self.fitted_model = fitted_model(galaxy, fit_instructions)

        # Set up the directory structure for saving outputs.
        utils.make_dirs(run=run)

        # The base name for output files.
        self.fname = "pipes/posterior/" + run + "/" + self.galaxy.ID + "_"

        # If a posterior file already exists load it.
        if os.path.exists(self.fname[:-1] + ".h5"):
            self.results = dd.io.load(self.fname[:-1] + ".h5")
            print("\nExisting fit loaded from " + self.fname[:-1] + ".h5\n")
            self.posterior = posterior(self.galaxy, run=run)

    def fit(self, verbose=False, n_live=400):
        """ Fit the specified model to the input galaxy data.

        Parameters
        ----------

        verbose : bool - optional
            Set to True to get progress updates from the sampler.

        n_live : int - optional
            Number of live points: reducing speeds up the code but may
            lead to unreliable results.
        """

        if "lnz" in list(self.results):
            print("Fitting not performed as results have already been"
                  + " loaded from " + self.fname[:-1] + ".h5. To start"
                  + " over delete this file or change run.\n")
            return

        print("\nBagpipes: fitting object " + self.galaxy.ID + "\n")

        start_time = time.time()

        pmn.run(self.fitted_model.lnlike, self.fitted_model.prior.transform,
                self.fitted_model.ndim, importance_nested_sampling=False,
                verbose=verbose, sampling_efficiency="model",
                n_live_points=n_live, outputfiles_basename=self.fname)

        runtime = time.time() - start_time

        print("\nCompleted in " + str("%.1f" % runtime) + " seconds.\n")

        # Load MultiNest outputs and save basic quantities to file.
        samples2d = np.loadtxt(self.fname + "post_equal_weights.dat")[:, :-1]
        lnz_line = open(self.fname + "stats.dat").readline().split()

        self.results["samples2d"] = samples2d
        self.results["lnz"] = lnz_line[-3]
        self.results["lnz_err"] = lnz_line[-1]
        self.results["median"] = np.median(samples2d, axis=0)
        self.results["conf_int"] = np.percentile(samples2d, (16, 84), axis=0)

        # Save re-formatted outputs as HDF5 and remove MultiNest output.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            dd.io.save(self.fname[:-1] + ".h5", self.results)

        os.system("rm " + self.fname + "*")

        # Create a posterior object to hold the results of the fit.
        self.posterior = posterior(self.galaxy, run=self.run)

        self._print_results()

    def _print_results(self):
        """ Print the 16th, 50th, 84th percentiles of the posterior. """

        print("{:<25}".format("Parameter")
              + "{:>31}".format("Posterior percentiles"))

        print("{:<25}".format(""),
              "{:>10}".format("16th"),
              "{:>10}".format("50th"),
              "{:>10}".format("84th"))

        print("-"*58)

        for i in range(self.fitted_model.ndim):
            print("{:<25}".format(self.fitted_model.params[i]),
                  "{:>10.3f}".format(self.results["conf_int"][0, i]),
                  "{:>10.3f}".format(self.results["median"][i]),
                  "{:>10.3f}".format(self.results["conf_int"][1, i]))

        print("\n")

    def plot_corner(self, show=False, save=True):
        plotting.plot_corner(self, show=show, save=save)

    def plot_1d_posterior(self, show=False, save=True):
        plotting.plot_1d_posterior(self, show=show, save=save)

    def plot_sfh_posterior(self, show=False, save=True):
        plotting.plot_sfh_posterior(self, show=show, save=save)

    def plot_spectrum_posterior(self, show=False, save=True):
        plotting.plot_spectrum_posterior(self, show=show, save=save)

    def plot_polynomial(self, show=False, save=True):
        plotting.plot_polynomial(self, show=show, save=save)
