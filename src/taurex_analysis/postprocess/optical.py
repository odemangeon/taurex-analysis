import json
import csv
import math
from statistics import NormalDist
import numpy as np
BANDS=("CHEOPS","TESS")

def number(value, name, positive=False):
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f'{name}: supply a numeric value') from None
    if not math.isfinite(result) or (positive and result <= 0):
        raise ValueError(f'{name}: expected a finite {"positive " if positive else ""}value')
    return result

def read_constraints(path):
    with path.open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError('Optical constraints file is empty')
    output = []
    for row in rows:
        band, kind = row['band'], row['kind']
        if band not in BANDS or kind not in ('measurement', 'interval', 'upper_limit', 'hpd_upper_endpoint'):
            raise ValueError(f'Unknown band/kind: {band}/{kind}')
        value = number(row['depth_ppm'], f'{band} {kind} depth_ppm')
        if kind == 'measurement':
            sigma = number(row['sigma_ppm'], f'{band} sigma_ppm', positive=True)
            for n in (1, 2, 3):
                output.append(dict(band=band, kind=kind, depth=value, sigma=sigma,
                                   level=n, probability=2*NormalDist().cdf(n)-1,
                                   label=f'{n}σ central', reference=row['reference']))
        elif kind == 'interval':
            probability = number(row['probability'], f'{band} probability')
            if not 0 < probability < 1:
                raise ValueError('Interval probability must lie strictly between 0 and 1')
            lower = value + number(row['delta_lower_ppm'], f'{band} delta_lower_ppm')
            upper = value + number(row['delta_upper_ppm'], f'{band} delta_upper_ppm')
            if not lower <= value <= upper or lower == upper:
                raise ValueError('Interval offsets must bracket the best value')
            output.append(dict(band=band, kind=kind, depth=value, lower=lower, upper=upper,
                               probability=probability, label=row['label'],
                               reference=row['reference'], interval_type=row.get('interval_type', 'unspecified'),
                               best_value_definition=row.get('best_value_definition', 'unspecified')))
        else:
            probability = number(row['probability'], f'{band} probability')
            if not 0 < probability < 1:
                raise ValueError('Upper-limit probability must lie strictly between 0 and 1')
            output.append(dict(band=band, kind=kind, depth=value, sigma=0,
                               level=None, probability=probability,
                               label=row['label'] or f'{100*probability:.3f}%', reference=row['reference'],
                               interval_type='HPD' if kind == 'hpd_upper_endpoint' else 'one-sided'))
    for band in BANDS:
        original = [r for r in rows if r['band'] == band]
        if not original:
            raise ValueError(f'Missing constraints for {band}')
        kinds = {r['kind'] for r in original}
        if len(kinds) != 1 or (kinds == {'measurement'} and len(original) != 1):
            raise ValueError(f'{band}: provide one measurement OR upper limits of the same observation')
        intervals = sorted((r for r in output if r['band'] == band and r['kind'] == 'interval'),
                           key=lambda r: r['probability'])
        if len({r['probability'] for r in intervals}) != len(intervals):
            raise ValueError(f'{band}: duplicate interval probabilities')
        if len({r['depth'] for r in intervals}) > 1:
            raise ValueError(f'{band}: intervals must describe the same best value')
        if any(a['lower'] < b['lower'] or a['upper'] > b['upper'] for a, b in zip(intervals, intervals[1:])):
            raise ValueError(f'{band}: intervals must be nested with increasing probability')
        limits = sorted((r for r in output if r['band'] == band and r['kind'] in ('upper_limit', 'hpd_upper_endpoint')),
                        key=lambda r: r['probability'])
        if len({r['probability'] for r in limits}) != len(limits):
            raise ValueError(f'{band}: duplicate upper-limit probabilities')
        if any(a['depth'] > b['depth'] for a, b in zip(limits, limits[1:])):
            raise ValueError(f'{band}: upper limits must increase with probability')
    return output

def convert(depth, thermal, rp_over_a):
    """Full-phase, circular-orbit conversion; depths in ppm."""
    return (np.asarray(depth) - np.asarray(thermal)) * 1e-6 / rp_over_a**2

def constraint_result(obs, thermal, rp_over_a):
    low, median, high = thermal[:3]
    result = dict(band=obs['band'], kind=obs['kind'], label=obs['label'],
                  probability=obs['probability'], reference=obs['reference'],
                  interval_type=obs.get('interval_type', 'Gaussian central' if obs['kind'] == 'measurement' else 'one-sided'),
                  best_value_definition=obs.get('best_value_definition', 'unspecified'),
                  rp_over_a=rp_over_a,
                  thermal_p16_ppm=low, thermal_median_ppm=median, thermal_p84_ppm=high)
    if obs['kind'] in ('measurement', 'interval'):
        if obs['kind'] == 'interval':
            lower, upper = obs['lower'], obs['upper']
        else:
            n = obs['level']
            lower, upper = obs['depth']-n*obs['sigma'], obs['depth']+n*obs['sigma']
        result.update(ag_center=float(convert(obs['depth'], median, rp_over_a)),
                      ag_lower=float(convert(lower, median, rp_over_a)),
                      ag_upper=float(convert(upper, median, rp_over_a)),
                      ag_upper_at_thermal_p84=float(convert(upper, high, rp_over_a)),
                      ag_upper_at_thermal_p16=float(convert(upper, low, rp_over_a)))
    else:
        result.update(ag_center='', ag_lower='',
                      ag_upper=float(convert(obs['depth'], median, rp_over_a)),
                      ag_upper_at_thermal_p84=float(convert(obs['depth'], high, rp_over_a)),
                      ag_upper_at_thermal_p16=float(convert(obs['depth'], low, rp_over_a)))
    return result
