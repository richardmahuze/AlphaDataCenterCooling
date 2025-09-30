# Understanding the Comprehensive REST API Test

This document explains what `test_rest_api_full.py` does, in plain language.

---

## Nomenclature (Key Terms Defined)

### Data Center Cooling Components

- **Data Center**: A building full of computers/servers that generate heat and need cooling
- **Chiller (CHI)**: A large refrigeration machine that cools water (like a giant air conditioner for water)
- **Cooling Tower (CT)**: A structure that uses outdoor air to cool hot water from the chillers
- **Condenser Water Pump (CDWP)**: Pumps that move hot water from chillers to cooling towers
- **Chilled Water Pump (CHWP)**: Pumps that move cold water from chillers to the data center
- **Fan**: Moves air through cooling towers to help cool the water faster

### Technical Terms

- **FMU (Functional Mock-up Unit)**: A computer file that contains a mathematical model of how the cooling system works
- **PyFMI**: Python software that runs FMU simulations
- **Simulink**: MATLAB software for creating simulations (industry standard)
- **MLP (Multi-Layer Perceptron)**: A type of artificial intelligence (neural network) used to calculate pump pressure requirements
- **REST API**: A way for computer programs to talk to each other over the internet (like a waiter taking orders)
- **Simulation**: Using a computer to mimic real-world behavior without actually running the physical equipment

### Power Measurements

- **P_CDWPs_sum**: Total electrical power consumed by all condenser water pumps (measured in Watts or kW)
- **P_CHWPs_sum**: Total electrical power consumed by all chilled water pumps (measured in Watts or kW)
- **P_Chillers_sum**: Total electrical power consumed by all chillers (measured in Watts or kW)
- **P_CTfans_sum**: Total electrical power consumed by all cooling tower fans (measured in Watts or kW)
- **kW (Kilowatt)**: 1000 Watts - a measure of power consumption (like the wattage of a light bulb, but much bigger)

### Time Terms

- **Time Step**: How often the system checks and adjusts itself (300 seconds = 5 minutes in this test)
- **Episode**: A complete run of the simulation from start to finish

---

## What Does This Script Do?

`test_rest_api_full.py` is a **validation tool** that tests whether a virtual (computer-simulated) data center cooling system works correctly. Think of it as a "quality check" before using the simulation for real optimization work.

**The Simple Version:**
1. Connects to a virtual cooling system running in Docker
2. Feeds it 2000 control commands (like turning pumps on/off, adjusting speeds)
3. Records how much power the pumps use
4. Compares these results against two trusted references
5. Creates graphs showing if the simulation matches reality

---

## Why Three Scenarios? (Ground Truth vs. Simulink vs. PyFMI+MLP)

When testing a new simulation, we need to know: **"Does it give the right answers?"**

We compare three different sources of data:

### 1. Ground Truth (Reality Baseline)
- **What it is**: Real-world measurements from an actual data center or high-fidelity reference data
- **Why it matters**: This is what actually happened in the real world
- **Think of it as**: The answer key in the back of a textbook

### 2. Simulink (Industry Standard Simulation)
- **What it is**: A simulation created using MATLAB/Simulink (trusted industry tool)
- **Why it matters**: Simulink is a well-established, thoroughly tested simulation platform
- **Think of it as**: A second opinion from a highly respected expert
- **Purpose**: If our new simulation matches Simulink, we know the physics are correct

### 3. PyFMI+MLP (Our New Approach)
- **What it is**: Our new simulation combining:
  - PyFMI (runs the cooling system model)
  - MLP neural network (calculates pump pressure requirements)
- **Why it matters**: This is what we're testing - does our faster/newer method work correctly?
- **Think of it as**: The student's answer that needs to be graded

### Why Compare All Three?

**Analogy**: Imagine you created a new calculator app. Before trusting it with important calculations, you would:
1. Test it against real-world problems with known answers (Ground Truth)
2. Compare it to a scientific calculator everyone trusts (Simulink)
3. See if your new app (PyFMI+MLP) gives the same results

If all three agree, we can confidently use the new simulation for research and optimization.

---

## Inputs (What Goes Into the Script)

### 1. Control Actions File
- **File**: `RealWorld_Actions_Observations.csv`
- **What it contains**: 100,330 rows of control commands (like a recipe book)
- **Each row specifies**:
  - Which chillers to turn on/off
  - How fast to run each pump (RPM = rotations per minute)
  - Which valves to open/close
  - What temperature to target
  - Fan speeds for cooling towers
- **Size**: 100 different control parameters per time step

### 2. Configuration Settings
- **URL**: `http://127.0.0.1:5000` (address of the virtual cooling system)
- **Step size**: 300 seconds (5 minutes per control decision)
- **Number of steps**: 2000 (total test duration)

### 3. Reference Data Files
- **Ground Truth**: `RealWorld_Actions_Observations.csv` (contains both actions and observed power consumption)
- **Simulink Output**: `Pumps_P_Simulink.csv` (power predictions from MATLAB/Simulink)

---

## Process (What Happens Step-by-Step)

### Phase 1: Connection and Discovery (Lines 76-115)

**Step 1**: Check if the virtual data center is running
- Like knocking on a door to see if anyone's home
- Sends a request to the API: "Are you there?"

**Step 2**: Query what the system can do
- Asks: "What controls do you accept?" → Gets list of 100 control inputs
- Asks: "What can you measure?" → Gets list of 86 sensors/measurements
- Asks: "What's your name and version?" → Confirms correct system

**Step 3**: Save all this information to a file
- **Output**: `api_metadata.txt` (documentation of what the system can do)

### Phase 2: Simulation Setup (Lines 117-163)

**Step 4**: Configure the simulation
- Sets time step to 300 seconds (how often to make decisions)
- Initializes system to time = 0 (like pressing reset)

**Step 5**: Load the control commands
- Reads `RealWorld_Actions_Observations.csv`
- Extracts 100 control parameters for each time step
- Validates all required columns are present

**Step 6**: Check initial state
- Records starting power consumption:
  - Condenser water pumps: ~26 kW
  - Chilled water pumps: ~23 kW
  - Chillers: 0 kW (off during initialization)
  - Cooling tower fans: ~28 kW

### Phase 3: Running the Simulation (Lines 165-203)

**Step 7**: Loop through 2000 time steps (5 minutes each)
- **Duration**: 2000 × 300s = 600,000 seconds = 166.7 hours = ~7 days of simulated time
- **Real-time execution**: Takes ~3-4 minutes on a typical computer

For each time step:
1. Read control commands from CSV (row i)
2. Send commands to virtual cooling system via API
3. System simulates what would happen over next 5 minutes
4. Receive back power consumption measurements
5. Record: `P_CDWPs_sum` and `P_CHWPs_sum`
6. Move to next time step

**Progress bar**: Shows which step you're on (e.g., "Progress: 1234/2000")

**Step 8**: Save simulation results
- **Output**: `Pumps_P_Pyfmi_mlp_restapi.csv`
- Contains 3 columns:
  - `time`: When the measurement was taken (0, 300, 600, ... seconds)
  - `P_CDWPs_sum`: Condenser pump power at that moment
  - `P_CHWPs_sum`: Chilled water pump power at that moment

**Step 9**: Calculate and print statistics
- Mean (average) power consumption
- Minimum power observed
- Maximum power observed

### Phase 4: Comparison and Visualization (Lines 205-277)

**Step 10**: Load all three datasets
- Ground Truth power measurements
- Simulink simulation predictions
- PyFMI+MLP simulation results (what we just generated)

**Step 11**: Create comparison plot for condenser water pumps
- **X-axis**: Time step (0 to 2000)
- **Y-axis**: Power consumption in kW
- **Three lines**:
  - Blue = Ground Truth (reality)
  - Orange = Simulink (industry standard)
  - Green = PyFMI+MLP (our new method)
- **Output**: `P_CDWPs_comparison.png`

**Step 12**: Create comparison plot for chilled water pumps
- Same format as Step 11
- Shows different component (CHWP instead of CDWP)
- **Output**: `P_CHWPs_comparison.png`

### Phase 5: Logging (Throughout entire execution)

**Step 13**: Record everything to log file
- All console output (what you see on screen)
- Timestamps and progress updates
- Error messages (if any)
- Final statistics
- **Output**: `test_results.txt`

---

## Outputs (What Files Are Created)

### 1. `api_metadata.txt`
- **Size**: ~10-20 KB
- **Contents**: JSON-formatted documentation of the virtual data center
- **Use case**: Reference for understanding what the system can do
- **Example excerpt**:
  ```json
  {
    "P_CDWPs_sum": {
      "Description": "The sum of condenser water pump power [W]"
    }
  }
  ```

### 2. `Pumps_P_Pyfmi_mlp_restapi.csv`
- **Size**: 2000 rows × 3 columns
- **Contents**: Time-series power consumption data
- **Columns**:
  - `time`: Simulation time in seconds (0, 300, 600, ...)
  - `P_CDWPs_sum`: Condenser water pump power in Watts
  - `P_CHWPs_sum`: Chilled water pump power in Watts
- **Use case**: Raw data for further analysis, plotting, or machine learning

### 3. `test_results.txt`
- **Size**: ~5-10 KB
- **Contents**: Complete log of test execution
- **Includes**:
  - Service health check results
  - Number of inputs/measurements found
  - Progress updates
  - Summary statistics
  - File paths of outputs
- **Use case**: Debugging, verification, audit trail

### 4. `P_CDWPs_comparison.png`
- **Size**: ~500 KB (high-resolution image)
- **Contents**: Line graph comparing condenser water pump power across three scenarios
- **What to look for**:
  - Do all three lines follow similar patterns?
  - Are there large deviations between PyFMI+MLP and the references?
  - Spikes = moments when pump configuration changed

### 5. `P_CHWPs_comparison.png`
- **Size**: ~500 KB (high-resolution image)
- **Contents**: Line graph comparing chilled water pump power across three scenarios
- **What to look for**:
  - Same analysis as CDWP plot
  - Typically shows more variability (chilled water responds to data center load)

---

## How to Read the Results

### Understanding the Statistics

When the script finishes, it prints summary statistics:

```
P_CDWPs_sum statistics:
  Mean: 26204.06 W  ← Average power consumption
  Min:  19096.01 W  ← Lowest power (light load)
  Max:  27710.99 W  ← Highest power (peak load)
```

**What's normal?**
- Condenser pumps: 15-30 kW typical for 6-pump system
- Chilled water pumps: 15-50 kW (varies more with data center load)
- Large range (min to max) = good, shows system adapts to changing conditions

### Understanding the Plots

#### Good Result (What We Want to See):
- All three lines (Truth, Simulink, PyFMI+MLP) follow the same general pattern
- Small differences are okay (no simulation is perfect)
- PyFMI+MLP captures major events (spikes, drops, trends)

#### Problematic Result (Red Flags):
- PyFMI+MLP line diverges significantly from Truth/Simulink
- Missing major spikes or drops
- Unrealistic values (e.g., negative power, or 1000 kW for a single pump)

#### In Your Case:
✅ **Condenser Water Pumps**: Excellent agreement, PyFMI+MLP tracks Truth/Simulink closely
✅ **Chilled Water Pumps**: Very good agreement, captures all major dynamics including the 48 kW spike at step ~600

### What Success Means

If the plots show good agreement (as yours do), it validates:
1. The FMU model is physically accurate
2. The MLP neural network calculates pump pressures correctly
3. The PyFMI simulation is stable over long time horizons
4. The virtual data center is ready for optimization research

---

## Common Questions

### Q: Why only test pump power, not chillers?
**A**: This is a **subsystem validation test**. Pumps are tested first because:
- They're simpler components (easier to validate)
- Pump models are critical for pressure calculations (MLP)
- Once pumps work correctly, we can test more complex components (chillers, fans)

### Q: Why 2000 steps?
**A**: Balances thoroughness with speed:
- Too few steps (e.g., 20) might miss rare events
- Too many steps (e.g., 100,000) takes too long to run
- 2000 steps = ~7 simulated days = captures weekly patterns

### Q: What if my plots don't match?
**A**: Check:
1. Is the Docker service running? (`docker-compose up`)
2. Are you using the correct CSV file? (RealWorld_Actions_Observations.csv)
3. Any error messages in `test_results.txt`?
4. Try running the script with fewer steps first (--steps 100)

### Q: Can I test other components?
**A**: Yes! Modify the script to collect additional measurements:
- Change lines 135-136 to include `P_Chillers_sum`, `P_CTfans_sum`
- Adjust the plotting code accordingly
- See `api_metadata.txt` for full list of available measurements

---

## Technical Details (For Advanced Users)

### API Endpoints Used
- `GET /name`: Retrieve test case name
- `GET /version`: Retrieve version number
- `GET /inputs`: List all control inputs
- `GET /measurements`: List all sensors
- `PUT /step`: Set time step size
- `PUT /initialize`: Reset simulation to start time
- `POST /advance`: Execute one simulation step with control inputs

### Data Flow
```
CSV File → Python Script → REST API → Docker Container → FMU Simulation
                ↓                                              ↓
         Control Commands                           Physics Calculations
                                                              ↓
         Results ← JSON Response ← REST API ← PyFMI + MLP Model
                ↓
         CSV + Plots
```

### Performance Characteristics
- **Simulation speed**: ~9.5 iterations/second (with progress bar)
- **API latency**: ~100-120ms per request (local Docker)
- **Memory usage**: ~50-100 MB for 2000 steps
- **Disk usage**: ~3 MB total (CSVs + PNGs + logs)

---

## Summary

`test_rest_api_full.py` is a comprehensive validation tool that:
1. Connects to a virtual data center cooling system
2. Runs a 7-day simulation with realistic control strategies
3. Measures pump power consumption
4. Compares results against Ground Truth and Simulink references
5. Generates visual comparisons and statistical summaries

**Success criteria**: PyFMI+MLP simulation should closely match both Ground Truth (reality) and Simulink (industry standard).

**Your results**: ✅ Validation successful - simulation is accurate and ready for research use.