"""Module to assess patterns in missing data, numerically or graphically"""

import numpy as np
import pandas as pd
from .checks import check_dimensions
from .helpers import _pattern_output, _is_null

@check_dimensions
def md_pairs(data, cols=None):
    """
    Calculates pairwise missing data statistics
    - rr: response-response pairs
    - rm: response-missing pairs
    - mr: missing-response pairs
    - mm: missing-missing pairs
    Returns a square matrix, where n = number of columns
    """
    int_ln = lambda arr: np.logical_not(arr)*1
    r = int_ln(_is_null(data))
    rr = np.matmul(r.T, r)
    mm = np.matmul(int_ln(r).T, int_ln(r))
    mr = np.matmul(int_ln(r).T, r)
    rm = np.matmul(r.T, int_ln(r))
    pairs = dict(rr=rr, rm=rm, mr=mr, mm=mm)
    pairs = {k: _pattern_output(v, cols, True)
             for k, v in pairs.items()}
    return pairs

@check_dimensions
def md_pattern(data, cols):
    """
    Calculates row-wise missing data statistics, where
    - 0 is missing, 1 is not missing
    - num rows is num different row patterns
    - 'nmis' is number of missing values in a row pattern
    - 'count' is number of total rows with row pattern
    """
    r = _is_null(data)
    nmis = np.sum(r, axis=0)
    r = r[:, np.argsort(nmis)]
    num_string = lambda row: "".join(str(e) for e in row)
    pat = np.apply_along_axis(num_string, 1, r*1)
    sort_r = r[np.argsort(pat), :]*1
    sort_r_df = _pattern_output(sort_r, cols, False)
    sort_r_df = sort_r_df.groupby(cols).size().reset_index()
    sort_r_df.columns = cols + ["count"]
    sort_r_df["nmis"] = sort_r_df[cols].sum(axis=1)
    sort_r_df[cols] = sort_r_df[cols].apply(np.logical_not)*1
    return sort_r_df[["count"] + cols + ["nmis"]]

def _inbound(pairs):
    """Helper to get inbound from pairs"""
    return pairs["mr"]/(pairs["mr"]+pairs["mm"])

def _outbound(pairs):
    """Helper to get outbound from pairs"""
    return pairs["rm"]/(pairs["rm"]+pairs["rr"])

def _influx(pairs):
    """Helper to get influx from pairs"""
    num = np.nansum(pairs["mr"], axis=1)
    denom = np.nansum(pairs["mr"]+pairs["rr"], axis=1)
    return num/denom

def _outflux(pairs):
    """Helper to get outflux from pairs"""
    num = np.nansum(pairs["rm"], axis=1)
    denom = np.nansum(pairs["rm"]+pairs["mm"], axis=1)
    return num/denom

def get_stat_for(func, data):
    """
    Generic method to get a missing data statistic from data
    Can be used directly in tandem with helper methods, but this is discouraged
    Instead, use specific methods below (inbound, outbound, etc)
    These methods utilize this function to compute specific stats
    """
    pairs = md_pairs(data)
    with np.errstate(divide="ignore", invalid="ignore"):
        stat = func(pairs)
    return stat

def inbound(data, cols=None):
    """
    Calculates proportion of usable cases (Ijk)
    - Ijk = 1 if variable Yk observed in all records where Yj missing
    - Used to quickly select potential predictors Yk for imputing Yj
    - High values are preferred
    """
    inbound_coeff = get_stat_for(_inbound, data)
    inbound_ = _pattern_output(inbound_coeff, cols, True)
    return inbound_

def outbound(data, cols=None):
    """
    Calculates the outbound statistic (Ojk)
    - Ojk measures how observed data Yj connect to rest of missing data
    - Ojk = 1 if Yj observed in all records where Yk is missing
    - Used to evaluate whether Yj is a potential predictor for imputing Yk
    - High values are preferred
    """
    outbound_coeff = get_stat_for(_outbound, data)
    outbound_ = _pattern_output(outbound_coeff, cols, True)
    return outbound_

def influx(data, cols=None):
    """
    Calculates the influx coefficient (Ij)
    - Ij = # pairs (Yj,Yk) w/ Yj missing & Yk observed / # observed data cells
    - Value depends on the proportion of missing data of the variable
    - Influx of a completely observed variable is equal to 0
    - Influx for completely missing variables is equal to 1
    - For two variables with the same proportion of missing data:
        - Var with higher influx is better connected to the observed data
        - Var with higher influx might thus be easier to impute
    """
    influx_coeff = get_stat_for(_influx, data)
    influx_coeff = influx_coeff.reshape(1, data.shape[1])
    influx_ = _pattern_output(influx_coeff, cols, False)
    return influx_

def outflux(data, cols=None):
    """
    Calculates the outflux coefficient (Oj)
    - Oj = # pairs w/ Yj observed and Yk missing / # incomplete data cells
    - Value depends on the proportion of missing data of the variable
    - Outflux of a completely observed variable is equal to 1
    - Outflux of a completely missing variable is equal to 0.
    - For two variables having the same proportion of missing data:
        - Var with higher outflux is better connected to the missing data
        - Var with higher outflux more useful for imputing other variables
    """
    outflux_coeff = get_stat_for(_outflux, data)
    outflux_coeff = outflux_coeff.reshape(1, data.shape[1])
    outflux_ = _pattern_output(outflux_coeff, cols, False)
    return outflux_

def flux(data, cols):
    """
    Port of Van Buuren's flux method in R. Calculates:
    - pobs: Proportion observed
    - ainb: Average inbound statistic
    - aout: Average outbound statistic
    - influx: Influx coefficient (Ij)
    - outflux: Outflux coefficient (Oj)
    """
    row_mean = lambda row: np.nansum(row)/(len(row) - 1)
    pairs = md_pairs(data)
    with np.errstate(divide="ignore", invalid="ignore"):
        pobs = np.mean(np.logical_not(_is_null(data)), axis=0)
        ainb = np.apply_along_axis(row_mean, 1, _inbound(pairs))
        aout = np.apply_along_axis(row_mean, 1, _outbound(pairs))
        inf = _influx(pairs)
        outf = _outflux(pairs)
        res = dict(pobs=pobs, influx=inf, outflux=outf, ainb=ainb, aout=aout)
    return pd.DataFrame(res, index=cols)
