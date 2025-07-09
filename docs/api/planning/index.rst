Planning System
===============

The planning system provides SE(3) MPC planners and trajectory optimization for autonomous drone navigation.

.. toctree::
   :maxdepth: 2

   base_planner
   cloud_planner
   edge_planner
   se3_mpc_planner

Overview
--------

The planning system implements SE(3) Model Predictive Control (MPC) planners designed specifically for quadrotor dynamics, with support for both cloud-based and edge-based planning architectures.

Key Features
------------

- **SE(3) MPC**: Proper aerial robotics planning algorithms
- **Cloud Planning**: Centralized mission planning and optimization
- **Edge Planning**: Onboard autonomous planning capabilities
- **Trajectory Optimization**: Real-time trajectory generation and smoothing

Core Components
---------------

Base Planner
~~~~~~~~~~~

The base planner interface that defines the planning contract:

.. automodule:: src.planning.base_planner
   :members:
   :undoc-members:
   :show-inheritance:

Cloud Planner
~~~~~~~~~~~~

Cloud-based planning for complex mission optimization:

.. automodule:: src.planning.cloud_planner
   :members:
   :undoc-members:
   :show-inheritance:

Edge Planner
~~~~~~~~~~~

Onboard autonomous planning for real-time operation:

.. automodule:: src.planning.edge_planner
   :members:
   :undoc-members:
   :show-inheritance:

SE(3) MPC Planner
~~~~~~~~~~~~~~~~

The core SE(3) Model Predictive Control planner:

.. automodule:: src.planning.se3_mpc_planner
   :members:
   :undoc-members:
   :show-inheritance: 