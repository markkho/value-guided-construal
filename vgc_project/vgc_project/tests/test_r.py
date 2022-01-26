import pandas as pd
import numpy as np
from vgc_project.r import create_R_model_interface, ImmutableDataFrame

def test_r_model_interface():
    np.random.seed(1028)
    ndata = 10000
    nrand = 4
    intercept = 1
    slope = 5

    mydata = pd.DataFrame({'x': 2*(.5 - np.random.random(ndata))})
    mydata['x2'] = mydata['x']
    mydata['y'] = intercept + slope*mydata['x'] + np.random.logistic(size=ndata)*.1
    mydata['s'] = np.random.randint(0, nrand, size=ndata)
    mydata['s_x'] = mydata['s'] - mydata['s'].max()/2
    mydata['y_s'] = mydata['y'] + mydata['s_x'] + np.random.logistic(size=ndata)*.1
    mydata['p'] = 1/(1 + np.exp(-mydata['y']))
    mydata['d'] = np.random.binomial(n=1, p=mydata['p'])
    mydata['p_s'] = 1/(1 + np.exp(-mydata['y_s']))
    mydata['d_s'] = np.random.binomial(n=1, p=mydata['p_s'])
    idf = ImmutableDataFrame(mydata)
    
    rmods = create_R_model_interface(joblib_cache_location=None)
    lm_res = rmods.lm(
        formula="y ~ x", data=idf
    )
    assert abs(lm_res['coefficients'][0]['estimate'] - intercept) < .1
    assert abs(lm_res['coefficients'][1]['estimate'] - slope) < .1

    glm_res = rmods.glm(
        formula="d ~ x", data=idf
    )
    assert abs(glm_res['coefficients'][0]['estimate'] - intercept) < .1
    assert abs(glm_res['coefficients'][1]['estimate'] - slope) < .1
    lmer_res = rmods.lmer(
        formula="y_s ~ (1 | s) + x", data=idf, 
        control='lmerControl(optimizer="bobyqa",optCtrl=list(maxfun=1e+07))'
    )
    assert abs(lmer_res['coefficients'][0]['estimate'] - intercept) < .1
    assert abs(lmer_res['coefficients'][1]['estimate'] - slope) < .1
    glmer_res = rmods.glmer(
        formula="d_s ~ (1 | s) + x", 
        data=idf, 
        control='glmerControl(optimizer="bobyqa",optCtrl=list(maxfun=1e+07))'
    )
    assert not glmer_res['is_singular']
    assert abs(glmer_res['coefficients'][0]['estimate'] - intercept) < .1
    assert abs(glmer_res['coefficients'][1]['estimate'] - slope) < .1
    glmer_sing_res = rmods.glmer(
        formula="d ~ (1 | s) + x", #random effect provides no info, so this should be singular
        data=idf, 
        control='glmerControl(optimizer="bobyqa",optCtrl=list(maxfun=1e+07))'
    )
    assert glmer_sing_res['is_singular']