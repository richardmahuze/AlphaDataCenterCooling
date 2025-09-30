#!/usr/bin/env python3
"""
Comprehensive REST API test script - Python version of test_REST_API.ipynb

Performs:
- Query and export all API metadata (inputs, measurements, name, version)
- Run 2000-step simulation with action streaming
- Generate comparison plots vs. ground truth and Simulink
- Export all results to txt and PNG files

Usage:
  python testing/test_rest_api_full.py

Requires: requests, pandas, matplotlib, tqdm
"""

import argparse
import json
import os
import sys
from typing import Dict, List

import requests
import pandas as pd
import matplotlib.pyplot as plt

try:
    from tqdm import tqdm
except Exception:
    def tqdm(iterable):
        return iterable


class Logger:
    """Simple logger that writes to both stdout and a file."""
    def __init__(self, filepath):
        self.terminal = sys.stdout
        self.log = open(filepath, 'w')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    def close(self):
        self.log.close()


def query_api_metadata(url: str, output_file: str) -> Dict:
    """Query all API metadata and save to text file."""
    print("=" * 80)
    print("QUERYING API METADATA")
    print("=" * 80)

    metadata = {}

    with open(output_file, 'w') as f:
        # Query inputs
        print("\n1. Querying control inputs...")
        try:
            r = requests.get(f'{url}/inputs', timeout=10)
            r.raise_for_status()
            input_info = r.json()
            metadata['inputs'] = input_info

            f.write("=" * 80 + "\n")
            f.write("CONTROL INPUTS (/inputs)\n")
            f.write("=" * 80 + "\n")
            f.write(json.dumps(input_info, indent=2) + "\n\n")

            num_inputs = len(input_info.get('payload', {}))
            print(f"   Found {num_inputs} control inputs")
        except Exception as e:
            print(f"   Error querying inputs: {e}")
            return {}

        # Query measurements
        print("2. Querying measurements...")
        try:
            r = requests.get(f'{url}/measurements', timeout=10)
            r.raise_for_status()
            measurements_info = r.json()
            metadata['measurements'] = measurements_info

            f.write("=" * 80 + "\n")
            f.write("MEASUREMENTS (/measurements)\n")
            f.write("=" * 80 + "\n")
            f.write(json.dumps(measurements_info, indent=2) + "\n\n")

            num_measurements = len(measurements_info.get('payload', {}))
            print(f"   Found {num_measurements} measurements")
        except Exception as e:
            print(f"   Error querying measurements: {e}")
            return {}

        # Query name
        print("3. Querying test case name...")
        try:
            r = requests.get(f'{url}/name', timeout=10)
            r.raise_for_status()
            name_info = r.json()
            metadata['name'] = name_info

            f.write("=" * 80 + "\n")
            f.write("TEST CASE NAME (/name)\n")
            f.write("=" * 80 + "\n")
            f.write(json.dumps(name_info, indent=2) + "\n\n")

            test_name = name_info.get('payload', {}).get('name', 'Unknown')
            print(f"   Test case name: {test_name}")
        except Exception as e:
            print(f"   Error querying name: {e}")

        # Query version
        print("4. Querying version...")
        try:
            r = requests.get(f'{url}/version', timeout=10)
            r.raise_for_status()
            version_info = r.json()
            metadata['version'] = version_info

            f.write("=" * 80 + "\n")
            f.write("VERSION (/version)\n")
            f.write("=" * 80 + "\n")
            f.write(json.dumps(version_info, indent=2) + "\n\n")

            version_num = version_info.get('payload', {}).get('version', 'Unknown')
            print(f"   Version: {version_num}")
        except Exception as e:
            print(f"   Error querying version: {e}")

    print(f"\nAPI metadata saved to: {output_file}")
    return metadata


def run_simulation(url: str, csv_path: str, step_size: int, total_steps: int, output_csv: str):
    """Run the full simulation and save results."""
    print("\n" + "=" * 80)
    print("RUNNING SIMULATION")
    print("=" * 80)

    # Set step size
    print(f"\n1. Setting step size to {step_size}s...")
    try:
        r = requests.put(f'{url}/step', json={'step': step_size}, timeout=10)
        r.raise_for_status()
        print("   Step size set successfully")
    except Exception as e:
        print(f"   Error setting step: {e}")
        return False

    # Initialize simulation
    print("2. Initializing simulation at time 0...")
    try:
        r = requests.put(f'{url}/initialize', json={'start_time': 0}, timeout=30)
        r.raise_for_status()
        init_payload = r.json().get('payload', {})
        print(f"   Simulation initialized successfully")
        print(f"   Initial P_CDWPs_sum: {init_payload.get('P_CDWPs_sum', 'N/A')} W")
        print(f"   Initial P_CHWPs_sum: {init_payload.get('P_CHWPs_sum', 'N/A')} W")
        print(f"   Initial P_Chillers_sum: {init_payload.get('P_Chillers_sum', 'N/A')} W")
        print(f"   Initial P_CTfans_sum: {init_payload.get('P_CTfans_sum', 'N/A')} W")
    except Exception as e:
        print(f"   Error initializing: {e}")
        return False

    # Load actions
    print(f"3. Loading actions from {csv_path}...")
    if not os.path.isfile(csv_path):
        print(f"   Error: Actions CSV not found")
        return False

    df = pd.read_csv(csv_path)
    action_columns = [
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

    missing = [c for c in action_columns if c not in df.columns]
    if missing:
        print(f"   Error: Missing columns: {', '.join(missing)}")
        return False

    df2 = df[action_columns]
    print(f"   Loaded {len(df2)} action rows")

    # Run simulation loop
    n = min(total_steps, len(df2))
    print(f"4. Running {n} simulation steps...")

    times = []
    P_CDWPs_sum = []
    P_CHWPs_sum = []

    t = 0
    for i in tqdm(range(n), desc="   Progress"):
        u = df2.iloc[i].to_dict()
        try:
            resp = requests.post(f'{url}/advance', json=u, timeout=120)
            resp.raise_for_status()
            payload = resp.json().get('payload', {})
        except Exception as e:
            print(f"\n   Error at step {i}: {e}")
            return False

        # Collect outputs
        P_CDWPs_sum.append(payload.get('P_CDWPs_sum', 0))
        P_CHWPs_sum.append(payload.get('P_CHWPs_sum', 0))
        times.append(t)
        t += step_size

    # Save results
    print(f"\n5. Saving results to {output_csv}...")
    out_df = pd.DataFrame({
        'time': times,
        'P_CDWPs_sum': P_CDWPs_sum,
        'P_CHWPs_sum': P_CHWPs_sum
    })
    out_df.to_csv(output_csv, index=False)
    print(f"   Results saved successfully")

    # Print summary statistics
    print("\n" + "=" * 80)
    print("SIMULATION SUMMARY")
    print("=" * 80)
    print(f"Total steps completed: {n}")
    print(f"Simulation time: 0 to {t}s ({t/3600:.1f} hours)")
    print(f"\nP_CDWPs_sum statistics:")
    print(f"  Mean: {out_df['P_CDWPs_sum'].mean():.2f} W")
    print(f"  Min:  {out_df['P_CDWPs_sum'].min():.2f} W")
    print(f"  Max:  {out_df['P_CDWPs_sum'].max():.2f} W")
    print(f"\nP_CHWPs_sum statistics:")
    print(f"  Mean: {out_df['P_CHWPs_sum'].mean():.2f} W")
    print(f"  Min:  {out_df['P_CHWPs_sum'].min():.2f} W")
    print(f"  Max:  {out_df['P_CHWPs_sum'].max():.2f} W")

    return True


def generate_plots(script_dir: str):
    """Generate comparison plots and save as PNG files."""
    print("\n" + "=" * 80)
    print("GENERATING COMPARISON PLOTS")
    print("=" * 80)

    # Load data files
    print("\n1. Loading data files...")
    try:
        truth_path = os.path.join(script_dir, 'RealWorld_Actions_Observations.csv')
        simulink_path = os.path.join(script_dir, 'Pumps_P_Simulink.csv')
        pyfmi_path = os.path.join(script_dir, 'Pumps_P_Pyfmi_mlp_restapi.csv')

        df_truth = pd.read_csv(truth_path, usecols=['P_CDWPs_sum', 'P_CHWPs_sum'])
        df_simulink = pd.read_csv(simulink_path)
        df_pyfmi_mlp = pd.read_csv(pyfmi_path)

        print(f"   Truth data: {len(df_truth)} rows")
        print(f"   Simulink data: {len(df_simulink)} rows")
        print(f"   PyFMI+MLP data: {len(df_pyfmi_mlp)} rows")
    except Exception as e:
        print(f"   Error loading data files: {e}")
        return False

    # Determine plot range
    n_points = min(2000, len(df_truth) - 1, len(df_simulink) - 1, len(df_pyfmi_mlp))
    print(f"   Plotting {n_points} points")

    # Plot 1: P_CDWPs_sum comparison
    print("\n2. Generating P_CDWPs_sum comparison plot...")
    plt.figure(figsize=(24, 16))
    plt.plot(range(0, n_points), df_truth['P_CDWPs_sum'].iloc[1:n_points+1],
             label='Truth', linewidth=2)
    plt.plot(range(0, n_points), df_simulink['Pcdwp_sum'].iloc[1:n_points+1],
             label='Simulink', linewidth=2)
    plt.plot(range(0, n_points), df_pyfmi_mlp['P_CDWPs_sum'].iloc[0:n_points] / 1000,
             label='PyFMI+MLP', linewidth=2)
    plt.legend(fontsize=25)
    plt.xlabel('Time step', fontsize=20)
    plt.ylabel('P_CDWPs_sum (kW)', fontsize=20)
    plt.title('Condenser Water Pumps Power Comparison', fontsize=30)
    plt.xticks(fontsize=15)
    plt.yticks(fontsize=15)
    plt.grid(True, alpha=0.3)

    cdwp_plot_path = os.path.join(script_dir, 'P_CDWPs_comparison.png')
    plt.savefig(cdwp_plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"   Saved to: {cdwp_plot_path}")

    # Plot 2: P_CHWPs_sum comparison
    print("3. Generating P_CHWPs_sum comparison plot...")
    plt.figure(figsize=(24, 16))
    plt.plot(range(0, n_points), df_truth['P_CHWPs_sum'].iloc[1:n_points+1],
             label='Truth', linewidth=2)
    plt.plot(range(0, n_points), df_simulink['Pchwp_sum'].iloc[1:n_points+1],
             label='Simulink', linewidth=3)
    plt.plot(range(0, n_points), df_pyfmi_mlp['P_CHWPs_sum'].iloc[0:n_points] / 1000,
             label='PyFMI+MLP', linewidth=2)
    plt.legend(fontsize=25)
    plt.xlabel('Time step', fontsize=20)
    plt.ylabel('P_CHWPs_sum (kW)', fontsize=20)
    plt.title('Chilled Water Pumps Power Comparison', fontsize=30)
    plt.xticks(fontsize=15)
    plt.yticks(fontsize=15)
    plt.grid(True, alpha=0.3)

    chwp_plot_path = os.path.join(script_dir, 'P_CHWPs_comparison.png')
    plt.savefig(chwp_plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"   Saved to: {chwp_plot_path}")

    print("\nPlots generated successfully")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description='Comprehensive REST API test (notebook to script)')
    parser.add_argument('--url', default='http://127.0.0.1:5000', help='Base URL of REST API')
    parser.add_argument('--step-size', type=int, default=300, help='Control step (s), must be multiple of 300')
    parser.add_argument('--steps', type=int, default=2000, help='Number of steps to simulate')
    parser.add_argument('--csv', default=None, help='Path to RealWorld_Actions_Observations.csv')
    parser.add_argument('--out', default=None, help='Output CSV for results')
    parser.add_argument('--skip-plots', action='store_true', help='Skip plot generation')
    args = parser.parse_args()

    # Resolve paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = args.csv or os.path.join(script_dir, 'RealWorld_Actions_Observations.csv')
    out_csv = args.out or os.path.join(script_dir, 'Pumps_P_Pyfmi_mlp_restapi.csv')
    metadata_file = os.path.join(script_dir, 'api_metadata.txt')
    log_file = os.path.join(script_dir, 'test_results.txt')

    # Set up logging
    logger = Logger(log_file)
    sys.stdout = logger

    try:
        print("=" * 80)
        print("ALPHADATACENTER REST API COMPREHENSIVE TEST")
        print("=" * 80)
        print(f"URL: {args.url}")
        print(f"Step size: {args.step_size}s")
        print(f"Total steps: {args.steps}")
        print(f"Actions CSV: {csv_path}")
        print(f"Output CSV: {out_csv}")
        print()

        # Quick health check
        print("Checking service health...")
        try:
            r = requests.get(f'{args.url}/name', timeout=10)
            r.raise_for_status()
            print("Service is reachable\n")
        except Exception as e:
            print(f"Error: Service not reachable: {e}")
            return 2

        # Query and export API metadata
        metadata = query_api_metadata(args.url, metadata_file)
        if not metadata:
            print("Failed to query API metadata")
            return 3

        # Run simulation
        success = run_simulation(args.url, csv_path, args.step_size, args.steps, out_csv)
        if not success:
            print("\nSimulation failed")
            return 4

        # Generate plots
        if not args.skip_plots:
            success = generate_plots(script_dir)
            if not success:
                print("\nPlot generation failed (non-fatal)")
        else:
            print("\nSkipping plot generation (--skip-plots)")

        print("\n" + "=" * 80)
        print("TEST COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"\nOutput files:")
        print(f"  - API metadata: {metadata_file}")
        print(f"  - Simulation results: {out_csv}")
        print(f"  - Test log: {log_file}")
        if not args.skip_plots:
            print(f"  - CDWP plot: {os.path.join(script_dir, 'P_CDWPs_comparison.png')}")
            print(f"  - CHWP plot: {os.path.join(script_dir, 'P_CHWPs_comparison.png')}")

        return 0

    finally:
        sys.stdout = logger.terminal
        logger.close()


if __name__ == '__main__':
    sys.exit(main())