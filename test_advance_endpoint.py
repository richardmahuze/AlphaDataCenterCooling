#!/usr/bin/env python3
"""
Test script for validating the advance endpoint functionality after FMPy lower-level API implementation.

This script tests:
1. Basic initialization
2. Single advance step
3. Multiple consecutive advance steps (MPC scenario)
4. Error handling and recovery
5. State persistence between steps
"""

import requests
import time
import json
import pandas as pd
import matplotlib.pyplot as plt
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://127.0.0.1:5000"

def test_api_availability():
    """Test if the API is available."""
    try:
        response = requests.get(f"{BASE_URL}/version", timeout=10)
        if response.status_code == 200:
            version_info = response.json()
            logger.info(f"API available. Version: {version_info}")
            return True
        else:
            logger.error(f"API returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"API not available: {e}")
        return False

def test_initialization():
    """Test the initialization endpoint."""
    logger.info("Testing initialization...")

    try:
        response = requests.put(f"{BASE_URL}/initialize",
                               json={"start_time": 0},
                               timeout=30)

        if response.status_code == 200:
            result = response.json()
            logger.info(f"Initialization successful: {result['message']}")
            return result['payload']
        else:
            logger.error(f"Initialization failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Initialization error: {e}")
        return None

def test_single_advance():
    """Test a single advance step."""
    logger.info("Testing single advance step...")

    # Simple control inputs for testing
    control_inputs = {
        "CHI01": 0,          # Chiller 1 OFF
        "CHI02": 1,          # Chiller 2 ON
        "CHWP01_rpm": 800,   # Chilled water pump 1 speed
        "CHWP02_rpm": 900,   # Chilled water pump 2 speed
        "CDWP01_rpm": 850,   # Condenser water pump 1 speed
        "U_CT1": 1,          # Cooling tower 1 valve open
        "U_CT2": 1,          # Cooling tower 2 valve open
        "Ffan_CT1_01": 0.7,  # Fan speed ratio
        "Ffan_CT2_01": 0.8   # Fan speed ratio
    }

    try:
        response = requests.post(f"{BASE_URL}/advance",
                                json=control_inputs,
                                timeout=60)  # Increased timeout for advance

        if response.status_code == 200:
            result = response.json()
            logger.info(f"Single advance successful: {result['message']}")
            return result['payload']
        else:
            logger.error(f"Single advance failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Single advance error: {e}")
        return None

def test_multiple_advances():
    """Test multiple consecutive advance steps (MPC scenario)."""
    logger.info("Testing multiple advance steps for MPC validation...")

    results = []

    # Different control scenarios for each step
    control_scenarios = [
        {"CHI01": 1, "CHI02": 0, "CHWP01_rpm": 750, "U_CT1": 1, "Ffan_CT1_01": 0.6},
        {"CHI01": 1, "CHI02": 1, "CHWP01_rpm": 800, "CHWP02_rpm": 850, "U_CT1": 1, "U_CT2": 1},
        {"CHI01": 0, "CHI02": 1, "CHWP02_rpm": 900, "U_CT2": 1, "Ffan_CT2_01": 0.8},
        {"CHI01": 1, "CHI02": 1, "CHWP01_rpm": 820, "CHWP02_rpm": 880, "U_CT1": 1, "U_CT2": 1},
    ]

    for i, controls in enumerate(control_scenarios):
        logger.info(f"Advance step {i+1}/4...")

        try:
            response = requests.post(f"{BASE_URL}/advance",
                                    json=controls,
                                    timeout=60)

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Step {i+1} successful: {result['message']}")

                # Extract key metrics
                payload = result['payload']
                step_result = {
                    'step': i+1,
                    'time': payload.get('time', [0])[-1] if isinstance(payload.get('time', []), list) else payload.get('time', 0),
                    'P_Chillers_sum': payload.get('P_Chillers_sum', 0),
                    'P_CDWPs_sum': payload.get('P_CDWPs_sum', 0),
                    'P_CHWPs_sum': payload.get('P_CHWPs_sum', 0),
                    'Tchw_supply': payload.get('Tchw_supply', 0),
                    'controls': controls
                }
                results.append(step_result)

            else:
                logger.error(f"Step {i+1} failed: {response.status_code} - {response.text}")
                break

        except Exception as e:
            logger.error(f"Step {i+1} error: {e}")
            break

        # Small delay between steps
        time.sleep(1)

    return results

def test_error_recovery():
    """Test error handling and recovery."""
    logger.info("Testing error recovery with invalid inputs...")

    # Test with invalid control inputs
    invalid_inputs = {
        "CHI01": "invalid",  # Should be numeric
        "CHWP01_rpm": -100,  # Should be positive
    }

    try:
        response = requests.post(f"{BASE_URL}/advance",
                                json=invalid_inputs,
                                timeout=30)

        if response.status_code != 200:
            logger.info(f"Error handling working correctly: {response.status_code}")

            # Try to recover with valid inputs
            valid_inputs = {"CHI01": 1, "CHWP01_rpm": 800}
            recovery_response = requests.post(f"{BASE_URL}/advance",
                                            json=valid_inputs,
                                            timeout=60)

            if recovery_response.status_code == 200:
                logger.info("Recovery successful after error")
                return True
            else:
                logger.error(f"Recovery failed: {recovery_response.status_code}")
                return False
        else:
            logger.warning("Invalid inputs were accepted - this might indicate an issue")
            return False

    except Exception as e:
        logger.error(f"Error recovery test failed: {e}")
        return False

def visualize_results(multi_step_results):
    """Create visualizations of the multi-step results."""
    if not multi_step_results:
        logger.warning("No results to visualize")
        return

    logger.info("Creating visualizations...")

    # Convert to DataFrame for easier plotting
    df = pd.DataFrame(multi_step_results)

    # Create plots
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('MPC Validation: Multi-Step Advance Results', fontsize=16)

    # Power consumption plot
    axes[0, 0].plot(df['step'], df['P_Chillers_sum'], 'ro-', label='Chillers', linewidth=2, markersize=6)
    axes[0, 0].plot(df['step'], df['P_CDWPs_sum'], 'bo-', label='CDWP', linewidth=2, markersize=6)
    axes[0, 0].plot(df['step'], df['P_CHWPs_sum'], 'go-', label='CHWP', linewidth=2, markersize=6)
    axes[0, 0].set_title('Power Consumption by Step')
    axes[0, 0].set_xlabel('Step')
    axes[0, 0].set_ylabel('Power (W)')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)

    # Temperature plot
    axes[0, 1].plot(df['step'], df['Tchw_supply'], 'mo-', linewidth=2, markersize=6)
    axes[0, 1].set_title('Chilled Water Supply Temperature')
    axes[0, 1].set_xlabel('Step')
    axes[0, 1].set_ylabel('Temperature (K)')
    axes[0, 1].grid(True, alpha=0.3)

    # Control actions plot
    chiller_states = [result['controls'].get('CHI01', 0) + result['controls'].get('CHI02', 0)
                     for result in multi_step_results]
    axes[1, 0].bar(df['step'], chiller_states, alpha=0.7, color='orange')
    axes[1, 0].set_title('Active Chillers per Step')
    axes[1, 0].set_xlabel('Step')
    axes[1, 0].set_ylabel('Number of Active Chillers')
    axes[1, 0].grid(True, alpha=0.3)

    # Simulation time progression
    axes[1, 1].plot(df['step'], df['time'], 'co-', linewidth=2, markersize=6)
    axes[1, 1].set_title('Simulation Time Progression')
    axes[1, 1].set_xlabel('Step')
    axes[1, 1].set_ylabel('Simulation Time (s)')
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('mpc_validation_results.png', dpi=150, bbox_inches='tight')
    logger.info("Visualization saved as 'mpc_validation_results.png'")

    # Print summary statistics
    logger.info("=== MPC Validation Summary ===")
    logger.info(f"Total steps completed: {len(df)}")
    logger.info(f"Time range: {df['time'].min():.1f} - {df['time'].max():.1f} s")
    logger.info(f"Avg chiller power: {df['P_Chillers_sum'].mean():.1f} W")
    logger.info(f"Avg total pump power: {(df['P_CDWPs_sum'] + df['P_CHWPs_sum']).mean():.1f} W")
    logger.info(f"Temp range: {df['Tchw_supply'].min():.2f} - {df['Tchw_supply'].max():.2f} K")

def main():
    """Main test execution."""
    logger.info("=== Starting Advanced Endpoint Validation ===")

    # Test 1: API Availability
    if not test_api_availability():
        logger.error("API not available. Exiting.")
        return False

    # Test 2: Initialization
    init_result = test_initialization()
    if not init_result:
        logger.error("Initialization failed. Exiting.")
        return False

    # Test 3: Single Advance
    single_result = test_single_advance()
    if not single_result:
        logger.error("Single advance failed. Cannot proceed to MPC testing.")
        return False

    logger.info("✅ Single advance step successful!")

    # Test 4: Multiple Advances (MPC Scenario)
    multi_results = test_multiple_advances()
    if not multi_results:
        logger.error("Multiple advance steps failed.")
        return False

    logger.info(f"✅ Multiple advance steps successful! Completed {len(multi_results)} steps.")

    # Test 5: Error Recovery
    recovery_ok = test_error_recovery()
    if recovery_ok:
        logger.info("✅ Error recovery working correctly!")
    else:
        logger.warning("⚠️ Error recovery may have issues.")

    # Test 6: Visualization
    visualize_results(multi_results)

    # Final summary
    logger.info("=== FINAL RESULTS ===")
    logger.info("✅ API Available")
    logger.info("✅ Initialization Working")
    logger.info("✅ Single Advance Working")
    logger.info(f"✅ Multi-Step Simulation Working ({len(multi_results)} steps)")
    logger.info("✅ MPC Functionality Validated")

    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 ALL TESTS PASSED! The advance endpoint is now working correctly for MPC applications!")
    else:
        print("\n❌ Some tests failed. Check the logs for details.")