# -*- coding: utf-8 -*-
"""
This module defines the API to the test case used by the REST requests to 
perform functions such as advancing the simulation, retreiving test case 
information, and calculating and reporting results.
"""
try:
    from fmpy import simulate_fmu, dump, instantiate_fmu
    from fmpy.model_description import read_model_description, DefaultExperiment
    from fmpy.fmi2 import FMU2Slave
    import fmpy.fmi2 as fmi2
    FMPY_AVAILABLE = True
except ImportError:
    # Fallback to PyFMI if FMPy is not available
    from pyfmi import load_fmu
    FMPY_AVAILABLE = False
import numpy as np
import pandas as pd
import copy
import config
import math
import logging
import traceback
import array as a
import torch
from utils import MLP
class TestCase(object):
    '''Class that implements the test case.
    
    '''
    
    def __init__(self):
        '''Constructor.
        
        '''
        # Set AlphaDataCenterCooling version number
        with open('Resources/version.txt', 'r') as f:
            self.version = f.read()
        # Get configuration information
        con = config.get_config()
        self.fmupath = con['fmupath']

        # Load FMU
        self.name = con['name']
        self.step = con['step']

        if FMPY_AVAILABLE:
            # Use FMPy with persistent FMU instance
            self.model_description = read_model_description(self.fmupath)
            fmu_version = self.model_description.fmiVersion

            # Get available control inputs and outputs
            if fmu_version == '2.0':
                self.input_names = [v.name for v in self.model_description.modelVariables if v.causality == 'input']
                self.output_names = [v.name for v in self.model_description.modelVariables if v.causality == 'output']
            else:
                raise ValueError('FMU must be version 2.0.')

            # Store FMU path for improved simulation calls
            self.fmu = None  # Will use simulate_fmu with better parameters

            # Log FMU capabilities for debugging
            logging.info(f"FMU initialized: {self.model_description.modelName}")
            logging.info(f"FMU GUID: {self.model_description.guid}")
            if hasattr(self.model_description, 'defaultExperiment') and self.model_description.defaultExperiment:
                exp = self.model_description.defaultExperiment
                logging.info(f"FMU default experiment: start={exp.startTime}, stop={exp.stopTime}, step={exp.stepSize}")
                # Store FMU timing constraints
                self.fmu_default_start = exp.startTime if exp.startTime is not None else 0.0
                self.fmu_default_stop = exp.stopTime if exp.stopTime is not None else 1.0
                self.fmu_default_step = exp.stepSize if exp.stepSize is not None else 0.1
            else:
                # Fallback values if no default experiment
                self.fmu_default_start = 0.0
                self.fmu_default_stop = 1.0
                self.fmu_default_step = 0.1

            logging.info(f"Co-Simulation available: {self.model_description.coSimulation is not None}")
            logging.info(f"Model Exchange available: {self.model_description.modelExchange is not None}")
            logging.info(f"Using FMU timing constraints: start={self.fmu_default_start}, stop={self.fmu_default_stop}, step={self.fmu_default_step}")

        else:
            # Fallback to PyFMI
            self.fmu = load_fmu(self.fmupath)
            self.fmu.set_log_level(7)
            self.fmu.reset()

            # Get version
            fmu_version = self.fmu.get_version()

            # Get available control inputs and outputs
            if fmu_version == '2.0':
                self.input_names=list(self.fmu.get_model_variables(causality=2).keys())
                self.output_names=list(self.fmu.get_model_variables(causality=3).keys())
            else:
                raise ValueError('FMU must be version 2.0.')



        # options['CVode_options']['rtol'] = 1e-6
        if FMPY_AVAILABLE:
            # FMPy doesn't have simulate_options, we'll set options directly during simulate calls
            self.options = {
                'filter': self.output_names + self.input_names,
                'solver': 'CVode',
                'rtol': 1e-6,
                'atol': 1e-6
            }
        else:
            self.options = self.fmu.simulate_options()
            self.options['filter'] = self.output_names + self.input_names

        # Set initial simulation start
        start_time = 0
        self.start_time = start_time
        self.final_time = start_time
        self.initialize_fmu = True
        if FMPY_AVAILABLE:
            # FMPy doesn't need these PyFMI-specific option structures
            pass
        else:
            self.options['initialize'] = self.initialize_fmu
            self.options['CVode_options']['rtol'] = 0.001
            self.options['CVode_options']['atol'] = 0.001
            self.options['ncp'] = 5
        self.sim_interval=300
        # Load disturbance data
        self.disturbance_data=pd.read_csv('Resources/Disturbance.csv',index_col=0)
        self.disturbance_var=['Twb_outside','Mchw','Tchw_r']
        self.initialization_actions=pd.read_csv('Resources/Initialization_actions.csv',index_col='time')
        self.initialization_obs0 = pd.read_csv('Resources/Initialization_observation0.csv')
        self.mlp_model=torch.load('Resources/mlp.pth', weights_only=False)



        self.__initilize_data()

    def __initilize_data(self):

        '''Initializes objects for simulation data storage.

        Uses self.output_names and self.input_names to create
        self.y, self.y_store, self.u, self.u_store,
        self.inputs_metadata, self.outputs_metadata.

        Parameters
        ----------
        None

        Returns
        -------
        None

        '''

        # Get input and output and forecast meta-data
        self.input_names_without_distubance=list(set(self.input_names) - set(self.disturbance_var))
        if 'Head_required' in self.input_names_without_distubance:
            self.input_names_without_distubance.remove('Head_required')
        if FMPY_AVAILABLE:
            self.inputs_metadata = self._get_var_metadata(self.model_description, self.input_names_without_distubance, inputs=True)
        else:
            self.inputs_metadata = self._get_var_metadata(self.fmu, self.input_names_without_distubance, inputs=True)

        if FMPY_AVAILABLE:
            self.outputs_metadata = self._get_var_metadata(self.model_description, self.output_names)
        else:
            self.outputs_metadata = self._get_var_metadata(self.fmu, self.output_names)

        self.y = {'time': []}
        for key in self.output_names:
            self.y[key] = []

        self.y_store = copy.deepcopy(self.y)

        self.u = {'time': []}
        for key in self.input_names_without_distubance:
            self.u[key] = []

        self.u_store = copy.deepcopy(self.u)

        self.input_keys=list(set(self.input_names))

        self.P_chillers_sum=0

    def _reset_fmu(self):
        '''Reset FMU state for fresh simulation.

        '''
        if FMPY_AVAILABLE:
            # For the high-level API approach, reset is handled by simulate_fmu automatically
            logging.info("FMU reset (using high-level API - no action needed)")
        else:
            # PyFMI reset
            if self.fmu is not None:
                self.fmu.reset()

    def _simulate_fmu_improved(self, start_time, stop_time, inputs=None):
        '''Simulate FMU with improved timing and parameter handling.

        Parameters
        ----------
        start_time : float
            Start time for simulation
        stop_time : float
            Stop time for simulation
        inputs : dict, optional
            Input values to set during simulation

        Returns
        -------
        dict or None
            Simulation results if successful, None if failed
        '''
        if not FMPY_AVAILABLE:
            return None

        try:
            logging.info(f"Simulating FMU: start_time={start_time}, stop_time={stop_time}")

            # Adjust timing to respect FMU constraints
            adjusted_start = max(start_time, self.fmu_default_start)
            total_duration = stop_time - start_time

            # Break into smaller chunks if duration exceeds FMU default stop time
            if total_duration > self.fmu_default_stop:
                logging.warning(f"Simulation duration ({total_duration}s) exceeds FMU default ({self.fmu_default_stop}s)")
                # Use smaller time window
                chunk_size = min(self.fmu_default_stop * 0.8, total_duration)  # Use 80% of FMU limit as safety margin
                adjusted_stop = adjusted_start + chunk_size
                logging.info(f"Using chunked simulation: {adjusted_start} to {adjusted_stop}")
            else:
                adjusted_stop = stop_time

            # Convert inputs to structured array format if provided
            fmpy_input = None
            if inputs:
                # Create simple time series with constant inputs
                u_names = ['time'] + [k for k in inputs.keys() if k in self.input_names]
                time_points = np.array([adjusted_start, adjusted_stop])

                # Build structured array
                dtype_list = [('time', 'f8')] + [(name, 'f8') for name in u_names if name != 'time']
                fmpy_input = np.zeros(len(time_points), dtype=dtype_list)
                fmpy_input['time'] = time_points

                for name in u_names:
                    if name != 'time' and name in inputs:
                        fmpy_input[name] = float(inputs[name])  # Constant value over time

            # Run simulation with improved parameters
            res = simulate_fmu(
                filename=self.fmupath,
                start_time=adjusted_start,
                stop_time=adjusted_stop,
                output_interval=min(self.fmu_default_step, (adjusted_stop - adjusted_start) / 10),
                input=fmpy_input,
                output=self.options['filter'],
                solver=self.options.get('solver', 'CVode'),
                relative_tolerance=self.options.get('rtol', 1e-6)
                # Note: reset is not a valid parameter for simulate_fmu
            )

            logging.info("FMU simulation completed successfully")
            return res

        except Exception as e:
            logging.error(f"FMU simulation failed: {e}")
            logging.error(f"Exception type: {type(e)}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            return None

    # Remove _simulate_fmu_step since we're using high-level API

    def initialize(self, start_time, end_time=30099300):
        '''Initialize the test simulation.

        Parameters
        ----------
        start_time: int or float
            Start time of simulation to initialize to in seconds.
        end_time: int or float, optional
            Specifies a finite end time to allow the simulation to continue
            Default value is 30099300, which represents the maximum duration that the environment can run.

        Returns
        -------
        status: int
            Indicates whether an initialization request has been completed.
            If 200, initialization was completed successfully.
            If 400, an invalid start time  was identified.
        message: str
            Includes detailed debugging information.
        payload: dict
            Contains the full state of measurement and input data at the end
            of the initialization period.

        '''

        status = 200
        payload = None
        # Reset fmu
        if FMPY_AVAILABLE:
            # Reset FMPy instance
            self._reset_fmu()
        else:
            # Only PyFMI has reset method
            self.fmu.reset()
        # Reset simulation data storage
        self.__initilize_data()
        # Check if the inputs are valid
        try:
            start_time = float(start_time)
        except:
            payload = None
            status = 400
            message = "Invalid value {} for parameter start_time. Value must be a float, integer, or string able to be converted to a float, but is {}.".format(start_time, type(start_time))
            logging.error(message)
            return status, message, payload

        if start_time < 0:
            payload = None
            status = 400
            message = "Invalid value {} for parameter start_time. Value must not be negative.".format(start_time)
            logging.error(message)
            return status, message, payload
        if start_time%300!=0:
            payload = None
            status = 400
            message = "Invalid value {} for parameter start_time. Value must be  0 or a multiple of 300 . For example, valid values include 0, 300, 600, 900, etc.".format(start_time)
            logging.error(message)
            return status, message, payload

        try:
            end_time = float(end_time)
        except:
            payload = None
            status = 400
            message = "Invalid value {} for parameter end_time. Value must be a float, integer, or string able to be converted to a float, but is {}.".format(end_time, type(end_time))
            logging.error(message)
            return status, message, payload

        if end_time < 0:
            payload = None
            status = 400
            message = "Invalid value {} for parameter end_time. Value must not be negative.".format(end_time)
            logging.error(message)
            return status, message, payload

        if end_time <= start_time:
            payload = None
            status = 400
            message = "Invalid value {} for parameter end_time. Value must be greater than start_time.".format(end_time)
            logging.error(message)
            return status, message, payload

        if end_time%300!=0:
            payload = None
            status = 400
            message = "Invalid value {} for parameter end_time. Value must be a multiple of 300 . For example, valid values include 300, 600, 900, etc.".format(end_time)
            logging.error(message)
            return status, message, payload

        if end_time>30099300.0:
            payload = None
            status = 400
            message = "Invalid value {} for parameter end_time. Value must be less than or equal 30099300 seconds, which represents the maximum end time that the environment can run.".format(
                end_time)
            logging.error(message)
            return status, message, payload

        # Set fmu intitialization
        self.initialize_fmu = True
        if start_time==0:

            payload=self.initialization_obs0.iloc[0].to_dict()
            message = "Simulation initialized successfully to 0s."
            logging.info(message)
            return status, message, payload

        else:
            init_t1=start_time-300

            u_trajectory = init_t1
            u_list=[]
            init_u=self.initialization_actions.iloc[int(init_t1/300)].to_dict()
            for key in self.input_keys:
                if key !='time' and key in init_u:
                    value=float(init_u[key])
                    u_list.append(key)
                    u_trajectory=np.vstack((u_trajectory,value))
                elif key in self.disturbance_var:
                    value = float(self.disturbance_data.loc[init_t1,key])
                    u_list.append(key)
                    u_trajectory = np.vstack((u_trajectory, value))

            input_object = (u_list, np.transpose(u_trajectory))
            if FMPY_AVAILABLE:
                # Use improved FMPy simulation with timing constraints
                # Convert input_object to simple dictionary
                input_dict = {}
                if input_object is not None:
                    u_names, u_data = input_object
                    for i, name in enumerate(u_names):
                        if name != 'time' and len(u_data) > i:
                            input_dict[name] = u_data[i, 0] if u_data.ndim > 1 else u_data[i]

                # Run improved simulation for warmup period
                res = self._simulate_fmu_improved(init_t1, init_t1+300, input_dict)

                if res is None:
                    payload = None
                    status = 500
                    message = "Failed to simulate FMU for warmup period."
                    logging.error(message)
                    return status, message, payload
            else:
                self.options['initialize'] = self.initialize_fmu
                res = self.fmu.simulate(start_time=init_t1,
                                        final_time=init_t1+300,
                                        options=self.options,
                                        input=input_object)
            self.initialize_fmu = False
        if not isinstance(res, str):

            self.__store_results(res,store=False)
            # Set simulation start time to start_time
            self.start_time = start_time
            # Set simulation end time to end_time
            self.end_time=end_time
            # Get full current state
            payload = self._get_full_current_state()
            message = "Simulation initialized successfully to {0}s with warmup period of 300s.".format(self.start_time)
            logging.info(message)
            return status, message, payload
        else:
            payload = None
            status = 500
            message = "Failed to initialize test simulation: {}.".format(res)
            logging.error(message)

            return status, message, payload

    def __calc_Mcw(self,Mchw,P_chillers_sum,Tchw_r,Tchws_set_CHI):

        """
        Calculate the mass flow rate of the cooling water (Mcw).

        Parameters
        ----------
        Mchw: float
            Mass flow rate of chilled water (kg/s).
        P_chillers_sum: float
            Total power input of the chillers (Watts).
        Tchw_r: float
            Temperature of the return chilled water (Kelvin).
        Tchws_set_CHI: float
            Setpoint temperature for the chilled water supply (Kelvin).

        Returns
        -------
        Mcw: float
            The required mass flow rate of cooling water (kg/s).
        """

        Mcw = Mchw + (P_chillers_sum / (4200 * (Tchw_r - Tchws_set_CHI)))

        return Mcw

    def __calc_head_required(self,chiller_count,heat_exchanger_count,cooling_tower_valve_count,mcw):
        """
        Calculate the required head (pressure) for the cooling system.

        This method uses a multi-layer perceptron (MLP) model to predict the required head based on the number of chillers,
        heat exchangers, cooling tower valves, and the mass flow rate of cooling water.

        Parameters
        ----------
        chiller_count : int
           The number of chillers in operation.
        heat_exchanger_count : int
           The number of heat exchangers in operation.
        cooling_tower_valve_count : int
           The number of cooling tower valves in operation.
        mcw : float
           The mass flow rate of cooling water (kg/s).

        Returns
        -------
        head_required : float
           The required head (pressure) for the cooling system to operate effectively, measured in meters (m).
        """

        x=torch.tensor([chiller_count,heat_exchanger_count,cooling_tower_valve_count,mcw])
        x=x.float()
        output_tensor=self.mlp_model.step(x)
        head_required=output_tensor.item()
        return head_required

    def advance(self,u):
        '''Advances the test case model simulation forward one step.
        
        Parameters
        ----------
        u : dict
            Defines the control input data to be used for the step.
            {<input_name> : <input_value>}
            
        Returns
        -------
        y : dict
            Contains the measurement data at the end of the step.
            {<measurement_name> : <measurement_value>}
            
        '''

        # Simulate
        # print input_object
        status = 200
        # Handle None values by treating them as 0 (OFF/CLOSED)
        chiller_count = (u.get('CHI01', 0) or 0) + (u.get('CHI02', 0) or 0) + (u.get('CHI03', 0) or 0) + (u.get('CHI04', 0) or 0) + (u.get('CHI05', 0) or 0) + (u.get('CHI06', 0) or 0)
        heat_exchanger_count = (u.get('CHI01_CW3', 0) or 0) + (u.get('CHI02_CW3', 0) or 0) + (u.get('CHI03_CW3', 0) or 0) + (u.get('CHI04_CW3', 0) or 0) + (u.get('CHI05_CW3', 0) or 0) + (u.get('CHI06_CW3', 0) or 0)
        cooling_tower_valve_count = ((u.get('U_CT1', 0) or 0) + (u.get('U_CT2', 0) or 0) + (u.get('U_CT3', 0) or 0) + (u.get('U_CT4', 0) or 0) + (u.get('U_CT5', 0) or 0) + (u.get('U_CT6', 0) or 0)) * 2

        iteration_num= math.ceil(self.step / self.sim_interval)
        for i in range(iteration_num):
            self.options['initialize'] = self.initialize_fmu
            self.start_time_itr = self.start_time + self.sim_interval*i
            if i < iteration_num - 1:
                self.final_time_itr = self.start_time+self.sim_interval * (i + 1)
            else:
                self.final_time_itr = self.start_time + self.step

            # Initialize variables with default values
            Tchws_set_CHI = 286.55  # Default chilled water supply temperature setpoint (K)
            Mchw = None  # Will be set from disturbance data
            Tchw_r = None  # Will be set from disturbance data

            # Set control inputs if they exist
            if u.keys():
                u_list = []
                u_trajectory = self.start_time_itr
                for key in self.input_keys:

                    if key != 'time' and key in u:
                        if u[key] is not None:
                            try:
                                value = float(u[key])
                            except:
                                payload = None
                                status = 400
                                message = "Invalid value {} for input {}. Value must be a float, integer, or string able to be converted to a float, but is {}.".format(u[key], key, type(u[key]))
                                logging.error(message)
                                return status, message, payload
                            if key=='Tchws_set_CHI':
                                Tchws_set_CHI=value
                            u_list.append(key)
                            u_trajectory = np.vstack((u_trajectory, value))
                    elif key in self.disturbance_var:


                        value = float(self.disturbance_data.loc[self.start_time_itr,key])
                        if key == 'Mchw':
                            Mchw=value
                        if key=='Tchw_r':
                            Tchw_r=value

                        u_list.append(key)
                        u_trajectory = np.vstack((u_trajectory, value))

                Mcw=self.__calc_Mcw(Mchw,self.P_chillers_sum,Tchw_r,Tchws_set_CHI)/1000
                Head_required = self.__calc_head_required(chiller_count, heat_exchanger_count,
                                                          cooling_tower_valve_count, Mcw)


                u_list.append('Head_required')
                if 'Head_required' in u.keys():

                    u_trajectory = np.vstack((u_trajectory, u['Head_required']))
                else:
                    u_trajectory = np.vstack((u_trajectory, Head_required))
                input_object = (u_list, np.transpose(u_trajectory))
            else:
                input_object = None

            try:
                if FMPY_AVAILABLE:
                    # Use improved FMPy simulation with timing constraints
                    # Convert input to dictionary format
                    input_dict = {}
                    if input_object is not None:
                        u_names, u_data = input_object
                        for i, name in enumerate(u_names):
                            if name != 'time' and len(u_data) > i:
                                input_dict[name] = u_data[i, 0] if u_data.ndim > 1 else u_data[i]

                    # Run improved simulation for advance step
                    res = self._simulate_fmu_improved(self.start_time_itr, self.final_time_itr, input_dict)

                    if res is None:
                        raise Exception("FMU advance simulation failed")

                else:
                    res = self.fmu.simulate(start_time=self.start_time_itr,
                                            final_time=self.final_time_itr,
                                            options=self.options,
                                            input=input_object)
            except Exception as e:
                logging.warning(f"Primary simulation failed: {e}")
                if not FMPY_AVAILABLE:
                    self.fmu = load_fmu(self.fmupath)
                    self.fmu.set_log_level(7)
                    self.fmu.reset()
                    self.options['CVode_options']['rtol'] = 0.001
                    self.options['CVode_options']['atol'] = 0.001
                    self.options['ncp'] = 5
                    self.options['initialize'] = True
                    res = self.fmu.simulate(start_time=self.start_time_itr,
                                            final_time=self.final_time_itr,
                                            options=self.options,
                                            input=input_object)
                else:
                    # For FMPy, retry with improved simulation method
                    logging.info("Retrying FMPy simulation with relaxed parameters")

                    # Convert input to dictionary format
                    input_dict = {}
                    if input_object is not None:
                        u_names, u_data = input_object
                        for i, name in enumerate(u_names):
                            if name != 'time' and len(u_data) > i:
                                input_dict[name] = u_data[i, 0] if u_data.ndim > 1 else u_data[i]

                    # Retry with improved simulation (automatically handles timing constraints)
                    res = self._simulate_fmu_improved(self.start_time_itr, self.final_time_itr, input_dict)

                    if res is None:
                        raise Exception("FMPy retry simulation also failed")

            self.initialize_fmu = False
            self.P_chillers_sum=res['Pchi1'][-1]+res['Pchi2'][-1]+res['Pchi3'][-1]+res['Pchi4'][-1]+res['Pchi5'][-1]+res['Pchi6'][-1]

        # Get result and store measurement
        if not isinstance(res, str):

            self.__store_results(res,store=True)


            message = "Advanced simulation successfully from {0}s to {1}s.".format(self.start_time,
                                                                                   self.start_time + self.step)
            # Advance start time
            self.start_time = self.final_time_itr
            # Get full current state
            payload = self._get_full_current_state()
            logging.info(message)
            return status, message, payload
        else:
            # Errors in the simulation
            status = 500
            message = "Failed to advance simulation: {}.".format(res)
            payload = res
            logging.error(message)
            return status, message, payload

    def get_step(self):
        '''Returns the current control step in seconds.

        Parameters
        ----------
        None

        Returns
        -------
        status: int
            Indicates whether a request for querying the control step has been completed.
            If 200, the step was successfully queried.
            If 500, an internal error occurred.
        message: str
            Includes detailed debugging information.
        payload: int
            The current control step.
            None if error during query.

        '''

        status = 200
        message = "Queried the control step successfully."
        payload = None
        try:
            payload = self.step
            logging.info(message)
        except:
            status = 500
            message = "Failed to query the simulation step: {}".format(traceback.format_exc())
            logging.error(message)

        return status, message, payload

    def set_step(self,step):
        '''Sets the control step in seconds.

        Parameters
        ----------
        step: int or float
            Control step in seconds.

        Returns
        -------
        status: int
            Indicates whether a request for setting the control step has been completed.
            If 200, the step was successfully set.
            If 400, an invalid simulation step (non-numeric) was identified.
            If 500, an internal error occurred.
        message: str
            Includes detailed debugging information.
        payload:
            None

        '''

        status = 200
        message = "Control step set successfully."
        payload = None
        try:
            step = float(step)
        except:
            payload = None
            status = 400
            message = "Invalid value {} for parameter step. Value must be a float, integer, or string able to be converted to a float, but is {}.".format(step, type(step))
            logging.error(message)
            return status, message, payload
        if step < 0:
            payload = None
            status = 400
            message = "Invalid value {} for parameter step. Value must not be negative.".format(step)
            logging.error(message)
            return status, message, payload
        if step%300!=0:
            payload = None
            status = 400
            message = "Invalid value {} for parameter step. Value must be a multiple of 300 or 0. For example, valid values include 0, 300, 600, 900, etc.".format(step)
            logging.error(message)
            return status, message, payload
        try:
            self.step = step
        except:
            payload = None
            status = 500
            message = "Failed to set the control step: {}".format(traceback.format_exc())
            logging.error(message)
            return status, message, payload
        payload={'step':self.step}
        logging.info(message)

        return status, message, payload
        
    def get_inputs(self):
        '''Returns a dictionary of control inputs and their meta-data.

        Parameters
        ----------
        None

        Returns
        -------
        status: int
            Indicates whether a request for querying the inputs has been completed.
            If 200, the inputs were successfully queried.
            If 500, an internal error occurred.
        message: str
            Includes detailed debugging information.
        payload: dict
            Dictionary of control inputs and their meta-data.
            Returns None if error in getting inputs and meta-data.

        '''

        status = 200
        message = "Queried the inputs successfully."
        payload = None
        try:
            payload = self.inputs_metadata
            logging.info(message)
        except:
            status = 500
            message = "Failed to query the input list: {}".format(traceback.format_exc())
            logging.error(message)

        return status, message, payload
        
    def get_measurements(self):
        '''Returns a dictionary of measurements and their meta-data.

        Parameters
        ----------
        None

        Returns
        -------
        status: int
            Indicates whether a request for querying the outputs has been completed.
            If 200, the outputs were successfully queried.
            If 500, an internal error occurred.
        message: str
            Includes detailed debugging information.
        payload : dict
            Dictionary of measurements and their meta-data.
            Returns None if error in getting measurements and meta-data.

        '''

        status = 200
        message = "Queried the measurements successfully."
        payload = None
        try:
            payload = self.outputs_metadata
            logging.info(message)
        except:
            status = 500
            message = "Failed to query the measurement list: {}".format(traceback.format_exc())
            logging.error(message)

        return status, message, payload
        
    def get_results(self, point_names, start_time, final_time):
        '''Returns measurement and control input trajectories.

        Parameters
        ----------
        point_names: list
            Variable names.
        start_time : int or float
            Start time of data to return in seconds.
        final_time : int or float
            Start time of data to return in seconds.

        Returns
        -------
        status: int
            Indicates whether a request for querying the results has been completed.
            If 200, the results were successfully queried.
            If 400, invalid start time and/or invalid final time (non-numeric) were identified.
            If 500, an internal error occured.
        message: str
            Includes detailed debugging information.
        payload : dict
            Dictionary of variable trajectories with time as lists.
            {'time':[<time_data>],
             'var':[<var_data>]
            }
            Returns None if no variable can be found or a simulation error occurs.

        '''
        status = 200
        try:
            start_time=float(start_time)
        except:
            payload=None
            status=400
            message="Invalid value {} for parameter start time. Value must be float, integer, or string able to be converted to a float, but is {}.".format(start_time,type(start_time))
            logging.error(message)
            return status,message,payload
        try:
            final_time=float(final_time)
        except:
            payload=None
            status=400
            message="Invalid value {} for parameter start time. Value must be float, integer, or string able to be converted to a float, but is {}.".format(final_time,type(final_time))
            logging.error(message)
            return status,message,payload
        payload={}
        try:
            for point_name in point_names:
                # Get correct points
                if point_name in self.y_store.keys():
                    payload[point_name]=self.y_store[point_name]
                elif point_name in self.u_store.keys():
                    payload[point_name]=self.u_store[point_name]
                else:
                    status=400
                    message="Invalid point name {} in parameter point_names. Check lists of available inputs and measurements.".format(point_name)
                    logging.error(message)
                    return status,message,None
            if any(item in point_names for item in self.y_store.keys()):
                payload['time']=self.y_store['time']
            elif any(item in point_names for item in self.u_store.keys()):
                payload['time']=self.u_store['time']
            # Get correct time
            if payload and 'time' in payload:
                # Find min and max time
                min_t=min(payload['time'])
                max_t=max(payload['time'])
                # If min time is before start time
                if min_t<start_time:
                    # Check if start time in time array
                    if start_time in payload['time']:
                        t1=start_time
                    # Otherwise, find first time in time array after start time
                    else:
                        np_t=np.array(payload['time'])
                        t1=np_t[np_t>=start_time][0]
                # Otherwise, first time is min time
                else:
                    t1=min_t

                # If max time is after final time
                if max_t>final_time:
                    # Check if final time in time array
                    if final_time in payload['time']:
                        t2=final_time
                    # Otherwise, find last time in time array before final time
                    else:
                        np_t=np.array(payload['time'])
                        t2=np_t[np_t<=final_time][-1]
                else:
                    t2=max_t
                # Use found first and last time to find corresponding indecies
                i1=payload['time'].index(t1)
                i2=payload['time'].index(t2)+1
                for key in (point_names+['time']):
                    payload[key]=payload[key][i1:i2]
        except:
            status=500
            message="Failed query simulation results: {}".format(traceback.format_exc())
            logging.error(message)
            return status,message,None

        if not isinstance(payload,(list,type(None))):
            for key in payload:
                payload[key]=payload[key].tolist()
        message="Queried results data succesfully for point names {}.".format(point_names)
        logging.info(message)
        return status,message,payload

    def get_version(self):
        '''Returns the version number of AlphaDataCenterCooling_Gym.

        Parameters
        ----------
        None

        Returns
        -------
        status: int
            Indicate whether a request for querying the version number of AlphaDataCenterCooling_Gym has been completed.
            If 200, the version was successfully queried.
            If 500, an internal error occurred.
        message: str
            Includes detailed debugging information
        payload:  dict
            Version of AlphaDataCenterCooling_Gym as {'version': <str>}

        '''

        status = 200
        message = "Queried the version number successfully."
        logging.info(message)
        payload = {'version': self.version}

        return status, message, payload

    def _get_var_metadata(self, fmu, var_list, inputs=False):
        '''Build a dictionary of variables and their metadata.

        Parameters
        ----------
        fmu : pyfmi fmu object
            FMU from which to get variable metadata
        var_list : list of str
            List of variable names

        Returns
        -------
        var_metadata : dict
            Dictionary of variable names as keys and metadata as fields.
            {<var_name_str> :
                "Unit" : str,
                "Description" : str,
                "Minimum" : float,
                "Maximum" : float
            }

        '''

        # Inititalize
        var_metadata = dict()
        # Get metadata
        for var in var_list:
            # Units
            if var == 'time':
                unit = 's'
                description = 'Time of simulation'
                mini = None
                maxi = None
            elif '_activate' in var:
                unit = None
                if FMPY_AVAILABLE and hasattr(fmu, 'modelVariables'):
                    # FMPy model description
                    var_obj = next((v for v in fmu.modelVariables if v.name == var), None)
                    description = var_obj.description if var_obj and var_obj.description else var
                else:
                    # PyFMI fmu object
                    description = fmu.get_variable_description(var)
                mini = None
                maxi = None
            else:
                unit = None
                if FMPY_AVAILABLE and hasattr(fmu, 'modelVariables'):
                    # FMPy model description
                    var_obj = next((v for v in fmu.modelVariables if v.name == var), None)
                    description = var_obj.description if var_obj and var_obj.description else var
                else:
                    # PyFMI fmu object
                    description = fmu.get_variable_description(var)

                if inputs:
                    mini = None
                    maxi =None
                else:
                    mini = None
                    maxi = None
            # var_metadata[var] = {'Unit':unit,
            #                      'Description':description,
            #                      'Minimum':mini,
            #                      'Maximum':maxi}
            var_metadata[var] = {'Description': description}

        return var_metadata

    def get_name(self):
        '''Returns the name of the test case fmu.

        Parameters
        ----------
        None

        Returns
        -------
        status: int
            Indicate whether a request for querying the name of the test case has been successfully completed.
            If 200, the name was successfully queried.
            If 500, an internal error occurred.
        message: str
            Includes detailed debugging information
        payload :  dict
            Name of test case as {'name': <str>}

        '''

        status = 200
        message = "Queried the name of the test case successfully."
        payload = {'name': self.name}
        logging.info(message)

        return status, message, payload

    def _get_full_current_state(self):
        '''Combines the self.y and self.u dictionaries into one.

        Returns
        -------
        z: dict
            Combination of self.y and self.u dictionaries.

        '''

        z = self.y.copy()
        z.update(self.u)

        # Convert numpy types to Python native types for JSON serialization
        for key, value in z.items():
            if hasattr(value, 'item'):  # numpy scalar
                z[key] = value.item()
            elif hasattr(value, 'tolist'):  # numpy array
                z[key] = value.tolist()
            elif isinstance(value, (np.bool_, np.int_, np.float_)):
                z[key] = value.item()

        return z

    def __store_results(self,res,store=False):
        for key in self.y.keys():
            self.y[key] = res[key][-1]
            if store:
                self.y_store[key].append(res[key][-1])
        # Store control inputs
        for key in self.u.keys():
            self.u[key] = res[key][-1]
            if store:
                self.u_store[key].append(res[key][-1])


