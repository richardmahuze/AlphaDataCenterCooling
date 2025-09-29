#!/usr/bin/env python3
"""
CLI smoke test for AlphaDataCenterCooling REST API.

Performs:
- Set control step
- Initialize at start_time
- Stream actions from RealWorld_Actions_Observations.csv
- POST /advance in a loop and save selected outputs to CSV

Usage:
  python testing/run_rest_api.py --steps 20

Requires: requests, pandas (optional: tqdm)
"""

import argparse
import os
import sys
from typing import List

import requests
import pandas as pd

try:
    from tqdm import trange
except Exception:
    def trange(n):
        return range(n)


DEFAULT_COLUMNS: List[str] = [
    'U_CT1', 'U_CT2', 'U_CT3', 'U_CT4', 'U_CT5', 'U_CT6',
    'Ffan_CT1_01', 'Ffan_CT1_02', 'Ffan_CT2_01', 'Ffan_CT2_02',
    'Ffan_CT3_01', 'Ffan_CT3_02', 'Ffan_CT4_01', 'Ffan_CT4_02',
    'Ffan_CT5_01', 'Ffan_CT5_02', 'Ffan_CT6_01', 'Ffan_CT6_02',
    'CDWP01_rpm', 'CDWP02_rpm', 'CDWP03_rpm', 'CDWP04_rpm',
    'CDWP05_rpm', 'CDWP06_rpm', 'CHWP01_rpm', 'CHWP02_rpm',
    'CHWP03_rpm', 'CHWP04_rpm', 'CHWP05_rpm', 'CHWP06_rpm',
    'CHI01', 'CHI02', 'CHI03', 'CHI04', 'CHI05', 'CHI06',
    'CHI01_CW1', 'CHI01_CW2', 'CHI01_CW3', 'CHI01_CW4',
    'CHI02_CW1', 'CHI02_CW2', 'CHI02_CW3', 'CHI02_CW4',
    'CHI03_CW1', 'CHI03_CW2', 'CHI03_CW3', 'CHI03_CW4',
    'CHI04_CW1', 'CHI04_CW2', 'CHI04_CW3', 'CHI04_CW4',
    'CHI05_CW1', 'CHI05_CW2', 'CHI05_CW3', 'CHI05_CW4',
    'CHI06_CW1', 'CHI06_CW2', 'CHI06_CW3', 'CHI06_CW4',
    'CHI01_CHW1', 'CHI01_CHW2', 'CHI01_CHW3', 'CHI01_CHW4',
    'CHI02_CHW1', 'CHI02_CHW2', 'CHI02_CHW3', 'CHI02_CHW4',
    'CHI03_CHW1', 'CHI03_CHW2', 'CHI03_CHW3', 'CHI03_CHW4',
    'CHI04_CHW1', 'CHI04_CHW2', 'CHI04_CHW3', 'CHI04_CHW4',
    'CHI05_CHW1', 'CHI05_CHW2', 'CHI05_CHW3', 'CHI05_CHW4',
    'CHI06_CHW1', 'CHI06_CHW2', 'CHI06_CHW3', 'CHI06_CHW4',
    'CDWP01_ONOFF', 'CDWP02_ONOFF', 'CDWP03_ONOFF', 'CDWP04_ONOFF',
    'CDWP05_ONOFF', 'CDWP06_ONOFF', 'CHWP01_ONOFF', 'CHWP02_ONOFF',
    'CHWP03_ONOFF', 'CHWP04_ONOFF', 'CHWP05_ONOFF', 'CHWP06_ONOFF',
    'CWP_speedInput', 'Tchws_set_CHI', 'Tchws_set_HEX', 'CWP_activatedNumber'
]


def main() -> int:
    parser = argparse.ArgumentParser(description='AlphaDataCenterCooling REST API smoke test')
    parser.add_argument('--url', default='http://127.0.0.1:5000', help='Base URL of the REST API')
    parser.add_argument('--start-time', type=float, default=0.0, help='Initialization start time (s)')
    parser.add_argument('--step-size', type=int, default=300, help='Control step (s), must be multiple of 300')
    parser.add_argument('--steps', type=int, default=20, help='Number of steps to simulate')
    parser.add_argument('--csv', default=None, help='Path to RealWorld_Actions_Observations.csv')
    parser.add_argument('--out', default=None, help='Output CSV for results')
    args = parser.parse_args()

    # Resolve paths relative to this script for sensible defaults
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = args.csv or os.path.join(script_dir, 'RealWorld_Actions_Observations.csv')
    out_path = args.out or os.path.join(script_dir, 'Pumps_P_Pyfmi_mlp_restapi.csv')

    # Quick health checks
    try:
        r = requests.get(f'{args.url}/name', timeout=10)
        r.raise_for_status()
        print('Service name:', r.json().get('payload', {}).get('name'))
        r = requests.get(f'{args.url}/version', timeout=10)
        r.raise_for_status()
        print('Service version:', r.json().get('payload', {}).get('version'))
    except Exception as e:
        print('Error: service not reachable or unhealthy:', e)
        return 2

    # Configure step
    try:
        r = requests.put(f'{args.url}/step', json={'step': args.step_size}, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print('Error setting step:', e, '\nResponse:', getattr(r, 'text', ''))
        return 3

    # Initialize simulation
    try:
        r = requests.put(f'{args.url}/initialize', json={'start_time': args.start_time}, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print('Error initializing:', e, '\nResponse:', getattr(r, 'text', ''))
        return 4

    # Load actions
    if not os.path.isfile(csv_path):
        print(f'Error: actions CSV not found: {csv_path}')
        return 5

    df = pd.read_csv(csv_path)
    missing = [c for c in DEFAULT_COLUMNS if c not in df.columns]
    if missing:
        print('Error: actions CSV is missing required columns:', ', '.join(missing))
        return 6
    df2 = df[DEFAULT_COLUMNS]

    n = min(args.steps, len(df2))
    print(f'Running {n} steps with step size {args.step_size}s')

    times = []
    p_cdwps = []
    p_chwps = []

    t = 0
    for i in trange(n):
        u = df2.iloc[i].to_dict()
        try:
            resp = requests.post(f'{args.url}/advance', json=u, timeout=120)
            resp.raise_for_status()
            payload = resp.json().get('payload', {})
        except Exception as e:
            print(f'Error at step {i}:', e, '\nResponse:', getattr(resp, 'text', ''))
            return 7

        # Collect outputs
        try:
            p_cdwps.append(payload['P_CDWPs_sum'])
            p_chwps.append(payload['P_CHWPs_sum'])
        except KeyError:
            print('Error: expected outputs missing in payload. Keys present:', list(payload.keys()))
            return 8
        times.append(t)
        t += args.step_size

    out_df = pd.DataFrame({'time': times, 'P_CDWPs_sum': p_cdwps, 'P_CHWPs_sum': p_chwps})
    out_df.to_csv(out_path, index=False)
    print('Saved results to:', out_path)
    return 0


if __name__ == '__main__':
    sys.exit(main())

