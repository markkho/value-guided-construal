import random
import textwrap
import json
from types import SimpleNamespace
from functools import lru_cache
from itertools import combinations, product
import warnings
import sys
import logging
logger = logging.getLogger()
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.WARNING)

from tqdm import tqdm
import numpy as np
from scipy.stats import chi2_contingency
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
from frozendict import frozendict

from msdm.domains import GridWorld

from vgc_project import utils, gridutils
from vgc_project.modelinterface import create_modeling_interface
from vgc_project.parameter_fit import create_fit_vgc_model_to_trials, Trial
from vgc_project.soft_vgc import soft_value_guided_construal

sem = lambda c: np.std(c)/np.sqrt(np.sum(c != np.nan))

predictor_names = {
    'vgc_weight': 'Value Guided Construal',
    'log_traj_based_hitcount': "Trajectory-based Heuristic Search",
    'graph_based_hitcount': "Graph-based Heuristic Search",
    'goal_dist': "Distance to Goal",
    'start_dist': "Distance to Start",
    'nav_mindist': "Minimum Navigation Distance",
    'nav_mindist_timestep': "Timestep of Minimum Distance",
    'optpolicy_dist': "Distance from Optimal Plan",
    'walls_dist': "Distance to Center Wall",
    'center_dist': "Distance to Center",
    'bottleneck_dist': "Distance to Optimal Bottleneck",
    'sr_occ': "Successor Representation Overlap"
}
short_predictor_names = {
    'vgc_weight': 'VGC',
    'log_traj_based_hitcount': "Traj HS",
    'graph_based_hitcount': "Graph HS",
    'goal_dist': "Goal Dist",
    'start_dist': "Start Dist",
    'nav_mindist': "Nav Dist",
    'nav_mindist_timestep': "Nav Dist Step",
    'optpolicy_dist': "Opt Dist",
    'walls_dist': "Wall Dist",
    'center_dist': "Center Dist",
    'bottleneck_dist': "Bottleneck",
    'sr_occ': "SR Overlap"
}


class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

def bin_sem(v):
    return np.sqrt(np.mean(v)*(1-np.mean(v))/len(v))

def pval_to_string(p):
    if p == 0.0:
        p = f"< 1.0 \\times 10^{{{-16}}}" #smallest representable p value
    else:
        p = f"= {latex_float(p)}"
    return p

def latex_float(f):
    float_str = "{0:#.2g}".format(f)
    if "e" in float_str:
        base, exponent = float_str.split("e")
        return r"{0} \times 10^{{{1}}}".format(base, int(exponent))
    elif float_str == "0":
        return "0.0"
    else:
        return float_str
def clean_writeup(paragraphs):
    res = []
    for p in paragraphs:
        res.append(p.replace("\n", " ").replace("  ", " ").strip())
    res = "\n\n".join(res)
    return res
def format_rmod_coefficients(mod):
    return pd.DataFrame(mod['coefficients']).set_index('effect').rename(columns={"estimate": r"$\beta$", "se": "SE"})

def highlow_by_obs_analysis(exp_df, var1, var2):
    assert all([0 <= v <= 1.00001 for v in exp_df[var1]]), exp_df[var1]
    assert all([0 <= v <= 1.00001 for v in exp_df[var2]]), exp_df[var2]
    means = exp_df.groupby(['grid', 'obstacle'])[[var1, var2]].mean().reset_index()
    tab = pd.crosstab(means[var1] >= .5, means[var2] >= .5)
    chi2, pval, dof, exp = chi2_contingency(tab, correction=False)
    res = f"$\chi^2({dof}, N={len(means)})={chi2:.2f}$, $p {pval_to_string(pval)}$"
    return res

def global_lesion_analysis(
    *,
    name,
    data,
    dv,
    model_func,
    random_effects,
    predictors,
    rmods
) -> pd.DataFrame:
    """
    Starts with a global model with all predictors (FULL),
    then fits models with each predictor lesioned.

    DataFrame is returned with a `plot_results()` method.
    """
    comp = []
    for lesioned_eff in tqdm(["FULL"] + predictors):
        fixed_eff = [f for f in predictors if f != lesioned_eff]
        mod = getattr(rmods, model_func)
        formula = f"{dv} ~ {random_effects} + {'+'.join(sorted(set(fixed_eff)))}"
        model_res = mod(formula=formula, data=data)
        assert not model_res['is_singular']
        comp.append({
            **model_res,
            "lesioned_effect": lesioned_eff,
            "rand_effects": random_effects,
            "fixed_effects": fixed_eff,
            "dv": dv
        })
    comp =  pd.DataFrame(comp)
    comp['dAIC.FULL'] = comp['aic'] - comp[comp.lesioned_effect == "FULL"].iloc[0]['aic']
    def plot_results(ax=None, figsize=(6, 3), dpi=150):
        if ax is None:
            fig, ax = plt.subplots(1, 1, figsize=figsize, dpi=dpi)
        g = sns.barplot(
            data=comp,
            y="dAIC.FULL",
            x="lesioned_effect",
            orient='v',
            ax=ax,
            edgecolor='k',
            linewidth=1,
        )
        ax.set_xticklabels(ax.get_xticklabels(), rotation=40, ha='right')
        ax.set_title(name, fontsize=10)
        return ax
    from scipy import stats
    def likelihood_ratio_test(lesioned_effect, df):
        h1 = comp[comp['lesioned_effect'] == 'FULL']['loglik'].item()
        h0 = comp[comp['lesioned_effect'] == lesioned_effect]['loglik'].item()
        llr_stat = -2*(h0 - h1)
        p = 1 - stats.chi2.cdf(llr_stat, df=df)
        p = pval_to_string(p)
        return f"$\chi^2({df}) = {llr_stat:.2f}, p {p}$"
    def save_for_table(exp_name, filename):
        renamed = comp[['dAIC.FULL', 'lesioned_effect']].\
            set_index('lesioned_effect').\
            rename(columns={"dAIC.FULL": exp_name}).drop('FULL')
        renamed.to_json(filename)
        return renamed
    comp.plot_results = plot_results
    comp.likelihood_ratio_test = likelihood_ratio_test
    comp.save_for_table = save_for_table
    return comp

def pairwise_predictors_analysis(
    *,
    name,
    data,
    dv,
    model_func,
    random_effects,
    predictors,
    rmods
) -> pd.DataFrame:
    """
    Calculates models that include pairs of predictors.
    """
    comps = []
    for fixed_eff in tqdm(list(product(predictors, repeat=2))):
        unique_fixed_eff = sorted(set(fixed_eff))
        mod = getattr(rmods, model_func)
        formula = f"{dv} ~ {random_effects} + {'+'.join(sorted(set(unique_fixed_eff)))}"
        model_res = mod(formula=formula, data=data)
        assert not model_res['is_singular']
        comps.append({
            **model_res,
            'base': fixed_eff[0],
            'target': fixed_eff[1],
            "rand_effects": random_effects,
            "fixed_effects": fixed_eff,
            "dv": dv
        })
    comps = pd.DataFrame(comps)
    comps['dAIC'] = comps['aic'] - comps['aic'].min()
    def plot_results(
        ax=None,
        figsize=(8*.8, 6*.8),
        dpi=150,
        predictor_order=None,
        predictor_labels=None,
        title_fontsize=7,
        cell_fontsize=5,
        ytick_fontsize=7,
        xtick_fontsize=7,
        cbar_ticks_fontsize=6,
        cbar_label_fontsize=7
    ):
        if predictor_order is None:
            predictor_order = predictors
        comp = comps.drop_duplicates(['base', 'target'])
        table = comp.pivot(columns="target", index="base", values="dAIC").loc[predictor_order, predictor_order]
        mask = np.zeros_like(table)
        mask[np.triu_indices_from(mask)] = True
        mask[np.diag_indices_from(mask)] = False
        if ax is None:
            fig, ax = plt.subplots(1, 1, figsize=figsize, dpi=dpi)
        sns.heatmap(table, mask=mask,
                    annot=True, fmt='.0f',
                    # cbar_kws={"label": "$\Delta$AIC"},
                    annot_kws={"fontsize": cell_fontsize},
                    ax=ax).\
            set_title(name, fontsize=title_fontsize)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=40, ha='right')
        cbar = ax.collections[0].colorbar
        cbar.ax.tick_params(labelsize=cbar_ticks_fontsize)
        cbar.set_label(label="$\Delta$AIC", size=cbar_label_fontsize)

        if predictor_labels:
            get_label = lambda lab: predictor_labels.get(lab, predictor_labels.get(lab.replace("_Z", ""), lab))
            xticklabels = [get_label(t.get_text()) for t in ax.get_xticklabels()]
            yticklabels = [get_label(t.get_text()) for t in ax.get_yticklabels()]
            ax.set_xticklabels(xticklabels, fontname="Arial", fontsize=xtick_fontsize)
            ax.set_yticklabels(yticklabels, fontname="Arial", fontsize=ytick_fontsize)
            ax.set_ylabel(None)
            ax.set_xlabel(None)
        return ax
    
    def create_tex_caption(figuretype, textwidth_mult, image, caption, short_caption, name):
        return textwrap.dedent(
            """
            \\begin{{{figuretype}}}
            \\centering
            \\includegraphics[width={textwidth_mult:.2f}\\textwidth]{{{image}}}
            \\caption[{short_caption}]{{{caption}}}
            \\label{{fig:{name}}}
            \\end{{{figuretype}}}
            """
        ).format(
            figuretype=figuretype,
            textwidth_mult=textwidth_mult,
            image=image,
            caption=caption,
            short_caption=short_caption,
            name=name
        )
    comps.plot_results = plot_results
    comps.create_tex_caption = create_tex_caption
    return comps

def single_predictor_analysis(
    *,
    name,
    data,
    dv,
    model_func,
    random_effects,
    predictor,
    rmods,
    coeff_digits,
    normalized_predictor=False
) -> str:
    """
    Hierarchical GLM analysis with a predictor by itself.
    """
    assert coeff_digits > 0, "rounding to integers is weird in python"
    mod = getattr(rmods, model_func)
    model_res = mod(formula=f"{dv} ~ {random_effects} + {predictor}", data=data)
    assert not model_res['is_singular']
    mod = getattr(rmods, model_func)
    lesioned_model_res = mod(formula=f"{dv} ~ {random_effects}", data=data)
    assert not model_res['is_singular']

    from scipy import stats
    llr_stat = -2*(lesioned_model_res['loglik'] - model_res['loglik'])
    p = 1 - stats.chi2.cdf(llr_stat, df=1)
    coeff = [c for c in model_res['coefficients'] if c['effect'] == predictor][0]
    coeff_letter = r"\beta" if normalized_predictor else "b"
    summary = f"$\chi^2(1) = {llr_stat:.2f}, p  {pval_to_string(p)}$; ${coeff_letter} = {round(coeff['estimate'], ndigits=coeff_digits)}$, S.E. $= {round(coeff['se'], ndigits=coeff_digits)}$"
    return dotdict(
        log_likelihood_ratio_statistic=llr_stat,
        coefficient=coeff,
        chi_sq_p_value=p,
        summary=summary
    )

def marginalization_analysis(
    *,
    name,
    data,
    dv,
    model_func,
    random_effects,
    predictors,
    rmods
) -> pd.DataFrame:
    """
    """
    from itertools import combinations
    def subsets(S):
        S = sorted(S)
        for i in range(len(S)+1):
            for s in combinations(S, r=i):
                yield sorted(s)
    comps = []
    for fixed_eff in tqdm(list(subsets(predictors))):
        if len(fixed_eff) == 0:
            formula = f"{dv} ~ {random_effects}"
        else:
            formula = f"{dv} ~ {random_effects} + {'+'.join(fixed_eff)}"
        mod = getattr(rmods, model_func)
        model_res = mod(formula=formula, data=data)
        assert not model_res['is_singular']
        comps.append({
            **model_res,
            "rand_effects": random_effects,
            "fixed_effects": fixed_eff,
            "dv": dv
        })
    comps = pd.DataFrame(comps)
    comps['dAIC'] = comps['aic'] - comps['aic'].min()
    def marginalized_table():
        marg_table = []
        for pred in predictors:
            pred_marg = dict(
                total_with = 0,
                n_with = 0,
                total_without = 0,
                n_without = 0,
                pred = pred
            )
            for _, row in comps.iterrows():
                if pred in row['fixed_effects']:
                    pred_marg['total_with'] += np.exp(-row['dAIC']/2)
                    pred_marg['n_with'] += 1
                else:
                    pred_marg['total_without'] += np.exp(-row['dAIC']/2)
                    pred_marg['n_without'] += 1
            marg_table.append(pred_marg)
        marg_table = pd.DataFrame(marg_table)
        marg_table['mean_with'] = marg_table['total_with']/marg_table['n_with']
        marg_table['mean_without'] = marg_table['total_without']/marg_table['n_without']
        marg_table['difference'] = marg_table['mean_without'] - marg_table['mean_with']
        return marg_table
    comps.marginalized_table = marginalized_table
    return comps


def fit_vgc_model_to_experiment_data(
    exp_df,
    mazes,
    response_type,
    response_col,
    parameters_to_fit,
    fit_vgc_model_to_trials,
    seed=None
):
    assert response_type in ['real', 'binomial']
    assert response_type == 'real', "Currently not set up for fitting binomial data"

    # set up trials
    trials = [
        Trial(
            maze=mazes[r['grid']],
            obstacle=r['obstacle'].split('-')[1],
            type=response_type,
            value=r[response_col]
        )
        for _, r in exp_df.iterrows()
    ]

    # set up optimization parameters
    default_vgc_parameters = dict(
        construal_inverse_temp=10,
        construal_rand_choose=1e-5,
        policy_inverse_temp=10,
        policy_rand_choose=1e-5,
        construal_weight=1,
        obs_awareness_prior=.5,

        success_prob=1-1e-5,
        feature_rewards=(("G", 0), ),
        absorbing_features=("G",),
        wall_features="#0123456789",
        default_features=(".",),
        initial_features=("S",),
        step_cost=-1,
        discount_rate=.99
    )
    initial_fit_values = dict(
        construal_inverse_temp=10,
        construal_rand_choose=.2,
        policy_inverse_temp=10,
        policy_rand_choose=.2,
        construal_weight=1,
        obs_awareness_prior=.5,
    )

    if seed is not None:
        rng = random.Random(seed)
        for p, v in initial_fit_values.items():
            if p not in parameters_to_fit:
                continue
            if p in [
                'construal_rand_choose',
                'policy_rand_choose',
                'obs_awareness_prior'
            ]:
                initial_fit_values[p] = rng.random()
            elif p in [
                'construal_inverse_temp',
                'policy_inverse_temp',
                'construal_weight',
            ]:
                initial_fit_values[p] = rng.random()*rng.choice([1, 10])
            else:
                raise

    # do the optimization
    minimize_method = "Nelder-Mead"
    fit_res = fit_vgc_model_to_trials(
        trials=tuple(trials),
        default_vgc_parameters=frozendict(**{
            **default_vgc_parameters,
            **{p: initial_fit_values[p] for p in parameters_to_fit}
        }),
        parameters_to_fit=tuple(parameters_to_fit),
        minimize_kwargs=frozendict(
            method=minimize_method,
            options=frozendict(
                maxiter=1000,
            ),
        ),
    )

    # return the fit results and also a convenience function
    # that takes in a dataframe row
    fit_vgc_params = {
        **default_vgc_parameters,
        **fit_res['fitted_parameters']
    }
    def calc_vgc_fitted_weight(row):
        return soft_value_guided_construal(
            tile_array=mazes[row['grid']],
            **fit_vgc_params
        ).obstacle_probs[row['obstacle'].split('-')[1]]

    # for summarizing fitting results - this is only for real data
    result_df = exp_df.copy()
    result_df[f'vgc_{response_col}_fitted_prob'] = result_df.apply(calc_vgc_fitted_weight, axis=1)
    result_df[f'logodd_vgc_{response_col}_fitted_prob'] = \
        result_df[f'vgc_{response_col}_fitted_prob'].\
        apply(lambda w: np.log(w/(1 - w)))
    total_ss = sum((result_df[response_col] - result_df[response_col].mean())**2)
    r2 = 1 - fit_res['score']/total_ss
    mse = fit_res['score']/len(result_df)
    manual_score = sum((result_df[response_col] - result_df[f'logodd_vgc_{response_col}_fitted_prob'])**2)
    assert np.isclose(manual_score, fit_res['score'], atol=1.e-8)
    summary_str = "\n".join([
        f"R^2 = {r2:.2f}",
        f"MSE ({response_col} - logodd_vgc_prob)^2/n = {mse:.2f}",
        f"Est. Params: {', '.join([f'{p}={v:.2g}' for p, v in fit_res['fitted_parameters'].items()])}",
        f"VGC models evaluated by {minimize_method}: {fit_res['minimize_result']['nfev']}"
    ])
    summary = SimpleNamespace(
        r2=r2,
        mse=mse,
    )

    def plot(y=None, logodd_vgc=True, ax=None, fontsize=7):
        if ax is None:
            fig, ax = plt.subplots(1, 1, figsize=(2, 2), dpi=150)
        if y is None:
            y = response_col
        if logodd_vgc:
            x = f'logodd_vgc_{response_col}_fitted_prob'
        else:
            x = f'vgc_{response_col}_fitted_prob'
        ax.plot(
            result_df[x], result_df[y],
            linestyle='',
            marker="o",
            markerfacecolor="red",
            markersize=3,
            markeredgewidth=.2,
            markeredgecolor="purple",
            alpha=.5
        )
        ax.set_xlabel(x, fontsize=fontsize)
        ax.set_ylabel(y, fontsize=fontsize)
        return ax

    def vgc_maze_models():
        maze_models = {}
        for maze_name, maze in mazes.items():
            maze_models[maze_name] = soft_value_guided_construal(
                tile_array=maze,
                **fit_vgc_params
            )
        return maze_models

    return SimpleNamespace(
        fit_result=fit_res,
        fit_vgc_params=fit_vgc_params,
        calc_vgc_fitted_weight=calc_vgc_fitted_weight,
        result_df=result_df,
        summary_str=summary_str,
        summary=summary,
        plot=plot,
        vgc_maze_models=vgc_maze_models
    )

# def quantile_predictor_analysis(
#     data,
#     dv,
#     quantile_preds,
#     title,
#     xlabel,
#     ylabel,
#     ylim,
#     xlim,
#     predictor_labels ,
#     quantiles,
#     invert_pred=None,
#     legend=True
# ):
#     # Calculate quantile bins for each predictor
#     mean_preds = data[['grid', 'obstacle', dv] + quantile_preds].groupby(['grid', 'obstacle']).mean().reset_index()
#     if invert_pred is not None:
#         for pred in quantile_preds:
#             if invert_pred(pred):
#                 mean_preds[pred] = -mean_preds[pred]
#     for pred in quantile_preds:
#         mean_preds[pred+'_quantile'] = pd.qcut(mean_preds[pred], q=quantiles, labels=False, duplicates='drop')

#     # Plot actual and predicted mean for each predictor, grouped by quantile
#     fig, ax = plt.subplots(1, 1, figsize=(6.5, 5), dpi=100)
#     plt.ylim(*ylim)
#     plt.xlim(*xlim)
#     plt.title(title)
#     plt.xlabel(xlabel)
#     plt.ylabel(ylabel)
#     legend_artists = []
#     for pred in quantile_preds:
#         pred_quart_means = mean_preds.groupby(pred+'_quantile')[[dv, pred]].mean()
#         pred_quart_sem = mean_preds.groupby(pred+'_quantile')[[dv, pred]].sem()
#         lines = ax.errorbar(
#             x=pred_quart_means[pred],
#             y=pred_quart_means[dv],
#             xerr=pred_quart_sem[pred],
#             yerr=pred_quart_sem[dv],
#             capsize=5 if 'vgc' in pred else 3,
#             color='k' if 'vgc' in pred else None,
#             linewidth=4 if 'vgc' in pred else 1,
#             elinewidth=3 if 'vgc' in pred else 1,
#             capthick=3 if 'vgc' in pred else 1,
#             linestyle='-' if 'vgc' in pred else '-',
#             zorder=-10 if 'vgc' in pred else None
#         )
#         legend_artists.append(lines[0])

#     if legend:
#         _ = ax.legend(
#             legend_artists,
#             [predictor_labels.get(p.replace('_Z', ''), p) for p in quantile_preds],
#             bbox_to_anchor=(1, 0, 0, 1),
#             loc="upper left", 
#             # mode="expand",
#             ncol=1
#         )
#     plt.tight_layout()
#     return fig

def quantile_predictor_row_figure(
    data,
    dv,
    quantile_preds,
    ylabel,
    predictor_labels,
    quantiles,
    invert_pred=None,
    legend=True,
    fig_width_mm=182,
    fig_height_mm=30,
    spinewidth=.4,
    yticks=None
):
    mm_to_inch = 1/25.4 
    figsize = (fig_width_mm*mm_to_inch, fig_height_mm*mm_to_inch)
    assert fig_width_mm <= 182
    assert fig_height_mm <= 245

    # Calculate quantile bins for each predictor
    mean_preds = data[['grid', 'obstacle', dv] + [p for p in quantile_preds if p is not None]].groupby(['grid', 'obstacle']).mean().reset_index()
    for pred in quantile_preds:
        if pred is None:
            continue
        mean_preds[pred+'_quantile'] = pd.qcut(mean_preds[pred], q=quantiles, labels=False, duplicates='drop')

    # Plot actual and predicted mean for each predictor, grouped by quantile
    fig, axes = plt.subplots(1, len(quantile_preds), figsize=figsize, dpi=300)
    axes = axes.flatten()
    legend_artists = []
    for ax_i, pred in enumerate(quantile_preds):
        ax = axes[ax_i]
        for spine in ['top','bottom','left','right']:
            ax.spines[spine].set_linewidth(spinewidth)
        if pred is None:
            ax.set_xticks([])
            ax.set_xlabel(None)
        else:
            pred_quart_means = mean_preds.groupby(pred+'_quantile')[[dv, pred]].mean()
            pred_quart_sem = mean_preds.groupby(pred+'_quantile')[[dv, pred]].sem()
            ax.plot(
                data[pred], data[dv],
                'ko',
                zorder=-4,
                markersize=1,
                markerfacecolor='k',
                alpha=.01,
                markeredgewidth=0
            )
            lines = ax.errorbar(
                x=pred_quart_means[pred],
                y=pred_quart_means[dv],
                xerr=pred_quart_sem[pred],
                yerr=pred_quart_sem[dv],
                capsize=1,
                color='red',
                linewidth=.5,
                elinewidth=.5,
                capthick=.5,
                linestyle='-',
            )
            ax.tick_params(axis = 'both', which = 'major', labelsize = 5, width=.4, length=2, pad=1)
            ax_title = ax.set_title(predictor_labels.get(pred.replace("_Z", ""), pred), pad=2, font="Arial")
            ax_title.set_fontsize(6)
            if invert_pred(pred):
                cur_xlim = ax.get_xlim()
                ax.set_xlim(cur_xlim[1], cur_xlim[0])
            for ax_ticklabel in ax.get_xticklabels():
                ax_ticklabel.set_fontproperties("Arial")
                ax_ticklabel.set_fontsize(5)
        if ax_i != 0:
            ax.set_yticks([])
            ax.set_ylabel(None)
        else:
            if yticks is not None:
                ax.set_yticks(yticks)
            ax_ylabel = ax.set_ylabel(ylabel, font="Arial")
            ax_ylabel.set_fontsize(6)
            for ax_ticklabel in ax.get_yticklabels():
                ax_ticklabel.set_fontproperties("Arial")
                ax_ticklabel.set_fontsize(5)
                
    fig.tight_layout(w_pad=.1)
    return fig