import functools
import joblib
import hashlib
import pandas as pd
import numpy as np
import logging
from types import SimpleNamespace

class ImmutableDataFrame(pd.DataFrame):
    """A wrapper around pandas dataframe to prevent changes and allow hashing"""
    def __init__(self, df):
        super(ImmutableDataFrame, self).__init__(df.copy())
        res = hashlib.sha256(pd.util.hash_pandas_object(self, index=True).values)
        _hashvalue = int.from_bytes(res.digest(), 'big')
        super(ImmutableDataFrame, self).__setattr__("_hashvalue", _hashvalue)
    def __hash__(self):
        return self._hashvalue
    def __eq__(self, other):
        return hash(self) == hash(other)
    def __ne__(self, other):
        return not (self == other)
    def _immutable(self, name, val):
        raise TypeError("ImmutableDataFrame is immutable")
    __setitem__ = _immutable
    __setattr__ = _immutable
    __delitem__ = _immutable
        
def create_R_model_interface(
    *, 
    use_cache=True,
    always_load_data=False,
    joblib_cache_location=None
):
    joblibmemory = joblib.Memory(joblib_cache_location, verbose=0)
    
    from rpy2 import robjects as ro
    from rpy2.robjects import numpy2ri, pandas2ri
    template_converter = ro.conversion.converter
    template_converter += numpy2ri.converter
    template_converter += pandas2ri.converter
    converter = ro.conversion.Converter('my converter', template=template_converter)
    Rcontext = ro.conversion.localconverter(converter)
    R = ro.r
    for lib in ["lme4"]:
        R.library(lib)
    
    def simple_cache(func):
        cache = {}
        @functools.wraps(func)
        def wrapped(*args, **kw):
            kw_key = tuple((k, kw[k]) for k in sorted(kw.keys()))
            key = (args, kw_key)
            if key in cache:
                return cache[key]
            else:
                cache[key] = func(*args, **kw)
                return cache[key]
        wrapped._cache = cache
        return wrapped
        
    def lm(*, formula, data, **kw):
        with Rcontext:
            data_id = f"data_{id(data)}_{hash(data)}"
            if always_load_data or not R(f"exists('{data_id}')")[0]:
                R.assign(f"{data_id}", data)
            R(f"mod <- lm({formula}, data={data_id}, {','.join([k + '=' + v for k, v in kw.items()])})")
            coefficients = R("data.frame(summary(mod)$coefficients)")
            is_singular = bool(R("NA %in% coef(mod)")[0])
            coefficients['effect'] = coefficients.index
            coefficients = coefficients.reset_index().\
                rename(columns={"Estimate": "estimate", 'Std..Error': "se"})[["effect", "estimate", "se"]].to_dict('records')
            res = dict(
                formula=formula,
                coefficients = coefficients,
                is_singular = is_singular,
                loglik = R("logLik(mod)")[0],
                aic = R("AIC(mod)")[0],
                residuals = R("resid(mod)"),
                predictions = R("predict(mod)"),
                data_id=data_id,
                **kw
            )
        return res
    
    def glm(*, formula, data, family="binomial", **kw):
        kw['family'] = family
        with Rcontext:
            data_id = f"data_{id(data)}_{hash(data)}"
            if always_load_data or not R(f"exists('{data_id}')")[0]:
                R.assign(f"{data_id}", data)
            R(f"mod <- glm({formula}, data={data_id}, {','.join([k + '=' + v for k, v in kw.items()])})")
            coefficients = R("data.frame(summary(mod)$coefficients)")
            is_singular = bool(R("NA %in% coef(mod)")[0])
            coefficients['effect'] = coefficients.index
            coefficients = coefficients.reset_index().\
                rename(columns={"Estimate": "estimate", 'Std..Error': "se"})[["effect", "estimate", "se"]].to_dict('records')
            res = dict(
                formula=formula,
                coefficients = coefficients,
                is_singular = is_singular,
                loglik = R("logLik(mod)")[0],
                aic = R("AIC(mod)")[0],
                residuals = R("resid(mod)"),
                predictions = R("predict(mod)"),
                data_id=data_id,
                **kw
            )
        return res
        
    def lmer(*, 
             formula,
             data,
             REML="F",
             is_singular_tol=1e-4,
             control='lmerControl(optimizer="bobyqa",optCtrl=list(maxfun=1e+07))',
             **kw
        ):
        kw["REML"] = REML
        kw['control'] = control
        with Rcontext:
            data_id = f"data_{id(data)}_{hash(data)}"
            if always_load_data or not R(f"exists('{data_id}')")[0]:
                R.assign(f"{data_id}", data)
            model_call = f"lmer({formula}, data={data_id}, {','.join([k + '=' + v for k, v in kw.items()])})"
            R(f"mod <- {model_call}")
            coefficients = R("data.frame(summary(mod)$coefficients)")
            is_singular = bool(R(f"isSingular(mod, tol={is_singular_tol:g})")[0])
            coefficients['effect'] = coefficients.index
            coefficients = coefficients.reset_index().\
                rename(columns={"Estimate": "estimate", 'Std..Error': "se"})[["effect", "estimate", "se"]].to_dict('records')
            res = dict(
                formula=formula,
                coefficients = coefficients,
                is_singular = is_singular,
                loglik = R("logLik(mod)")[0],
                aic = R("AIC(mod)")[0],
                residuals = R("resid(mod)"),
                predictions = R("predict(mod)"),
                **kw,
                call=model_call,
                data_id=data_id,
                data_hash=hash(data),
            )
        return res
    
    def glmer(*, 
              formula,
              data,
              family="binomial", 
              is_singular_tol=1e-4,
              control='glmerControl(optimizer="bobyqa",optCtrl=list(maxfun=1e+07))',
              **kw
        ):
        kw["family"] = family
        kw['control'] = control
        with Rcontext:
            data_id = f"data_{id(data)}_{hash(data)}"
            if always_load_data or not R(f"exists('{data_id}')")[0]:
                R.assign(f"{data_id}", data)
            model_call = f"glmer({formula}, data={data_id}, {','.join([k + '=' + v for k, v in kw.items()])})"
            R(f"mod <- {model_call}")
            coefficients = R("data.frame(summary(mod)$coefficients)")
            is_singular = bool(R(f"isSingular(mod, tol={is_singular_tol:g})")[0])
            coefficients['effect'] = coefficients.index
            coefficients = coefficients.reset_index().\
                rename(columns={"Estimate": "estimate", 'Std..Error': "se"})[["effect", "estimate", "se"]].to_dict('records')
            res = dict(
                formula=formula,
                coefficients = coefficients,
                is_singular = is_singular,
                loglik = R("logLik(mod)")[0],
                aic = R("AIC(mod)")[0],
                residuals = R("resid(mod)"),
                predictions = R("predict(mod)"),
                **kw,
                call=model_call,
                data_id=data_id,
                data_hash=hash(data),
            )
        return res
    
    rmods = SimpleNamespace()
    for mod in [lm, glm, lmer, glmer]:
        if use_cache:
            joblib_func = joblibmemory.cache()(mod)
            mod = functools.wraps(mod)(joblib_func)
            mod = simple_cache(mod)
        setattr(rmods, mod.__name__, mod)
    return rmods