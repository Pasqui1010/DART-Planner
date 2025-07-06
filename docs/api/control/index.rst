Control System
==============

The control system provides geometric controllers and tuning management for autonomous drone flight.

.. toctree::
   :maxdepth: 2

   geometric_controller
   control_config
   trajectory_smoother

Overview
--------

The control system implements geometric controllers designed specifically for quadrotor dynamics, with comprehensive tuning profiles and trajectory smoothing capabilities.

Key Features
------------

- **Geometric Controllers**: SE(3) aware controllers for proper aerial robotics
- **Tuning Profiles**: Pre-configured and customizable controller gains
- **Trajectory Smoothing**: Smooth, continuous trajectory generation
- **Performance Monitoring**: Real-time performance tracking and optimization

Core Components
---------------

Geometric Controller
~~~~~~~~~~~~~~~~~~~

The main controller class that implements geometric control for quadrotors:

.. automodule:: src.control.geometric_controller
   :members:
   :undoc-members:
   :show-inheritance:

Control Configuration
~~~~~~~~~~~~~~~~~~~~

Tuning profiles and configuration management:

.. automodule:: src.control.control_config
   :members:
   :undoc-members:
   :show-inheritance:

Trajectory Smoother
~~~~~~~~~~~~~~~~~~

Smooth trajectory generation and optimization:

.. automodule:: src.control.trajectory_smoother
   :members:
   :undoc-members:
   :show-inheritance:

Usage Examples
--------------

Basic Controller Usage
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from src.control.geometric_controller import GeometricController
   from src.common.types import DroneState, ControlCommand

   # Initialize controller with optimized tuning
   controller = GeometricController(tuning_profile="sitl_optimized")

   # Get control command for current state
   current_state = DroneState(
       position=np.array([0.0, 0.0, 10.0]),
       velocity=np.zeros(3),
       attitude=np.zeros(3),
       angular_velocity=np.zeros(3)
   )

   desired_state = DroneState(
       position=np.array([10.0, 0.0, 10.0]),
       velocity=np.zeros(3),
       attitude=np.zeros(3),
       angular_velocity=np.zeros(3)
   )

   control_cmd = controller.compute_control(current_state, desired_state)

Custom Tuning Profile
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from src.control.control_config import ControllerTuningProfile, ControllerTuningManager
   import numpy as np

   # Create custom tuning profile
   custom_profile = ControllerTuningProfile(
       name="custom_aggressive",
       description="Aggressive tuning for fast maneuvers",
       kp_pos=np.array([25.0, 25.0, 30.0]),
       ki_pos=np.array([2.0, 2.0, 2.5]),
       kd_pos=np.array([12.0, 12.0, 14.0]),
       kp_att=np.array([20.0, 20.0, 8.0]),
       kd_att=np.array([8.0, 8.0, 3.5]),
       ff_pos=2.0,
       ff_vel=1.5,
       ff_acc=0.5,
       max_velocity=15.0,
       max_acceleration=8.0,
       max_angular_velocity=3.0,
       position_threshold=0.1,
       velocity_threshold=0.05,
       attitude_threshold=0.05
   )

   # Use custom profile
   controller = GeometricController(tuning_profile=custom_profile)

Performance Tuning
~~~~~~~~~~~~~~~~~

.. code-block:: python

   from src.control.control_config import get_controller_config

   # Get tuning manager
   tuning_manager = get_controller_config()

   # Compare different profiles
   tuning_manager.print_tuning_comparison([
       "original",
       "sitl_optimized", 
       "tracking_optimized"
   ])

   # Get specific profile
   profile = tuning_manager.get_profile("precision_tracking")
   print(f"Position gains: {profile.kp_pos}") 