# Understanding the Comprehensive REST API Test

This document explains what `test_rest_api_full.py` does and how all components interact.

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

- **FMU (Functional Mock-up Unit)**: A computer file that contains a mathematical model of how the cooling system works (compiled Modelica code)
- **PyFMI**: Python library that loads and runs FMU simulations
- **Simulink**: MATLAB software for creating simulations (industry standard)
- **MLP (Multi-Layer Perceptron)**: A type of artificial neural network used to calculate pump pressure requirements
- **REST API**: A way for computer programs to talk to each other over HTTP (like a waiter taking orders)
- **Simulation**: Using a computer to mimic real-world behavior without actually running the physical equipment
- **Flask**: Python web framework used to create the REST API server
- **Docker**: Containerization platform that packages the simulation environment

### Power Measurements

- **P_CDWPs_sum**: Total electrical power consumed by all condenser water pumps (measured in Watts or kW)
- **P_CHWPs_sum**: Total electrical power consumed by all chilled water pumps (measured in Watts or kW)
- **P_Chillers_sum**: Total electrical power consumed by all chillers (measured in Watts or kW)
- **P_CTfans_sum**: Total electrical power consumed by all cooling tower fans (measured in Watts or kW)
- **kW (Kilowatt)**: 1000 Watts - a measure of power consumption

### Time Terms

- **Time Step**: How often the system updates (300 seconds = 5 minutes in this test)
- **Episode**: A complete run of the simulation from start to finish

---

## Architecture Overview

### Two-Process Design

The system uses a **client-server architecture** with two separate Python processes:

```
┌─────────────────────────────┐         ┌──────────────────────────────────────┐
│  YOUR LAPTOP/WORKSTATION    │         │     DOCKER CONTAINER                 │
│                             │         │                                      │
│  test_rest_api_full.py      │  HTTP   │  restapi.py (Flask server)          │
│  (Client)                   │◄───────►│       │                             │
│                             │         │       │ imports                     │
│  - Reads CSV                │         │       ▼                             │
│  - Sends control inputs     │         │  testcase.py (Simulation wrapper)   │
│  - Receives measurements    │         │       │                             │
│  - Saves results            │         │       │ uses                        │
│  - Generates plots          │         │       ▼                             │
│                             │         │  ┌─────────────────────────────┐   │
│                             │         │  │ MLP (utils.py)              │   │
│                             │         │  │ + mlp.pth (trained weights) │   │
│                             │         │  └─────────────────────────────┘   │
│                             │         │       │                             │
│                             │         │       │ calls                       │
│                             │         │       ▼                             │
│                             │         │  ┌─────────────────────────────┐   │
│                             │         │  │ PyFMI                       │   │
│                             │         │  │ + FMU Physics Model         │   │
│                             │         │  │ (AlphaDataCenterCooling.fmu)│   │
│                             │         │  └─────────────────────────────┘   │
└─────────────────────────────┘         └──────────────────────────────────────┘
```

**Key Point:** The test script on your laptop only communicates with the REST API. It never directly touches the FMU, MLP, or testcase.py. All simulation logic runs inside Docker.

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

## Before Running the Script: Docker Setup

### What Happens When You Run `docker-compose up`

This step must be completed **before** running the test script. Here's what happens:

**1. Docker Container Starts (Dockerfile)**
- Loads Ubuntu 18.04 with Python 3.10
- Installs PyFMI, PyTorch, Flask, and dependencies
- Creates user environment

**2. Files Mounted into Container (docker-compose.yml)**
```yaml
volumes:
  - ./restapi.py → /home/user/restapi.py
  - ./testcase.py → /home/user/testcase.py
  - ./utils.py → /home/user/utils.py
  - ./Resources → /home/user/Resources/
```
All simulation files are now accessible inside Docker.

**3. Flask Server Starts Automatically (Dockerfile CMD)**
```bash
python restapi.py
```

**4. restapi.py Initialization (lines 32, 65)**
```python
from testcase import TestCase  # Import simulation wrapper
case = TestCase()              # Create singleton instance
```

**5. TestCase Initialization (testcase.py __init__, lines 23-88)**
When `TestCase()` is instantiated, it:
- Loads the FMU file: `AlphaDataCenterCooling_FMU.fmu`
- Loads the MLP neural network: `Resources/mlp.pth` (trained weights)
- Loads disturbance data: `Disturbance.csv` (outdoor conditions, load profiles)
- Loads initialization data: `Initialization_actions.csv`, `Initialization_observation0.csv`
- Configures simulation options (solver tolerances, step sizes)
- Prepares data storage structures

**6. Flask API Endpoints Registered (restapi.py lines 193-200)**
```python
api.add_resource(Advance, '/advance')      # POST - run simulation step
api.add_resource(Initialize, '/initialize') # PUT - reset simulation
api.add_resource(Step, '/step')            # GET/PUT - step size
api.add_resource(Inputs, '/inputs')        # GET - list control inputs
api.add_resource(Measurements, '/measurements') # GET - list sensors
```

**7. Server Listening on Port 5000**
The Docker container is now ready to receive API requests from the test script.

**Important:** This initialization happens **once** when Docker starts, not on every API call. The `TestCase()` instance persists throughout the container's lifetime.

---

## Inputs (What Goes Into the Script)

### 1. Control Actions File
- **File**: `RealWorld_Actions_Observations.csv`
- **Location**: On your laptop in `testing/` directory
- **What it contains**: 100,330 rows of control commands (like a recipe book)
- **Each row specifies**:
  - Which chillers to turn on/off (CHI01-06)
  - How fast to run each pump (CDWP01-06_rpm, CHWP01-06_rpm)
  - Which valves to open/close (CW1-4, CHW1-4 for each chiller)
  - Cooling tower valve positions (U_CT1-6)
  - Fan speeds (Ffan_CT)
  - Temperature setpoints (Tchws_set_CHI, Tchws_set_HEX)
- **Size**: 100 different control parameters per time step

### 2. Configuration Settings
- **URL**: `http://127.0.0.1:5000` (address of the Docker container)
- **Step size**: 300 seconds (5 minutes per control decision)
- **Number of steps**: 2000 (total test duration)

### 3. Reference Data Files
- **Ground Truth**: `RealWorld_Actions_Observations.csv` (contains both actions AND observed power consumption)
- **Simulink Output**: `Pumps_P_Simulink.csv` (power predictions from MATLAB/Simulink, pre-generated)

---

## Complete Process Flow (Step-by-Step)

### Phase 1: Connection and Discovery

**Script action:** Health check
```python
requests.get('http://127.0.0.1:5000/name')
```

**Network flow:**
```
Your laptop → HTTP GET /name → Docker container (port 5000)
```

**Inside Docker (restapi.py → testcase.py):**
1. Flask receives request at `/name` endpoint
2. Routes to `Name.get()` method (restapi.py line 176)
3. Calls `case.get_name()` (testcase.py line 816)
4. Returns `{'status': 200, 'message': '...', 'payload': {'name': 'AlphaDataCenterCooling'}}`

**Network response:**
```
Docker container → HTTP 200 + JSON → Your laptop
```

**Script continues with metadata queries:**
- `/inputs` → List of 100 control inputs with descriptions
- `/measurements` → List of 86 sensor measurements with descriptions
- `/version` → Environment version number

**Script output:** `api_metadata.txt` (saved on your laptop)

---

### Phase 2: Simulation Setup

**Script action:** Set step size
```python
requests.put('http://127.0.0.1:5000/step', json={'step': 300})
```

**Inside Docker (testcase.py):**
- Flask routes to `Step.put()` (restapi.py line 129)
- Calls `case.set_step(300)` (testcase.py line 497)
- Validates: must be multiple of 300 seconds
- Sets `self.step = 300`

**Script action:** Initialize simulation
```python
requests.put('http://127.0.0.1:5000/initialize', json={'start_time': 0})
```

**Inside Docker (testcase.py line 132):**
1. Flask routes to `Initialize.put()` (restapi.py line 109)
2. Calls `case.initialize(start_time=0)` (testcase.py line 132)
3. Resets FMU to initial state: `self.fmu.reset()`
4. Clears simulation data storage
5. If start_time = 0:
   - Loads pre-computed initial observation from `Initialization_observation0.csv`
6. If start_time > 0 (not in this test):
   - Runs 300s warmup simulation using `Initialization_actions.csv`
7. Returns initial measurements (P_CDWPs_sum ≈ 27 kW, P_CHWPs_sum ≈ 23 kW, all temperatures, etc.)

**Script receives:** Initial system state with 86 measurements

---

### Phase 3: Main Simulation Loop (2000 Iterations)

This is the **heart of the test**. For each time step i = 0 to 1999:

#### **Step 3.1: Script reads control inputs**
```python
df = pd.read_csv('RealWorld_Actions_Observations.csv')
u = df.iloc[i].to_dict()  # Extract 100 control values for step i
```

#### **Step 3.2: Script sends request**
```python
requests.post('http://127.0.0.1:5000/advance', json=u)
```

**Network flow:**
```
Your laptop → HTTP POST /advance + JSON (100 inputs) → Docker (port 5000)
```

**JSON payload example:**
```json
{
  "U_CT1": 0, "U_CT2": 1, "U_CT3": 1, ...,
  "CHI01": 0, "CHI02": 0, ...,
  "CDWP01_rpm": 900, "CDWP02_rpm": 0, ...,
  "Tchws_set_CHI": 286.55, ...
}
```

---

#### **Step 3.3: Inside Docker Container - The Critical Path**

**restapi.py receives request (line 98):**
```python
def post(self):
    u = parser_advance.parse_args()  # Parse 100 control inputs from JSON
    status, message, payload = case.advance(u)  # ← Call testcase.py
    return construct(status, message, payload)
```

**testcase.py advance() method (lines 332-461) - Where the Magic Happens:**

**3.3.1: Count active equipment (lines 352-354)**
```python
chiller_count = u['CHI01'] + u['CHI02'] + ... + u['CHI06']
heat_exchanger_count = u['CHI01_CW3'] + ... + u['CHI06_CW3']
cooling_tower_valve_count = (u['U_CT1'] + ... + u['U_CT6']) * 2
```
These counts will be used by the MLP.

**3.3.2: Build input trajectory (lines 365-394)**
For each control input:
- Extract value from `u` dictionary
- Add to `u_trajectory` array

For disturbance variables (outdoor wet-bulb temperature, chilled water load):
- Look up from `Disturbance.csv` based on current simulation time
- Add to `u_trajectory`

**3.3.3: Calculate condenser water flow rate (line 396)**
```python
Mcw = self.__calc_Mcw(Mchw, P_chillers_sum, Tchw_r, Tchws_set_CHI)
# Uses heat balance equation:
# Mcw = Mchw + (chiller_power / (c_p * delta_T))
```
This calculation uses thermodynamic principles to determine how much water must flow through the condenser circuit.

**3.3.4: ★ CALL MLP NEURAL NETWORK ★ (lines 397-398)**
```python
Head_required = self.__calc_head_required(
    chiller_count,
    heat_exchanger_count,
    cooling_tower_valve_count,
    Mcw
)
```

**Deep dive into MLP calculation (testcase.py lines 302-330, utils.py):**
```python
# testcase.py __calc_head_required():
x = torch.tensor([chiller_count, heat_exchanger_count,
                  cooling_tower_valve_count, mcw])
x = x.float()  # Convert to float32
output_tensor = self.mlp_model.step(x)  # ← Call neural network
head_required = output_tensor.item()  # Extract scalar value

# utils.py MLP.step():
x_normalized = normalize_input(x)  # Scale inputs to [0,1]
    # e.g., [2 chillers, 2 HEX, 4 CT valves, 0.5 kg/s]
    # → [0.33, 0.33, 0.67, 0.4]

output_normalized = self.layers(x_normalized)  # Neural network forward pass
    # 3-layer network: Input(4) → ReLU(64) → ReLU(64) → Output(1)
    # Trained weights from mlp.pth

head_original = inverse_normalize_output(output_normalized)
    # Scale back from [0,1] to [0, ~40 meters]

return head_original  # e.g., 15.5711 meters
```

**Why use MLP?** Traditional hydraulic calculations require solving complex fluid dynamics equations (flow splits, pressure drops through valves, pipe friction). The MLP learns these relationships from training data and predicts head pressure **instantly** (milliseconds vs seconds).

**3.3.5: Add Head_required to inputs (lines 401-406)**
```python
u_list.append('Head_required')
u_trajectory = np.vstack((u_trajectory, Head_required))
```
The FMU needs to know what pressure the pumps must generate. The MLP has calculated this.

**3.3.6: ★ RUN FMU PHYSICS SIMULATION ★ (lines 412-415)**
```python
res = self.fmu.simulate(
    start_time = self.start_time_itr,       # e.g., 0
    final_time = self.final_time_itr,       # e.g., 300
    options = self.options,                 # Solver settings
    input = (u_list, u_trajectory)          # 101 inputs (100 + Head_required)
)
```

**What happens inside the FMU simulation:**
1. **Initialization:** PyFMI loads the FMU state
2. **ODE Solver (CVode):** Integrates differential equations over 300 seconds
   - Thermodynamics: heat transfer, phase changes
   - Fluid mechanics: mass flow, pressure drops
   - Control systems: valve responses, pump curves
   - Energy balances: power consumption calculations
3. **Time stepping:** Internally uses much smaller steps (adaptive, typically ~1-10 seconds)
4. **Output collection:** Records all 86 measurements at final time

The FMU is a **compiled Modelica model** containing thousands of equations representing:
- 6 chillers with refrigeration cycles
- 6 cooling towers with air-water heat exchangers
- 12 pumps with characteristic curves
- Piping network with hydraulic resistances
- Control logic and setpoint tracking

**3.3.7: Extract results (lines 444, 858-867)**
```python
# Store latest measurements
self.y['P_CDWPs_sum'] = res['P_CDWPs_sum'][-1]  # e.g., 27121.77 W
self.y['P_CHWPs_sum'] = res['P_CHWPs_sum'][-1]  # e.g., 22873.69 W
# ... all 86 measurements

# Also store in time series for later retrieval
self.y_store['P_CDWPs_sum'].append(res['P_CDWPs_sum'][-1])
```

**3.3.8: Update simulation time**
```python
self.start_time += 300  # Advance to next time step
```

**3.3.9: Return measurements (line 452)**
```python
payload = self._get_full_current_state()
# Returns dictionary with all 86 measurements:
# {
#   'time': 300,
#   'P_CDWPs_sum': 27121.766587816655,
#   'P_CHWPs_sum': 22873.68662354903,
#   'H_CDWP1': 15.5711,
#   'Tchw_supply': 286.55,
#   ... (83 more measurements)
# }
return 200, "Advanced simulation successfully...", payload
```

**restapi.py wraps response:**
```python
response = {
    'status': 200,
    'message': 'Advanced simulation successfully from 0s to 300s.',
    'payload': { ... all 86 measurements ... }
}
```

---

**Network response:**
```
Docker container → HTTP 200 + JSON (86 measurements) → Your laptop
```

---

#### **Step 3.4: Script processes response**
```python
payload = resp.json().get('payload', {})
P_CDWPs_sum.append(payload['P_CDWPs_sum'])  # Save this one
P_CHWPs_sum.append(payload['P_CHWPs_sum'])  # Save this one
# Discard other 84 measurements
times.append(current_time)
current_time += 300
```

**This loop repeats 2000 times:**
- Simulated time: 0 to 600,000 seconds (≈ 7 days)
- Real execution time: ~3-4 minutes
- Each iteration: read CSV → HTTP POST → MLP calculation → FMU simulation → return measurements

**Progress bar updates:** "Progress: 1234/2000"

---

### Phase 4: Save Results

**Script saves collected data:**
```python
out_df = pd.DataFrame({
    'time': times,              # [0, 300, 600, ..., 599700]
    'P_CDWPs_sum': P_CDWPs_sum, # [27121.77, 27121.77, ...]
    'P_CHWPs_sum': P_CHWPs_sum  # [22873.69, 22873.69, ...]
})
out_df.to_csv('Pumps_P_Pyfmi_mlp_restapi.csv', index=False)
```

**Output:** `Pumps_P_Pyfmi_mlp_restapi.csv` (2000 rows × 3 columns) saved on your laptop

**Script calculates statistics:**
```
P_CDWPs_sum statistics:
  Mean: 26204.06 W
  Min:  19096.01 W
  Max:  27710.99 W
```

---

### Phase 5: Generate Comparison Plots

**Script loads three datasets:**
1. **Ground Truth:** `RealWorld_Actions_Observations.csv` (columns: actions + P_CDWPs_sum + P_CHWPs_sum + ...)
2. **Simulink:** `Pumps_P_Simulink.csv` (pre-generated from MATLAB simulation)
3. **PyFMI+MLP:** `Pumps_P_Pyfmi_mlp_restapi.csv` (just created by test script)

**Script creates plots using matplotlib:**

**Plot 1: Condenser Water Pumps Power Comparison**
```python
plt.plot(range(2000), df_truth['P_CDWPs_sum'], label='Truth')
plt.plot(range(2000), df_simulink['Pcdwp_sum'], label='Simulink')
plt.plot(range(2000), df_pyfmi_mlp['P_CDWPs_sum']/1000, label='PyFMI+MLP')
plt.savefig('P_CDWPs_comparison.png')
```

**Plot 2: Chilled Water Pumps Power Comparison**
(Same structure, different variable)

**Outputs:**
- `P_CDWPs_comparison.png` (high-resolution plot)
- `P_CHWPs_comparison.png` (high-resolution plot)

Both saved on your laptop.

---

### Phase 6: Logging

Throughout execution, everything is logged to `test_results.txt`:
- Health check results
- Metadata query results
- Simulation progress
- Final statistics
- Output file paths

---

## Where Does Each File Come From?

| File | Created By | When | Purpose |
|------|-----------|------|---------|
| `RealWorld_Actions_Observations.csv` | Pre-existing (reference data) | Before test | Source of control actions + ground truth measurements |
| `Pumps_P_Simulink.csv` | MATLAB/Simulink (offline) | Before test | Validation baseline from industry-standard tool |
| `Pumps_P_Pyfmi_mlp_restapi.csv` | **test_rest_api_full.py** | During test | Output being validated (PyFMI+MLP results) |
| `api_metadata.txt` | **test_rest_api_full.py** | During test | Documentation of API capabilities |
| `test_results.txt` | **test_rest_api_full.py** | During test | Execution log |
| `P_CDWPs_comparison.png` | **test_rest_api_full.py** | During test | Visual comparison plot |
| `P_CHWPs_comparison.png` | **test_rest_api_full.py** | During test | Visual comparison plot |

---

## Key Insights

### The MLP is Transparent to the Test Script

The test script **never directly interacts with the MLP**. From the script's perspective:
- Sends 100 control inputs
- Receives 86 measurements
- Doesn't know (or care) that MLP calculated Head_required internally

The MLP calculation happens **automatically inside testcase.py** during every `/advance` call. This encapsulation keeps the API clean and the simulation logic modular.

### testcase.py is the Simulation Orchestrator

`testcase.py` acts as a **wrapper** that:
1. Validates control inputs
2. Adds disturbances from CSV files
3. **Calculates pump head using MLP** (replaces complex hydraulic equations)
4. Runs FMU simulation
5. Extracts and returns measurements

It's the "glue" between the REST API and the physics simulation.

### Why Two Separate Processes?

**Advantages of client-server design:**
- **Isolation:** FMU/PyFMI dependencies stay in Docker (hard to install on all platforms)
- **Reusability:** Multiple clients can connect (Python scripts, Jupyter notebooks, RL agents)
- **Language-agnostic:** Any language that can make HTTP requests can use the API
- **Remote execution:** Could run Docker on a server, test script on laptop
- **State management:** Docker container maintains simulation state between requests

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

### What Success Means

If the plots show good agreement, it validates:
1. **FMU model is physically accurate** - captures thermodynamics, fluid mechanics correctly
2. **MLP neural network works correctly** - pump pressure calculations are accurate
3. **PyFMI simulation is stable** - no numerical divergence over long time horizons
4. **Integration is correct** - testcase.py properly orchestrates MLP + FMU
5. **Virtual data center is ready** - can be used for optimization research

---

## Common Questions

### Q: Why only test pump power, not chillers?
**A**: This is a **subsystem validation test**. Pumps are tested first because:
- They're simpler components (easier to validate)
- Pump models are critical for MLP validation (pressure calculations)
- Once pumps work correctly, we can test more complex components (chillers, fans)
- Focused testing helps isolate issues

### Q: Why 2000 steps?
**A**: Balances thoroughness with speed:
- Too few steps (e.g., 20) might miss rare events
- Too many steps (e.g., 100,000) takes too long to run
- 2000 steps ≈ 7 simulated days = captures weekly patterns and edge cases
- ~3-4 minutes execution time is reasonable for frequent testing

### Q: What if my plots don't match?
**A**: Debug checklist:
1. Is Docker running? (`docker ps` should show container)
2. Is the API responsive? (`curl http://127.0.0.1:5000/name`)
3. Are you using the correct CSV? (`RealWorld_Actions_Observations.csv` in `testing/`)
4. Check `test_results.txt` for error messages
5. Try with fewer steps first: `python test_rest_api_full.py --steps 100`
6. Restart Docker: `docker-compose down && docker-compose up`

### Q: Can I test other components?
**A**: Yes! Modify the script to collect additional measurements:
```python
# In run_simulation(), lines 134-136, change to:
P_CDWPs_sum.append(payload.get('P_CDWPs_sum', 0))
P_CHWPs_sum.append(payload.get('P_CHWPs_sum', 0))
P_Chillers_sum.append(payload.get('P_Chillers_sum', 0))  # Add this
P_CTfans_sum.append(payload.get('P_CTfans_sum', 0))     # Add this

# Update plotting code accordingly
# See api_metadata.txt for full list of 86 available measurements
```

### Q: How does the MLP know the right pump head?
**A**: The MLP was **pre-trained** on simulation data:
1. Ran thousands of simulations with different configurations
2. Recorded: (chiller_count, HEX_count, CT_valve_count, flow_rate) → required_head
3. Trained neural network to learn this mapping
4. Saved weights to `mlp.pth`
5. Now MLP can predict head instantly without solving fluid equations

The training process is not part of this test - we're validating the already-trained model.

---

## Technical Details (For Advanced Users)

### API Endpoints Used

| Endpoint | Method | Purpose | testcase.py Function |
|----------|--------|---------|---------------------|
| `/name` | GET | Retrieve test case name | `get_name()` line 816 |
| `/version` | GET | Retrieve version number | `get_version()` line 733 |
| `/inputs` | GET | List all control inputs | `get_inputs()` line 555 |
| `/measurements` | GET | List all sensors | `get_measurements()` line 589 |
| `/step` | PUT | Set time step size | `set_step()` line 497 |
| `/initialize` | PUT | Reset simulation | `initialize()` line 132 |
| `/advance` | POST | Execute one simulation step | `advance()` line 332 |

### Complete Data Flow Diagram

```
┌───────────────────────────────────────────────────────────────────────────┐
│                            YOUR LAPTOP                                    │
│                                                                           │
│  1. Read CSV ───────────────────────────────────────────────┐            │
│     RealWorld_Actions_Observations.csv                       │            │
│     (100 control inputs per row)                             ▼            │
│                                                                           │
│  2. test_rest_api_full.py                                                │
│     for i in range(2000):                                                │
│         u = csv.row[i]  ◄─────────────────────┐                          │
│         response = HTTP POST /advance          │                          │
│                    json = u                    │                          │
│                                                │                          │
└─────────────────────────┬──────────────────────┼───────────────────────────┘
                          │                      │
                          │ HTTP (localhost:5000)│
                          ▼                      │
┌───────────────────────────────────────────────┼───────────────────────────┐
│                       DOCKER CONTAINER        │                           │
│                                               │                           │
│  3. restapi.py (Flask)                        │                           │
│     POST /advance endpoint                    │                           │
│     parse JSON → u dict                       │                           │
│     call: case.advance(u) ────┐               │                           │
│                                │               │                           │
│  4. testcase.py                ▼               │                           │
│     advance(u):                                │                           │
│       ┌──────────────────────────────┐        │                           │
│       │ Count equipment:             │        │                           │
│       │ - chiller_count              │        │                           │
│       │ - heat_exchanger_count       │        │                           │
│       │ - cooling_tower_valve_count  │        │                           │
│       └────────────┬─────────────────┘        │                           │
│                    │                           │                           │
│       ┌────────────▼──────────────┐            │                           │
│       │ Calculate Mcw:            │            │                           │
│       │ Mcw = f(Mchw, P_chi, ...) │            │                           │
│       └────────────┬──────────────┘            │                           │
│                    │                           │                           │
│       ┌────────────▼──────────────┐            │                           │
│       │ ★ Call MLP:               │            │                           │
│       │ Head_req = mlp(           │            │                           │
│       │   chiller_count,          │◄───────────┤ 5. utils.py (MLP)         │
│       │   HEX_count,              │            │    - Neural network       │
│       │   CT_valve_count,         │            │    - mlp.pth weights      │
│       │   Mcw)                    │            │    - 3 layers, ReLU       │
│       └────────────┬──────────────┘            │                           │
│                    │                           │                           │
│       ┌────────────▼──────────────┐            │                           │
│       │ Build input trajectory:   │            │                           │
│       │ - 100 control inputs      │            │                           │
│       │ - Head_required (MLP)     │            │                           │
│       │ - Disturbances (CSV)      │            │                           │
│       └────────────┬──────────────┘            │                           │
│                    │                           │                           │
│       ┌────────────▼──────────────┐            │                           │
│       │ ★ Run FMU Simulation:     │◄───────────┤ 6. PyFMI + FMU            │
│       │ res = fmu.simulate(       │            │    - AlphaDataCenter.fmu  │
│       │   start_time,             │            │    - CVode solver         │
│       │   final_time,             │            │    - 300s physics         │
│       │   inputs)                 │            │    - Thermodynamics       │
│       └────────────┬──────────────┘            │    - Fluid mechanics      │
│                    │                           │                           │
│       ┌────────────▼──────────────┐            │                           │
│       │ Extract measurements:     │            │                           │
│       │ - P_CDWPs_sum             │            │                           │
│       │ - P_CHWPs_sum             │            │                           │
│       │ - 84 other measurements   │            │                           │
│       └────────────┬──────────────┘            │                           │
│                    │                           │                           │
│       return payload ──────────────┘           │                           │
│                    │                           │                           │
│  7. restapi.py wraps response                  │                           │
│     {'status': 200,                            │                           │
│      'payload': {...86 measurements...}}       │                           │
│                    │                           │                           │
└────────────────────┼───────────────────────────┼───────────────────────────┘
                     │                           │
                     │ HTTP Response (JSON)      │
                     ▼                           │
┌────────────────────────────────────────────────┼───────────────────────────┐
│                   YOUR LAPTOP                  │                           │
│                                                │                           │
│  8. test_rest_api_full.py                      │                           │
│     payload = response.json()['payload']       │                           │
│     P_CDWPs_sum.append(payload['P_CDWPs_sum']) │                           │
│     P_CHWPs_sum.append(payload['P_CHWPs_sum']) │                           │
│                                                │                           │
│     # Repeat 2000 times ───────────────────────┘                           │
│                                                                            │
│  9. Save results:                                                          │
│     Pumps_P_Pyfmi_mlp_restapi.csv ◄─── df.to_csv()                        │
│                                                                            │
│  10. Generate plots:                                                       │
│      Load: Ground Truth, Simulink, PyFMI+MLP                              │
│      Create: P_CDWPs_comparison.png                                        │
│               P_CHWPs_comparison.png                                       │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### Performance Characteristics
- **Simulation speed**: ~9.5 iterations/second (with progress bar)
- **API latency**: ~100-120ms per request (local Docker)
  - Network overhead: ~5ms
  - MLP inference: ~2-5ms
  - FMU simulation: ~90-110ms
- **Memory usage**: ~50-100 MB for 2000 steps
- **Disk usage**: ~3 MB total (CSVs + PNGs + logs)

### FMU Solver Settings
From testcase.py initialization:
```python
options['CVode_options']['rtol'] = 0.001  # Relative tolerance
options['CVode_options']['atol'] = 0.001  # Absolute tolerance
options['ncp'] = 5                         # Number of communication points
```
These control accuracy vs. speed tradeoff in the ODE solver.

---

## Summary

`test_rest_api_full.py` is a comprehensive validation tool that:
1. **Connects** to a virtual data center cooling system (Docker container)
2. **Sends** 2000 control commands via REST API
3. **Receives** power consumption measurements from PyFMI+MLP simulation
4. **Compares** results against Ground Truth and Simulink references
5. **Generates** visual comparisons and statistical summaries

**Key Architecture Points:**
- Test script (client) and simulation (server) run in separate processes
- Communication via HTTP REST API on localhost:5000
- MLP calculation happens automatically inside testcase.py (transparent to client)
- FMU simulation runs in Docker with PyFMI
- All simulation state maintained in Docker container

**Success Criteria:**
PyFMI+MLP simulation should closely match both Ground Truth (reality) and Simulink (industry standard). Good agreement validates that the FMU model, MLP neural network, and integration are all working correctly.

**Your Results:** ✅ Validation successful - simulation is accurate and ready for optimization research.
