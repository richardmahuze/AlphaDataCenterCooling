#!/usr/bin/env python3
"""
Toy Rule-Based Control Example for AlphaDataCenterCooling

This demonstrates the basic control loop structure that would be used for MPC,
but using simple rule-based logic instead of optimization. It proves that the
advance endpoint supports the fundamental MPC workflow:

1. Initialize system
2. Get current state
3. Compute control actions (rule-based instead of MPC optimization)
4. Apply controls via advance
5. Repeat

This validates that the infrastructure is ready for actual MPC implementation.
"""

import requests
import time
import numpy as np

# Handle matplotlib import gracefully
try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("⚠️ matplotlib not available - skipping visualizations")

BASE_URL = "http://127.0.0.1:5000"

class ToyRuleBasedController:
    """
    Simple rule-based controller that mimics MPC structure.

    Instead of optimization, uses basic rules:
    - Turn on chillers when temperature is too high
    - Adjust pump speeds based on load
    - Control cooling towers based on efficiency
    """

    def __init__(self):
        # Control targets (what MPC would optimize for)
        self.target_temp = 286.0  # Target chilled water supply temp (K)
        self.temp_tolerance = 1.0  # Temperature control tolerance

        # Control constraints (what MPC would respect)
        self.min_pump_speed = 600
        self.max_pump_speed = 1000

        # System state tracking
        self.control_history = []
        self.state_history = []

    def compute_control_action(self, current_state):
        """
        Compute control action using simple rules.

        In real MPC, this would be:
        - Model prediction over horizon
        - Cost function optimization
        - Constraint handling

        Here we use basic if-then rules.
        """

        # Get current system state
        current_temp = current_state.get('Tchw_supply', 286.0)
        chiller_power = current_state.get('P_Chillers_sum', 0)

        # Rule 1: Temperature control (primary objective)
        temp_error = current_temp - self.target_temp

        # Rule 2: Chiller staging based on temperature error
        if temp_error > self.temp_tolerance:
            # Too hot - turn on more chillers
            chi01 = 1
            chi02 = 1
            print(f"  🔥 Temp too high ({current_temp:.1f}K) - activating both chillers")
        elif temp_error > 0.5:
            # Slightly hot - one chiller
            chi01 = 1
            chi02 = 0
            print(f"  🌡️ Temp slightly high ({current_temp:.1f}K) - activating one chiller")
        else:
            # Good temperature - minimal cooling
            chi01 = 0
            chi02 = 1  # Keep one for stability
            print(f"  ❄️ Temp OK ({current_temp:.1f}K) - minimal cooling")

        # Rule 3: Pump speed control (secondary objective)
        # Higher speeds when chillers are running
        if chi01 and chi02:
            chwp_speed = 900  # High speed for both chillers
            cdwp_speed = 950
        elif chi01 or chi02:
            chwp_speed = 800  # Medium speed for one chiller
            cdwp_speed = 850
        else:
            chwp_speed = 700  # Low speed for circulation
            cdwp_speed = 750

        # Rule 4: Cooling tower control (efficiency optimization)
        # Open towers when chillers are active
        ct_valves = 1 if (chi01 or chi02) else 0
        fan_speed = 0.8 if (chi01 and chi02) else 0.6

        # Construct control action (use minimal controls based on what worked in previous tests)
        control_action = {
            'CHI01': chi01,
            'CHI02': chi02,
            'CHWP01_rpm': chwp_speed,
            'CHWP02_rpm': chwp_speed,
            'U_CT1': ct_valves,
            'U_CT2': ct_valves
        }

        return control_action

    def run_control_loop(self, num_steps=5):
        """
        Run the control loop for specified number of steps.

        This demonstrates the MPC-ready infrastructure:
        1. State feedback ✅
        2. Control computation ✅
        3. Control application ✅
        4. System response ✅
        """

        print("🚀 Starting Rule-Based Control Loop (MPC Infrastructure Demo)")
        print("=" * 60)

        # Initialize system
        print("\n📋 Step 0: System Initialization")
        response = requests.put(f"{BASE_URL}/initialize", json={"start_time": 0}, timeout=30)

        if response.status_code != 200:
            print(f"❌ Initialization failed: {response.text}")
            return False

        print("✅ System initialized successfully")

        # Control loop
        for step in range(1, num_steps + 1):
            print(f"\n🔄 Step {step}: Control Loop Iteration")
            print("-" * 40)

            # Get current state (MPC: state estimation)
            print("📊 Getting current system state...")

            # Compute control action (MPC: optimization)
            print("🧠 Computing control action...")
            if step == 1:
                # First step - use initialization state
                init_result = response.json()['payload']
                control_action = self.compute_control_action(init_result)
                current_state = init_result
            else:
                # Use state from previous advance
                control_action = self.compute_control_action(current_state)

            # Apply control action (MPC: control application)
            print("⚡ Applying control action...")
            print(f"   Controls: CHI01={control_action['CHI01']}, CHI02={control_action['CHI02']}")
            print(f"   Pump speeds: {control_action['CHWP01_rpm']} rpm")

            advance_response = requests.post(f"{BASE_URL}/advance",
                                           json=control_action,
                                           timeout=120)

            if advance_response.status_code != 200:
                print(f"❌ Control application failed: {advance_response.text}")
                return False

            # Get system response (MPC: prediction validation)
            result = advance_response.json()
            current_state = result['payload']

            # Log results
            temp = current_state.get('Tchw_supply', 0)
            chiller_power = current_state.get('P_Chillers_sum', 0)
            pump_power = current_state.get('P_CHWPs_sum', 0)

            print(f"📈 System Response:")
            print(f"   Temperature: {temp:.2f} K (target: {self.target_temp:.1f} K)")
            print(f"   Chiller Power: {chiller_power:.0f} W")
            print(f"   Pump Power: {pump_power:.0f} W")

            # Store for analysis
            self.control_history.append(control_action.copy())
            self.state_history.append({
                'step': step,
                'time': current_state.get('time', step * 300),
                'temperature': temp,
                'chiller_power': chiller_power,
                'pump_power': pump_power,
                'chi01': control_action['CHI01'],
                'chi02': control_action['CHI02']
            })

            # Brief delay (in real MPC, this would be the control interval)
            time.sleep(1)

        print("\n🎯 Control Loop Completed Successfully!")
        print("=" * 60)

        return True

    def analyze_results(self):
        """Analyze control performance and create visualization."""

        if not self.state_history:
            print("❌ No data to analyze")
            return

        print("\n📊 Performance Analysis")
        print("-" * 30)

        # Calculate metrics
        temps = [s['temperature'] for s in self.state_history]
        chiller_powers = [s['chiller_power'] for s in self.state_history]
        steps = [s['step'] for s in self.state_history]

        avg_temp = np.mean(temps)
        temp_std = np.std(temps)
        total_energy = sum(chiller_powers)

        print(f"Average Temperature: {avg_temp:.2f} K")
        print(f"Temperature Std Dev: {temp_std:.3f} K")
        print(f"Total Chiller Energy: {total_energy:.0f} W·steps")
        print(f"Control Variations: {len(set(tuple(sorted(h.items())) for h in self.control_history))}")

        # Print detailed step-by-step results
        print(f"\n📋 Step-by-Step Control Results:")
        for i, state in enumerate(self.state_history):
            control = self.control_history[i]
            print(f"  Step {state['step']}: T={state['temperature']:.2f}K, "
                  f"CHI01={control['CHI01']}, CHI02={control['CHI02']}, "
                  f"Pump={control['CHWP01_rpm']}rpm, Power={state['chiller_power']:.0f}W")

        # Create visualization if matplotlib available
        if not HAS_MATPLOTLIB:
            print("\n⚠️ Skipping visualization - matplotlib not available")
            print("   Install with: pip install matplotlib")
            return

        plt.figure(figsize=(12, 8))

        # Temperature control
        plt.subplot(2, 2, 1)
        plt.plot(steps, temps, 'b-o', linewidth=2, markersize=6)
        plt.axhline(y=self.target_temp, color='r', linestyle='--', label=f'Target ({self.target_temp}K)')
        plt.fill_between(steps,
                        self.target_temp - self.temp_tolerance,
                        self.target_temp + self.temp_tolerance,
                        alpha=0.2, color='green', label='Tolerance')
        plt.xlabel('Control Step')
        plt.ylabel('Temperature (K)')
        plt.title('Temperature Control Performance')
        plt.legend()
        plt.grid(True, alpha=0.3)

        # Power consumption
        plt.subplot(2, 2, 2)
        plt.bar(steps, chiller_powers, alpha=0.7, color='orange')
        plt.xlabel('Control Step')
        plt.ylabel('Chiller Power (W)')
        plt.title('Energy Consumption')
        plt.grid(True, alpha=0.3)

        # Chiller status
        plt.subplot(2, 2, 3)
        chi01_status = [s['chi01'] for s in self.state_history]
        chi02_status = [s['chi02'] for s in self.state_history]

        plt.plot(steps, chi01_status, 's-', label='CHI01', linewidth=2, markersize=8)
        plt.plot(steps, chi02_status, '^-', label='CHI02', linewidth=2, markersize=8)
        plt.xlabel('Control Step')
        plt.ylabel('Chiller Status (0=OFF, 1=ON)')
        plt.title('Chiller Control Actions')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.ylim(-0.1, 1.1)

        # Control summary
        plt.subplot(2, 2, 4)
        plt.text(0.1, 0.8, f"MPC Infrastructure Validation", fontsize=14, fontweight='bold')
        plt.text(0.1, 0.7, f"✅ State Feedback: Working", fontsize=12)
        plt.text(0.1, 0.6, f"✅ Control Application: Working", fontsize=12)
        plt.text(0.1, 0.5, f"✅ System Response: Working", fontsize=12)
        plt.text(0.1, 0.4, f"✅ Multi-step Control: Working", fontsize=12)
        plt.text(0.1, 0.3, f"📊 Avg Temp: {avg_temp:.2f}K", fontsize=12)
        plt.text(0.1, 0.2, f"⚡ Total Energy: {total_energy:.0f}W", fontsize=12)
        plt.text(0.1, 0.1, f"🎯 Ready for MPC Implementation!", fontsize=12, color='green', fontweight='bold')
        plt.xlim(0, 1)
        plt.ylim(0, 1)
        plt.axis('off')

        plt.tight_layout()
        plt.savefig('toy_mpc_validation.png', dpi=150, bbox_inches='tight')
        print(f"\n📊 Visualization saved to 'toy_mpc_validation.png'")

def main():
    """Main execution function."""

    print("🏭 Toy MPC Infrastructure Validation")
    print("====================================")
    print()
    print("This example demonstrates that the AlphaDataCenterCooling system")
    print("supports the fundamental workflow required for MPC implementation:")
    print()
    print("1. 📋 System Initialization")
    print("2. 🔄 Iterative Control Loop:")
    print("   - 📊 State Estimation (get current system state)")
    print("   - 🧠 Control Computation (optimization → rule-based)")
    print("   - ⚡ Control Application (apply via advance endpoint)")
    print("   - 📈 System Response (observe results)")
    print("3. 📊 Performance Analysis")
    print()

    # Create controller
    controller = ToyRuleBasedController()

    # Check API availability
    try:
        response = requests.get(f"{BASE_URL}/version", timeout=5)
        if response.status_code != 200:
            print("❌ API not available. Make sure the container is running.")
            return False
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to API. Make sure the container is running.")
        return False

    print("✅ API connection confirmed")

    # Run control experiment
    success = controller.run_control_loop(num_steps=4)

    if success:
        controller.analyze_results()

        print("\n🎉 SUCCESS: MPC Infrastructure Validated!")
        print("=" * 50)
        print("✅ All MPC workflow components working correctly")
        print("✅ System ready for actual MPC implementation")
        print("✅ Advance endpoint supports control applications")
        print()
        print("Next steps for real MPC:")
        print("1. 🔬 Develop system identification models")
        print("2. 🎯 Define cost function and constraints")
        print("3. ⚡ Implement optimization solver (e.g., CVX, Gurobi)")
        print("4. 🔄 Replace rule-based logic with MPC optimization")

        return True
    else:
        print("\n❌ FAILED: Issues with control infrastructure")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)