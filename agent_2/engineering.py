"""BuildWise: constrained enumeration of sensor-node BOMs with energy calculations."""
import io
import itertools
import math
import numpy as np
import pandas as pd

REQUIRED = ['part_id', 'category', 'price_inr', 'voltage_min_v', 'voltage_max_v', 'logic_v',
            'interface', 'wifi', 'active_ma', 'sleep_ma', 'capacity_mah', 'nominal_v',
            'output_v', 'efficiency', 'max_output_ma', 'quiescent_ma', 'stock', 'source']
NUMERIC = [c for c in REQUIRED if c not in ['part_id', 'category', 'interface', 'wifi', 'source']]


def read_catalog(data):
    if len(data) > 5 * 1024 * 1024:
        raise ValueError('Catalogue must be smaller than 5 MB.')
    try:
        df = pd.read_csv(io.BytesIO(data)).fillna('')
    except Exception:
        raise ValueError('Cannot read catalogue CSV.') from None
    if set(REQUIRED) - set(df.columns):
        raise ValueError('Catalogue columns are missing. Use the downloadable template with units in headers.')
    if not 4 <= len(df) <= 80:
        raise ValueError('Catalogue must contain 4–80 components.')
    if df.part_id.duplicated().any() or (df.part_id.astype(str).str.strip() == '').any():
        raise ValueError('Part IDs must be unique and non-empty.')
    if not set(df.category) <= {'controller', 'sensor', 'battery', 'regulator'}:
        raise ValueError('Categories must be controller, sensor, battery or regulator.')
    for c in NUMERIC:
        df[c] = pd.to_numeric(df[c], errors='coerce')
        if not np.isfinite(df[c]).all() or (df[c] < 0).any():
            raise ValueError(f'{c} must contain finite, non-negative numbers (use 0 for inapplicable fields).')
    if (df.voltage_min_v > df.voltage_max_v).any():
        raise ValueError('Minimum voltage cannot exceed maximum voltage.')
    if not set(df.wifi.astype(str).str.lower()) <= {'true', 'false'}:
        raise ValueError('wifi must be true or false.')
    df['wifi'] = df.wifi.astype(str).str.lower().eq('true')
    for row in df.to_dict('records'):
        kind = row['category']
        if kind == 'battery' and (row['capacity_mah'] <= 0 or row['nominal_v'] <= 0):
            raise ValueError('Batteries need positive capacity and nominal voltage.')
        if kind == 'regulator' and not (0 < row['efficiency'] <= 1 and row['output_v'] > 0 and row['max_output_ma'] > 0):
            raise ValueError('Regulators need efficiency in (0,1], output voltage and current rating.')
        if kind in ('controller', 'sensor') and (row['voltage_max_v'] <= 0 or row['logic_v'] <= 0):
            raise ValueError('Controllers and sensors need supply and logic voltage specifications.')
    return df


def validate_requirements(req):
    for name in ('budget_inr', 'runtime_days', 'interval_s', 'active_s', 'usable_fraction'):
        if not isinstance(req.get(name), (int, float)) or not math.isfinite(req[name]) or req[name] <= 0:
            raise ValueError(f'{name} must be finite and positive.')
    if req['active_s'] > req['interval_s']:
        raise ValueError('Active duration cannot exceed the sample interval.')
    if req['usable_fraction'] > 1:
        raise ValueError('Usable battery fraction must be at most 1.')
    if not isinstance(req.get('wifi'), bool):
        raise ValueError('Wi-Fi requirement must be true or false.')


def evaluate_catalog(df, req):
    validate_requirements(req)
    groups = [df[(df.category == c) & (df.stock >= 1)].to_dict('records')
              for c in ('controller', 'sensor', 'battery', 'regulator')]
    if any(not g for g in groups):
        raise ValueError('Need at least one in-stock controller, sensor, battery and regulator.')
    count = math.prod(len(g) for g in groups)
    if count > 20000:
        raise ValueError('Too many combinations. Limit catalogue to 20,000 combinations per run.')
    candidates = []
    for controller, sensor, battery, regulator in itertools.product(*groups):
        supply = regulator['output_v']
        interfaces = set(str(controller['interface']).upper().split('|'))
        peak = controller['active_ma'] + sensor['active_ma']
        checks = {
            'controller_supply': controller['voltage_min_v'] <= supply <= controller['voltage_max_v'],
            'sensor_supply': sensor['voltage_min_v'] <= supply <= sensor['voltage_max_v'],
            'logic_voltage': abs(controller['logic_v'] - sensor['logic_v']) < 0.05,
            'interface': str(sensor['interface']).upper() in interfaces,
            'wifi': not req['wifi'] or controller['wifi'],
            'battery_full_range': regulator['voltage_min_v'] <= battery['voltage_min_v'] and battery['voltage_max_v'] <= regulator['voltage_max_v'],
            'regulator_current_with_20pct_margin': regulator['max_output_ma'] >= peak * 1.2,
        }
        duty = req['active_s'] / req['interval_s']
        avg_ma = peak * duty + (controller['sleep_ma'] + sensor['sleep_ma']) * (1 - duty)
        input_mw = supply * avg_ma / regulator['efficiency'] + battery['nominal_v'] * regulator['quiescent_ma']
        wh = battery['capacity_mah'] * battery['nominal_v'] / 1000 * req['usable_fraction']
        hours = wh * 1000 / input_mw if input_mw > 0 else 0
        bom = [{'part_id': p['part_id'], 'category': p['category'], 'quantity': 1,
                'unit_price_inr': p['price_inr'], 'source': p['source']} for p in (controller, sensor, battery, regulator)]
        cost = sum(p['unit_price_inr'] for p in bom)
        checks['budget'] = cost <= req['budget_inr']
        checks['runtime'] = hours >= req['runtime_days'] * 24
        candidates.append({'bom': bom, 'cost_inr': round(cost, 2), 'runtime_days': round(hours / 24, 2),
                           'average_load_ma': round(avg_ma, 4), 'battery_input_mw': round(input_mw, 4),
                           'usable_energy_wh': round(wh, 4), 'peak_load_ma': peak, 'checks': checks,
                           'failed_constraints': [k for k, v in checks.items() if not v],
                           'feasible': all(checks.values())})
    candidates.sort(key=lambda c: (len(c['failed_constraints']), c['cost_inr'], -c['runtime_days']))
    feasible = [c for c in candidates if c['feasible']]
    return {'requirements': req, 'combinations_evaluated': count, 'feasible_count': len(feasible),
            'status': 'Feasible within modelled constraints' if feasible else 'No feasible design; requirements were not relaxed',
            'recommended': feasible[0] if feasible else None, 'alternatives': (feasible[1:4] if feasible else candidates[:3]),
            'assumptions': ['Scope: one controller, one digital temperature sensor, one battery and one regulator.',
                            'Catalogue values are user-supplied; retrieved datasheets provide evidence, not automatic specification verification.',
                            'Runtime uses nominal battery energy, entered duty cycle, constant conversion efficiency and battery-side quiescent current.',
                            'Active current must include radio peaks; active duration includes boot, acquisition and network connection time.',
                            'Excluded: taxes, shipping, PCB, enclosure, charger, battery protection, connector and assembly costs.',
                            'Pin mapping, I2C addresses, battery discharge rating, transients and physical fit require further verification.']}


def offline_report(result):
    r = result['recommended']
    text = '# BuildWise design report\n\n**Offline demo: deterministic constraint solver, no LLM.**\n\n' + result['status']
    if r:
        text += f"\n\nEstimated BOM: INR {r['cost_inr']:.2f}. Estimated runtime: {r['runtime_days']:.2f} days."
        text += '\n\n' + '\n'.join('- ' + p['category'] + ': ' + p['part_id'] for p in r['bom'])
    else:
        text += '\n\nClosest alternatives are diagnostic examples, not recommended designs. Review their failed constraints.'
    return text + '\n\n## Assumptions and unresolved checks\n' + '\n'.join('- ' + a for a in result['assumptions'])
