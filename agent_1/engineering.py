"""FaultSense: reproducible sensor analysis, not a fault-certainty classifier."""
import io
import numpy as np
import pandas as pd

METRICS = {'temperature_c': '°C', 'vibration_mm_s': 'mm/s RMS', 'current_a': 'A', 'rpm': 'RPM'}


def read_sensors(data):
    if len(data) > 10 * 1024 * 1024:
        raise ValueError('Sensor CSV must be smaller than 10 MB.')
    try:
        df = pd.read_csv(io.BytesIO(data))
    except Exception:
        raise ValueError('Cannot read sensor CSV. Download the sample for the required format.') from None
    required = ['timestamp', *METRICS]
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError('Missing columns: ' + ', '.join(sorted(missing)))
    if not 5 <= len(df) <= 100000:
        raise ValueError('Supply between 5 and 100,000 sensor rows.')
    df = df[required].copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce', utc=True)
    for col in METRICS:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        if not np.isfinite(df[col]).all():
            raise ValueError(f'{col} has missing or non-finite values. Correct them before analysis.')
    if df['timestamp'].isna().any() or df['timestamp'].duplicated().any():
        raise ValueError('Timestamps must be valid and unique.')
    if (df[['vibration_mm_s', 'current_a', 'rpm']] < 0).any().any():
        raise ValueError('Vibration, current and RPM cannot be negative.')
    return df.sort_values('timestamp').reset_index(drop=True)


def analyze_sensors(df, limits):
    if set(limits) != {'temperature_c', 'vibration_mm_s', 'current_a'}:
        raise ValueError('Provide temperature, vibration and current operating limits.')
    if any(not np.isfinite(v) or v <= 0 for v in limits.values()):
        raise ValueError('Operating limits must be finite and positive.')
    metrics = {}
    anomalies = []
    for col in METRICS:
        series = df[col]
        median = float(series.median())
        mad = float((series - median).abs().median())
        # Constant baselines still detect deviations; never divide by zero.
        robust = (series - median).abs() > (3.5 * mad / 0.6745 if mad > 1e-9 else max(abs(median) * 0.1, 1e-6))
        breach = series > limits[col] if col in limits else pd.Series(False, index=df.index)
        metrics[col] = {'unit': METRICS[col], 'mean': round(float(series.mean()), 3),
                        'maximum': round(float(series.max()), 3), 'median': round(median, 3),
                        'limit': limits.get(col), 'limit_exceedances': int(breach.sum()),
                        'statistical_outliers': int(robust.sum())}
        for i in df.index[breach | robust]:
            anomalies.append({'timestamp': df.loc[i, 'timestamp'].isoformat(), 'metric': col,
                              'value': float(series[i]), 'reason': 'Operating limit exceeded' if breach[i] else 'Statistical deviation'})
    hot = metrics['temperature_c']['limit_exceedances'] > 0
    vibration = metrics['vibration_mm_s']['limit_exceedances'] > 0
    current = metrics['current_a']['limit_exceedances'] > 0
    hypotheses = []
    if hot and current:
        hypotheses.append({'hypothesis': 'Excess load or an electrical supply issue',
                           'evidence': 'Both temperature and current exceeded user-entered limits.',
                           'check': 'Compare load and supply measurements against rated conditions.'})
    if vibration:
        hypotheses.append({'hypothesis': 'Imbalance, alignment or bearing-related issue',
                           'evidence': 'Vibration exceeded the user-entered limit.',
                           'check': 'Obtain vibration spectrum and bearing condition measurements to distinguish causes.'})
    if hot:
        hypotheses.append({'hypothesis': 'Cooling or ventilation issue',
                           'evidence': 'Temperature exceeded the user-entered limit.',
                           'check': 'Check ambient temperature, airflow and cooling condition using the maintenance procedure.'})
    if not hypotheses:
        hypotheses.append({'hypothesis': 'No operating-limit breach in this dataset',
                           'evidence': 'All monitored values are within entered limits; this does not prove machine health.',
                           'check': 'Compare with a verified healthy baseline and investigate any reported symptoms.'})
    gaps = df.timestamp.diff().dt.total_seconds().dropna()
    return {'rows': len(df), 'start': df.timestamp.iloc[0].isoformat(), 'end': df.timestamp.iloc[-1].isoformat(),
            'sampling_irregular': bool(gaps.max() > 1.5 * gaps.median()), 'metrics': metrics,
            'anomaly_count': len(anomalies), 'anomalies': anomalies[:200],
            'anomalies_truncated': len(anomalies) > 200, 'hypotheses_in_rule_priority_order': hypotheses,
            'limitations': ['Hypotheses are rule-based screening, not confirmed faults or calibrated probabilities.',
                            'Operating limits were entered by the user, not automatically verified against the manual.',
                            'Statistical outliers are deviations within this run, not a learned healthy baseline.',
                            'No equipment actuation; inspections require appropriate isolation and qualified personnel.']}


def offline_report(result):
    lines = ['# FaultSense diagnostic report', '**Offline demo: rule-based screening, no LLM.**',
             f"Analyzed {result['rows']} rows; flagged {result['anomaly_count']} metric observations.",
             '## Investigation priorities']
    for h in result['hypotheses_in_rule_priority_order']:
        lines += [f"### {h['hypothesis']}", h['evidence'], 'Next check: ' + h['check']]
    return '\n\n'.join(lines) + '\n\n' + '\n'.join('- ' + s for s in result['limitations'])
