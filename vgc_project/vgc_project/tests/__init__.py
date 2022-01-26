import functools
import joblib
import pandas as pd
import numpy as np
location = './_cache'
joblibmemory = joblib.Memory(location, verbose=0)

class ImmutableDataFrame(pd.DataFrame):
    """A wrapper around pandas dataframe to prevent changes and allow hashing"""
    equivalence_ids = {}
    def __hash__(self):
        try:
            return self._hashvalue
        except AttributeError:
            res = hashlib.sha256(pd.util.hash_pandas_object(self, index=True).values)
            self._hashvalue = int.from_bytes(res.digest(), 'big')
            return self._hashvalue
    def __eq__(self, other):
        if (id(self) in ImmutableDataFrame.equivalence_ids) and \
           (id(other) in ImmutableDataFrame.equivalence_ids) and \
           (ImmutableDataFrame.equivalence_ids[id(self)] == ImmutableDataFrame.equivalence_ids[id(other)]):
            return True
        eq = \
            (self.values == other.values).all().all() and \
            (self.index == other.index).all() and \
            (self.columns == other.columns).all()
        if eq:
            if id(self) not in ImmutableDataFrame.equivalence_ids:
                ImmutableDataFrame.equivalence_ids[id(self)] = id(self)
            ImmutableDataFrame.equivalence_ids[id(other)] = ImmutableDataFrame.equivalence_ids[id(self)]
        return eq
    def __setitem__(self, name, val):
        raise TypeError("ImmutableDataFrame is immutable")
        
def simple_cache(ignore=()):
    def wrapper(func):
        cache = {}
        @functools.wraps(func)
        def cached_function(*args, **kw):
            kw_key = tuple((k, kw[k]) for k in sorted(kw.keys()) if k not in ignore)
            key = (args, kw_key)
            try:
                return cache[key]
            except KeyError:
                cache[key] = func(*args, **kw)
                return cache[key]
        return cached_function
    return wrapper


@simple_cache(ignore=["R"])
@joblibmemory.cache(ignore=["R"])
def run_R_model(*, model_string: str, data: ImmutableDataFrame, R=None):
    """
    Pass an R model statement with `data=data`. This function
    checks a cache in memory, then checks a cache on disk. If it needs
    to compute a new result, it sees if the data has already been loaded
    into R, otherwise it loads it as a new variable.
    
    ```
    import pandas as pd
    from rpy2 import robjects as ro
    from rpy2.robjects.conversion import localconverter
    Rcontext = localconverter(ro.default_converter + ro.numpy2ri.converter + ro.pandas2ri.converter)

    mydata = pd.DataFrame({'x': np.random.random(100)})
    mydata['y'] = 2*mydata['x'] + np.random.normal(100)*.5
    mydata = ImmutableDataFrame(mydata)
    with Rcontext:
        print("first model")
        res = run_R_model(model_string="lm(y ~ x, data=data, REML=F)", data=mydata, R=ro.r)
        print("second model")
        res = run_R_model(model_string="lm(y ~ x*x, data=data, REML=F)", data=mydata, R=ro.r)
        print("done")
    ```
    """
    data_id = f"data_{id(data)}_{hash(data)}"
    if not R(f"exists('{data_id}')")[0]:
        print(f"Data variable does not exist; assigning to R variable {data_id}")
        R.assign(f"{data_id}", data)
    R(f"data <- {data_id}")
    R(f"mod <- {model_string}")
    coefficients = R("data.frame(summary(mod)$coefficients)")
    coefficients['effect'] = coefficients.index
    coefficients = coefficients.reset_index().\
        rename(columns={"Estimate": "estimate", 'Std..Error': "se"})[["effect", "estimate", "se"]].to_dict('records')
    return dict(
        model_string=model_string,
        data_id=data_id,
        coefficients = coefficients,
        loglik = R("logLik(mod)")[0],
        anova = R("anova(mod)").reset_index().to_dict('records'),
        aic = R("AIC(mod)")[0],
        residuals = R("resid(mod)"),
        predictions = R("predict(mod)"),
    )