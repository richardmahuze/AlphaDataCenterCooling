# Control Inputs Reference

This document provides a comprehensive reference for all control inputs available in the AlphaDataCenterCooling simulation environment.

## Table of Contents
- [Nomenclature](#nomenclature)
- [Overview](#overview)
- [Input Categories](#input-categories)
  - [Cooling Tower Valve Controls](#1-cooling-tower-valve-controls)
  - [Cooling Tower Fan Speed Controls](#2-cooling-tower-fan-speed-controls)
  - [Pump Speed Controls](#3-pump-speed-controls)
  - [Chiller On/Off Controls](#4-chiller-onoff-controls)
  - [Condenser Water Valve Controls](#5-condenser-water-valve-controls)
  - [Chilled Water Valve Controls](#6-chilled-water-valve-controls)
  - [Pump On/Off Controls](#7-pump-onoff-controls)
  - [Global Setpoints](#8-global-setpoints)
- [Special Considerations](#special-considerations)
- [Interdependencies](#interdependencies)

---

## Nomenclature

### System Components
- **CHI** - Chiller: Equipment that removes heat from chilled water using a vapor-compression or absorption refrigeration cycle
- **CT** - Cooling Tower: Heat rejection device that extracts waste heat to the atmosphere through evaporative cooling
- **CDWP** - Condenser Water Pump: Circulates water between chillers and cooling towers
- **CHWP** - Chilled Water Pump: Circulates chilled water between chillers and the data center load
- **HEX** - Heat Exchanger: Transfers thermal energy between chilled water circuits
- **CW** - Condenser Water: Water circuit that rejects heat from chillers to cooling towers
- **CHW** - Chilled Water: Water circuit that absorbs heat from the data center load

### Notation Conventions
- **01-06** - Equipment unit number (system has 6 of each major component)
- **_01, _02** - Sub-component identifier (e.g., each cooling tower has 2 fans)
- **_CW1-4** - Condenser water valve positions for each chiller (4 valves per chiller)
- **_CHW1-4** - Chilled water valve positions for each chiller (4 valves per chiller)

---

## Overview

The AlphaDataCenterCooling environment provides **100 control inputs** that govern the operation of a data center cooling system. The system architecture consists of 6 parallel cooling trains, each containing:
- 1 chiller with associated valves
- 1 cooling tower with 2 fans
- 1 condenser water pump
- 1 chilled water pump

Control inputs range from binary on/off signals to continuous variables like pump speeds and temperature setpoints. All inputs must be provided at each simulation step, with the step size constrained to multiples of 300 seconds.

---

## Input Categories

### 1. Cooling Tower Valve Controls

These binary inputs control whether cooling towers are active in the system. When a cooling tower valve is open (1), condenser water can flow through that tower for heat rejection.

| Index | Variable Name | Type | Range | Unit | Description |
|-------|--------------|------|-------|------|-------------|
| 0 | `U_CT1` | Binary | [0, 1] | - | Cooling tower 1 valve position (0=closed, 1=open) |
| 1 | `U_CT2` | Binary | [0, 1] | - | Cooling tower 2 valve position |
| 2 | `U_CT3` | Binary | [0, 1] | - | Cooling tower 3 valve position |
| 3 | `U_CT4` | Binary | [0, 1] | - | Cooling tower 4 valve position |
| 4 | `U_CT5` | Binary | [0, 1] | - | Cooling tower 5 valve position |
| 5 | `U_CT6` | Binary | [0, 1] | - | Cooling tower 6 valve position |

**Usage Guidelines:**
- Set to 1 to enable a cooling tower for heat rejection
- Should typically match the corresponding chiller's on/off state
- Opening a valve without running fans provides minimal cooling

---

### 2. Cooling Tower Fan Speed Controls

These continuous inputs control the normalized speed ratio of cooling tower fans. Each of the 6 cooling towers has 2 fans, providing fine-grained control over heat rejection capacity.

| Index | Variable Name | Type | Range | Unit | Description |
|-------|--------------|------|-------|------|-------------|
| 6 | `Ffan_CT1_01` | Continuous | [0, ∞) | - | Cooling tower 1, fan 1 normalized speed ratio |
| 7 | `Ffan_CT1_02` | Continuous | [0, ∞) | - | Cooling tower 1, fan 2 normalized speed ratio |
| 8 | `Ffan_CT2_01` | Continuous | [0, ∞) | - | Cooling tower 2, fan 1 normalized speed ratio |
| 9 | `Ffan_CT2_02` | Continuous | [0, ∞) | - | Cooling tower 2, fan 2 normalized speed ratio |
| 10 | `Ffan_CT3_01` | Continuous | [0, ∞) | - | Cooling tower 3, fan 1 normalized speed ratio |
| 11 | `Ffan_CT3_02` | Continuous | [0, ∞) | - | Cooling tower 3, fan 2 normalized speed ratio |
| 12 | `Ffan_CT4_01` | Continuous | [0, ∞) | - | Cooling tower 4, fan 1 normalized speed ratio |
| 13 | `Ffan_CT4_02` | Continuous | [0, ∞) | - | Cooling tower 4, fan 2 normalized speed ratio |
| 14 | `Ffan_CT5_01` | Continuous | [0, ∞) | - | Cooling tower 5, fan 1 normalized speed ratio |
| 15 | `Ffan_CT5_02` | Continuous | [0, ∞) | - | Cooling tower 5, fan 2 normalized speed ratio |
| 16 | `Ffan_CT6_01` | Continuous | [0, ∞) | - | Cooling tower 6, fan 1 normalized speed ratio |
| 17 | `Ffan_CT6_02` | Continuous | [0, ∞) | - | Cooling tower 6, fan 2 normalized speed ratio |

**Usage Guidelines:**
- 0.0 = fan off
- 1.0 = nominal design speed
- Values > 1.0 = overclock (if equipment supports)
- Higher speeds increase cooling capacity but consume more power
- Only effective when corresponding `U_CT` valve is open
- Recommended range: 0.0 to 1.2 for typical operation

---

### 3. Pump Speed Controls

These continuous inputs control the rotational speed of pumps in revolutions per minute (RPM). The system has 6 condenser water pumps and 6 chilled water pumps.

#### Condenser Water Pumps

| Index | Variable Name | Type | Range | Unit | Description |
|-------|--------------|------|-------|------|-------------|
| 18 | `CDWP01_rpm` | Continuous | [0, ∞) | RPM | Condenser water pump 1 rotational speed |
| 19 | `CDWP02_rpm` | Continuous | [0, ∞) | RPM | Condenser water pump 2 rotational speed |
| 20 | `CDWP03_rpm` | Continuous | [0, ∞) | RPM | Condenser water pump 3 rotational speed |
| 21 | `CDWP04_rpm` | Continuous | [0, ∞) | RPM | Condenser water pump 4 rotational speed |
| 22 | `CDWP05_rpm` | Continuous | [0, ∞) | RPM | Condenser water pump 5 rotational speed |
| 23 | `CDWP06_rpm` | Continuous | [0, ∞) | RPM | Condenser water pump 6 rotational speed |

#### Chilled Water Pumps

| Index | Variable Name | Type | Range | Unit | Description |
|-------|--------------|------|-------|------|-------------|
| 24 | `CHWP01_rpm` | Continuous | [0, ∞) | RPM | Chilled water pump 1 rotational speed |
| 25 | `CHWP02_rpm` | Continuous | [0, ∞) | RPM | Chilled water pump 2 rotational speed |
| 26 | `CHWP03_rpm` | Continuous | [0, ∞) | RPM | Chilled water pump 3 rotational speed |
| 27 | `CHWP04_rpm` | Continuous | [0, ∞) | RPM | Chilled water pump 4 rotational speed |
| 28 | `CHWP05_rpm` | Continuous | [0, ∞) | RPM | Chilled water pump 5 rotational speed |
| 29 | `CHWP06_rpm` | Continuous | [0, ∞) | RPM | Chilled water pump 6 rotational speed |

**Usage Guidelines:**
- Typical operating range: 500-1500 RPM
- Higher speeds increase flow rate but consume more power (cubic relationship: P ∝ RPM³)
- Must coordinate with corresponding pump on/off signal (`CDWP_ONOFF` or `CHWP_ONOFF`)
- RPM has no effect if pump is off
- Ensure sufficient speed to meet head pressure requirements (calculated automatically)

---

### 4. Chiller On/Off Controls

These binary inputs control whether each chiller is operational. Chillers are the primary energy consumers in the system.

| Index | Variable Name | Type | Range | Unit | Description |
|-------|--------------|------|-------|------|-------------|
| 30 | `CHI01` | Binary | [0, 1] | - | Chiller 1 on/off (0=off, 1=on) |
| 31 | `CHI02` | Binary | [0, 1] | - | Chiller 2 on/off |
| 32 | `CHI03` | Binary | [0, 1] | - | Chiller 3 on/off |
| 33 | `CHI04` | Binary | [0, 1] | - | Chiller 4 on/off |
| 34 | `CHI05` | Binary | [0, 1] | - | Chiller 5 on/off |
| 35 | `CHI06` | Binary | [0, 1] | - | Chiller 6 on/off |

**Usage Guidelines:**
- Only turn on chillers needed to meet cooling load
- When a chiller is on, ensure:
  - Corresponding cooling tower valve is open
  - Appropriate condenser and chilled water valves are open
  - Both condenser and chilled water pumps are running
- Frequent on/off cycling can damage equipment (avoid in real systems)
- Consider staging chillers based on load requirements

---

### 5. Condenser Water Valve Controls

These 24 binary inputs control valves on the condenser water side of each chiller. Each chiller has 4 condenser water valves (CW1-4) that regulate flow through different paths in the condenser water circuit.

| Index | Variable Name | Type | Range | Unit | Description |
|-------|--------------|------|-------|------|-------------|
| 36 | `CHI01_CW1` | Binary | [0, 1] | - | Chiller 1 condenser water valve 1 |
| 37 | `CHI01_CW2` | Binary | [0, 1] | - | Chiller 1 condenser water valve 2 |
| 38 | `CHI01_CW3` | Binary | [0, 1] | - | Chiller 1 condenser water valve 3 |
| 39 | `CHI01_CW4` | Binary | [0, 1] | - | Chiller 1 condenser water valve 4 |
| 40 | `CHI02_CW1` | Binary | [0, 1] | - | Chiller 2 condenser water valve 1 |
| 41 | `CHI02_CW2` | Binary | [0, 1] | - | Chiller 2 condenser water valve 2 |
| 42 | `CHI02_CW3` | Binary | [0, 1] | - | Chiller 2 condenser water valve 3 |
| 43 | `CHI02_CW4` | Binary | [0, 1] | - | Chiller 2 condenser water valve 4 |
| 44 | `CHI03_CW1` | Binary | [0, 1] | - | Chiller 3 condenser water valve 1 |
| 45 | `CHI03_CW2` | Binary | [0, 1] | - | Chiller 3 condenser water valve 2 |
| 46 | `CHI03_CW3` | Binary | [0, 1] | - | Chiller 3 condenser water valve 3 |
| 47 | `CHI03_CW4` | Binary | [0, 1] | - | Chiller 3 condenser water valve 4 |
| 48 | `CHI04_CW1` | Binary | [0, 1] | - | Chiller 4 condenser water valve 1 |
| 49 | `CHI04_CW2` | Binary | [0, 1] | - | Chiller 4 condenser water valve 2 |
| 50 | `CHI04_CW3` | Binary | [0, 1] | - | Chiller 4 condenser water valve 3 |
| 51 | `CHI04_CW4` | Binary | [0, 1] | - | Chiller 4 condenser water valve 4 |
| 52 | `CHI05_CW1` | Binary | [0, 1] | - | Chiller 5 condenser water valve 1 |
| 53 | `CHI05_CW2` | Binary | [0, 1] | - | Chiller 5 condenser water valve 2 |
| 54 | `CHI05_CW3` | Binary | [0, 1] | - | Chiller 5 condenser water valve 3 |
| 55 | `CHI05_CW4` | Binary | [0, 1] | - | Chiller 5 condenser water valve 4 |
| 56 | `CHI06_CW1` | Binary | [0, 1] | - | Chiller 6 condenser water valve 1 |
| 57 | `CHI06_CW2` | Binary | [0, 1] | - | Chiller 6 condenser water valve 2 |
| 58 | `CHI06_CW3` | Binary | [0, 1] | - | Chiller 6 condenser water valve 3 |
| 59 | `CHI06_CW4` | Binary | [0, 1] | - | Chiller 6 condenser water valve 4 |

**Usage Guidelines:**
- At least one valve (typically CW3) must be open when chiller is operating
- CW3 valves commonly represent the primary heat exchanger path
- Valve configuration affects flow distribution and pressure drop
- Opening multiple valves may provide redundancy but increases pump power

---

### 6. Chilled Water Valve Controls

These 24 binary inputs control valves on the chilled water side of each chiller. Each chiller has 4 chilled water valves (CHW1-4) that regulate flow to the data center load.

| Index | Variable Name | Type | Range | Unit | Description |
|-------|--------------|------|-------|------|-------------|
| 60 | `CHI01_CHW1` | Binary | [0, 1] | - | Chiller 1 chilled water valve 1 |
| 61 | `CHI01_CHW2` | Binary | [0, 1] | - | Chiller 1 chilled water valve 2 |
| 62 | `CHI01_CHW3` | Binary | [0, 1] | - | Chiller 1 chilled water valve 3 |
| 63 | `CHI01_CHW4` | Binary | [0, 1] | - | Chiller 1 chilled water valve 4 |
| 64 | `CHI02_CHW1` | Binary | [0, 1] | - | Chiller 2 chilled water valve 1 |
| 65 | `CHI02_CHW2` | Binary | [0, 1] | - | Chiller 2 chilled water valve 2 |
| 66 | `CHI02_CHW3` | Binary | [0, 1] | - | Chiller 2 chilled water valve 3 |
| 67 | `CHI02_CHW4` | Binary | [0, 1] | - | Chiller 2 chilled water valve 4 |
| 68 | `CHI03_CHW1` | Binary | [0, 1] | - | Chiller 3 chilled water valve 1 |
| 69 | `CHI03_CHW2` | Binary | [0, 1] | - | Chiller 3 chilled water valve 2 |
| 70 | `CHI03_CHW3` | Binary | [0, 1] | - | Chiller 3 chilled water valve 3 |
| 71 | `CHI03_CHW4` | Binary | [0, 1] | - | Chiller 3 chilled water valve 4 |
| 72 | `CHI04_CHW1` | Binary | [0, 1] | - | Chiller 4 chilled water valve 1 |
| 73 | `CHI04_CHW2` | Binary | [0, 1] | - | Chiller 4 chilled water valve 2 |
| 74 | `CHI04_CHW3` | Binary | [0, 1] | - | Chiller 4 chilled water valve 3 |
| 75 | `CHI04_CHW4` | Binary | [0, 1] | - | Chiller 4 chilled water valve 4 |
| 76 | `CHI05_CHW1` | Binary | [0, 1] | - | Chiller 5 chilled water valve 1 |
| 77 | `CHI05_CHW2` | Binary | [0, 1] | - | Chiller 5 chilled water valve 2 |
| 78 | `CHI05_CHW3` | Binary | [0, 1] | - | Chiller 5 chilled water valve 3 |
| 79 | `CHI05_CHW4` | Binary | [0, 1] | - | Chiller 5 chilled water valve 4 |
| 80 | `CHI06_CHW1` | Binary | [0, 1] | - | Chiller 6 chilled water valve 1 |
| 81 | `CHI06_CHW2` | Binary | [0, 1] | - | Chiller 6 chilled water valve 2 |
| 82 | `CHI06_CHW3` | Binary | [0, 1] | - | Chiller 6 chilled water valve 3 |
| 83 | `CHI06_CHW4` | Binary | [0, 1] | - | Chiller 6 chilled water valve 4 |

**Usage Guidelines:**
- At least one valve must be open when chiller is operating to deliver cooling
- CHW3 valves often represent the primary supply path to the load
- Configuration affects flow distribution to different zones or heat exchangers
- Balance valve positions to avoid short-circuiting flow

---

### 7. Pump On/Off Controls

These 12 binary inputs enable or disable pump operation. They work in conjunction with the pump RPM controls.

#### Condenser Water Pump On/Off

| Index | Variable Name | Type | Range | Unit | Description |
|-------|--------------|------|-------|------|-------------|
| 84 | `CDWP01_ONOFF` | Binary | [0, 1] | - | Condenser water pump 1 enable (0=off, 1=on) |
| 85 | `CDWP02_ONOFF` | Binary | [0, 1] | - | Condenser water pump 2 enable |
| 86 | `CDWP03_ONOFF` | Binary | [0, 1] | - | Condenser water pump 3 enable |
| 87 | `CDWP04_ONOFF` | Binary | [0, 1] | - | Condenser water pump 4 enable |
| 88 | `CDWP05_ONOFF` | Binary | [0, 1] | - | Condenser water pump 5 enable |
| 89 | `CDWP06_ONOFF` | Binary | [0, 1] | - | Condenser water pump 6 enable |

#### Chilled Water Pump On/Off

| Index | Variable Name | Type | Range | Unit | Description |
|-------|--------------|------|-------|------|-------------|
| 90 | `CHWP01_ONOFF` | Binary | [0, 1] | - | Chilled water pump 1 enable (0=off, 1=on) |
| 91 | `CHWP02_ONOFF` | Binary | [0, 1] | - | Chilled water pump 2 enable |
| 92 | `CHWP03_ONOFF` | Binary | [0, 1] | - | Chilled water pump 3 enable |
| 93 | `CHWP04_ONOFF` | Binary | [0, 1] | - | Chilled water pump 4 enable |
| 94 | `CHWP05_ONOFF` | Binary | [0, 1] | - | Chilled water pump 5 enable |
| 95 | `CHWP06_ONOFF` | Binary | [0, 1] | - | Chilled water pump 6 enable |

**Usage Guidelines:**
- Pump must be on (1) for corresponding RPM setting to have effect
- Match pump on/off state with chiller state in the same cooling train
- Setting RPM to 0 is NOT equivalent to turning pump off
- Consider minimum flow requirements when turning pumps off

---

### 8. Global Setpoints

These 4 continuous inputs control system-wide operational parameters that affect overall cooling performance.

| Index | Variable Name | Type | Range | Unit | Description |
|-------|--------------|------|-------|------|-------------|
| 96 | `CWP_speedInput` | Continuous | [0, ∞) | RPM | Average speed command for all active condenser water pumps |
| 97 | `Tchws_set_CHI` | Continuous | [0, ∞) | K | Chilled water supply temperature setpoint for chillers |
| 98 | `Tchws_set_HEX` | Continuous | [0, ∞) | K | Chilled water supply temperature setpoint for heat exchangers |
| 99 | `CWP_activatedNumber` | Integer | [0, 6] | - | Number of condenser water pumps to activate |

**Usage Guidelines:**

**CWP_speedInput:**
- Provides centralized speed control for condenser water pumps
- May override or coordinate with individual `CDWP_rpm` settings
- Typical range: 500-1500 RPM

**Tchws_set_CHI:**
- Target temperature for chilled water leaving the chillers
- Typical range: 282-295 K (9-22°C)
- Lower setpoints increase chiller power consumption
- Must be higher than data center supply requirements
- Common setpoint: 286.55 K (13.4°C)

**Tchws_set_HEX:**
- Target temperature for chilled water leaving heat exchangers
- Enables free cooling when outdoor conditions permit
- Typical range: 282-295 K (9-22°C)
- Should be coordinated with `Tchws_set_CHI`
- Common setpoint: 285.44 K (12.3°C)

**CWP_activatedNumber:**
- Integer value specifying how many condenser water pumps should run
- Used for load staging and redundancy
- Must be ≤ number of active chillers
- Setting this may interact with individual `CDWP_ONOFF` controls

---

## Special Considerations

### Automatically Calculated Input

**Head_required** (not directly controlled)
- The required pump head pressure is calculated automatically by the simulation
- Computed using a trained multi-layer perceptron (MLP) neural network
- Inputs to MLP: number of active chillers, heat exchangers, cooling tower valves, and condenser water flow rate
- This ensures pumps provide sufficient pressure for the current system configuration
- Users can optionally override this value in advanced scenarios

### Time Step Constraints

All control inputs must be updated at intervals that are multiples of 300 seconds (5 minutes):
- Valid step sizes: 300s, 600s, 900s, 1200s, etc.
- Default step size: 300 seconds
- Simulation bounds: 0 to 30,099,300 seconds (~348 days)

### Simulation Initialization

When starting simulation from a non-zero time:
- A 300-second warmup period is automatically applied
- Initial actions are loaded from `Resources/Initialization_actions.csv`
- This ensures stable initial conditions

---

## Interdependencies

Understanding relationships between inputs is crucial for effective control:

### Chiller Operation Requirements

When activating a chiller (e.g., `CHI01 = 1`), ensure:
1. **Condenser water circuit:**
   - Corresponding cooling tower valve open (`U_CT1 = 1`)
   - At least one condenser water valve open (e.g., `CHI01_CW3 = 1`)
   - Condenser water pump on (`CDWP01_ONOFF = 1`)
   - Condenser water pump speed > 0 (`CDWP01_rpm > 0`)

2. **Chilled water circuit:**
   - At least one chilled water valve open (e.g., `CHI01_CHW3 = 1`)
   - Chilled water pump on (`CHWP01_ONOFF = 1`)
   - Chilled water pump speed > 0 (`CHWP01_rpm > 0`)

3. **Cooling tower operation:**
   - At least one cooling tower fan running (e.g., `Ffan_CT1_01 > 0` or `Ffan_CT1_02 > 0`)

### Pump Control Hierarchy

Pumps have two-level control:
1. **Enable/Disable:** `CDWP_ONOFF` or `CHWP_ONOFF` must be 1
2. **Speed Control:** `CDWP_rpm` or `CHWP_rpm` sets rotational speed

The pump only operates when both conditions are satisfied.

### Valve Coordination

For efficient operation:
- **CW3 valves** (`CHI0X_CW3`) typically represent the heat exchanger path and should be open when the corresponding chiller is on
- **CHW3 valves** (`CHI0X_CHW3`) are often the primary chilled water supply path
- Opening multiple valves per chiller provides redundancy but increases hydraulic losses

### Temperature Setpoint Relationships

Maintain logical temperature hierarchy:
- Outdoor wet-bulb temperature (from `Disturbance.csv`)
- ≤ Cooling tower leaving water temperature
- ≤ Condenser water supply temperature
- ≤ Chilled water return temperature (from load)
- ≤ `Tchws_set_CHI` (chiller supply setpoint)
- ≤ Chilled water supply to data center

### Energy Efficiency Considerations

- **Pump power** scales with RPM³, so small speed reductions yield significant savings
- **Chiller efficiency** decreases at lower evaporator temperatures (lower `Tchws_set_CHI`)
- **Free cooling** is possible via heat exchangers when outdoor conditions allow (`Tchws_set_HEX`)
- **Staging chillers** (running fewer at higher capacity) is often more efficient than running many at low load

---

## Quick Reference: Action Space Vector

The 100-element action vector follows this structure:

```
[0:6]     - Cooling tower valves (U_CT)
[6:18]    - Cooling tower fan speeds (Ffan_CT)
[18:24]   - Condenser water pump speeds (CDWP_rpm)
[24:30]   - Chilled water pump speeds (CHWP_rpm)
[30:36]   - Chiller on/off (CHI)
[36:60]   - Condenser water valves (CHI_CW)
[60:84]   - Chilled water valves (CHI_CHW)
[84:90]   - Condenser water pump on/off (CDWP_ONOFF)
[90:96]   - Chilled water pump on/off (CHWP_ONOFF)
[96]      - Average condenser water pump speed (CWP_speedInput)
[97]      - Chiller supply temperature setpoint (Tchws_set_CHI)
[98]      - Heat exchanger supply temperature setpoint (Tchws_set_HEX)
[99]      - Number of active condenser water pumps (CWP_activatedNumber)
```

---

## Additional Resources

- **FMU Model:** `Resources/AlphaDataCenterCooling_FMU.fmu`
- **Disturbances:** `Resources/Disturbance.csv` (outdoor conditions and load)
- **Initial States:** `Resources/Initialization_actions.csv` and `Resources/Initialization_observation0.csv`
- **Schema Configuration:** `AlphaDataCenterCooling_Gym/schema.json`
- **REST API Documentation:** See `testing/test_REST_API.ipynb`

For measurement outputs and observations, refer to the companion `schema.json` file or query the `/measurements` endpoint of the REST API.
