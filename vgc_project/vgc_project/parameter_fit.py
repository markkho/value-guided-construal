import random
import numpy as np
from types import SimpleNamespace
from collections import namedtuple
from itertools import product
from typing import Sequence

from scipy.optimize import minimize

from vgc_project.soft_vgc import soft_value_guided_construal

Trial = namedtuple("Trial", "maze obstacle type value")
Bound = namedtuple("Bound", "min max")

default_parameter_bounds = dict(
    construal_inverse_temp=Bound(0, None),
    construal_rand_choose=Bound(0, 1),
    policy_inverse_temp=Bound(0, None),
    policy_rand_choose=Bound(0, 1),
    construal_weight=Bound(0, None),
    step_cost=Bound(None, 0),
    discount_rate=Bound(0, 1 - 1e-8),
    obs_awareness_prior=Bound(0., 1.),
)

def make_minimize_kwargs(
    *,
    trials : Sequence[Trial],
    default_vgc_parameters : dict,
    parameters_to_fit: list,
    parameter_bounds : dict=None,
):
    if parameter_bounds is None:
        parameter_bounds = default_parameter_bounds
    def fun(x):
        x_params = dict(zip(parameters_to_fit, x))
        
        # penalize for being outside of bounds
        for k, v in x_params.items():
            if parameter_bounds[k].min is not None and v < parameter_bounds[k].min:
                return np.inf
            if parameter_bounds[k].max is not None and v > parameter_bounds[k].max:
                return np.inf
            
        nll = 0
        for t in trials:
            model = soft_value_guided_construal(
                tile_array=t.maze,
                **{
                    **default_vgc_parameters,
                    **x_params
                }
            )
            if t.type == 'real':
                nll += model.nll_logodds(t.obstacle, t.value)
            elif t.type == 'binomial':
                nll += model.nll_binomial(t.obstacle, *t.value)
            else:
                raise
        return nll
    x0 = [default_vgc_parameters[p] for p in parameters_to_fit]
    bounds = [tuple(parameter_bounds[k]) for k in parameters_to_fit]
    return {
        'fun': fun,
        'x0': x0,
        'bounds': bounds
    }

def synthetic_trials(
    *,
    vgc_parameters,
    mazes,
    n_trials,
    response_type,
    binomial_total,
    rng
):
    trials = []
    for maze_name, maze in mazes.items():
        model = soft_value_guided_construal(
            tile_array=maze,
            **vgc_parameters
        )
        for t in range(n_trials):
            for obstacle, prob in model.obstacle_probs.items():
                if response_type == 'real':
                    trials.append(Trial(
                        maze=maze,
                        obstacle=obstacle,
                        type='real',
                        value=np.log(prob/(1-prob)) + rng.normalvariate(0, .05)
                    ))
                elif response_type == 'binomial':
                    count = sum([rng.random() < prob for _ in range(binomial_total)])
                    trials.append(Trial(
                        maze=maze,
                        obstacle=obstacle,
                        type='binomial',
                        value=(count, binomial_total)
                    ))
                else:
                    raise
    return trials

import joblib
import functools

def create_recover_parameters(joblib_cache_location=None, lru_cache_maxsize=int(1e7)):
    def recover_parameters(
        *,
        mazes : dict,
        vgc_parameters : dict,
        parameters_to_fit_initial_values : dict,
        seed : int,
        synthetic_trials_kwargs=None,
        minimize_kwargs=None,
    ):
        rng = random.Random(seed)
        if synthetic_trials_kwargs is None:
            synthetic_trials_kwargs = dict(
                n_trials=1,
                response_type='real',
                binomial_total=1
            )
        trials = synthetic_trials(
            vgc_parameters=vgc_parameters,
            mazes=mazes,
            **synthetic_trials_kwargs,
            rng = rng
        )
            
        if minimize_kwargs is None:
            minimize_kwargs = dict(
                method="Nelder-Mead",
                options=dict(
                    maxiter=1000,
                ),
            )
            assert 'fun' not in minimize_kwargs
            assert 'x0' not in minimize_kwargs
            assert 'bounds' not in minimize_kwargs
        parameters_to_fit = tuple(sorted(parameters_to_fit_initial_values.keys()))
        main_minimize_kwargs = make_minimize_kwargs(
            trials=trials,
            default_vgc_parameters={
                **vgc_parameters,
                **parameters_to_fit_initial_values
            },
            parameters_to_fit=parameters_to_fit,
            parameter_bounds=None,
        )
        minimize_result = minimize(
            **main_minimize_kwargs,
            **minimize_kwargs,
        )
        
        return dict(
            fitted_parameters=dict(zip(parameters_to_fit, minimize_result.x)),
            score=minimize_result.fun,
            minimize_result=minimize_result
        )
    
    if joblib_cache_location:
        joblibmemory = joblib.Memory(joblib_cache_location, verbose=0)
        joblib_func = joblibmemory.cache()(recover_parameters)
        recover_parameters = functools.wraps(recover_parameters)(joblib_func)
        recover_parameters = functools.lru_cache(maxsize=lru_cache_maxsize)(recover_parameters)
        return recover_parameters
    return recover_parameters

def create_fit_vgc_model_to_trials(joblib_cache_location=None, lru_cache_maxsize=int(1e7)):
    def fit_vgc_model_to_trials(
        *,
        trials : Sequence[Trial],
        default_vgc_parameters : dict,
        parameters_to_fit : Sequence,
        minimize_kwargs : dict =None,
    ):
        if minimize_kwargs is None:
            minimize_kwargs = dict(
                method="Nelder-Mead",
                options=dict(
                    maxiter=1000,
                ),
            )
            assert 'fun' not in minimize_kwargs
            assert 'x0' not in minimize_kwargs
            assert 'bounds' not in minimize_kwargs
        main_minimize_kwargs = make_minimize_kwargs(
            trials=trials,
            default_vgc_parameters=default_vgc_parameters,
            parameters_to_fit=parameters_to_fit,
            parameter_bounds=None,
        )

        if len(parameters_to_fit) == 0:
            fit_result = dict(
                fitted_parameters=dict(),
                score=main_minimize_kwargs['fun']([]),
                minimize_result=None
            )
        else:
            minimize_result = minimize(
                **main_minimize_kwargs,
                **minimize_kwargs,
            )
            fit_result = dict(
                fitted_parameters=dict(zip(parameters_to_fit, minimize_result.x)),
                score=minimize_result.fun,
                minimize_result=minimize_result
            )
        return fit_result
    if joblib_cache_location:
        joblibmemory = joblib.Memory(joblib_cache_location, verbose=0)
        joblib_func = joblibmemory.cache()(fit_vgc_model_to_trials)
        fit_vgc_model_to_trials = functools.wraps(fit_vgc_model_to_trials)(joblib_func)
        fit_vgc_model_to_trials = functools.lru_cache(maxsize=lru_cache_maxsize)(fit_vgc_model_to_trials)
    return fit_vgc_model_to_trials
