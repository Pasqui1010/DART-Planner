DART-Planner API Reference
==========================

Welcome to the DART-Planner API documentation. This reference provides comprehensive documentation for all public APIs, classes, and modules in the DART-Planner autonomous drone navigation system.

.. toctree::
   :maxdepth: 2
   :caption: Core Components

   control/index
   planning/index
   hardware/index
   common/index

.. toctree::
   :maxdepth: 2
   :caption: Architecture

   edge/index
   cloud/index
   neural_scene/index

.. toctree::
   :maxdepth: 2
   :caption: Utilities

   utils/index
   communication/index

.. toctree::
   :maxdepth: 2
   :caption: Examples

   examples/index

.. autosummary::
   :toctree: .
   :recursive:

   dart_planner

Overview
--------

DART-Planner is organized into several key modules:

**Core Control System**
   - :doc:`control/index` - Geometric controllers and tuning
   - :doc:`planning/index` - SE(3) MPC planners and trajectory optimization

**Hardware Integration**
   - :doc:`hardware/index` - AirSim and PX4 interfaces
   - :doc:`communication/index` - ZMQ communication protocols

**Architecture Layers**
   - :doc:`edge/index` - Onboard autonomous operation
   - :doc:`cloud/index` - Cloud-based mission planning
   - :doc:`neural_scene/index` - Neural scene representation

**Utilities**
   - :doc:`utils/index` - Simulation and testing utilities
   - :doc:`common/index` - Shared data types and constants

Quick Start
-----------

Here's a minimal example to get you started:

.. code-block:: python

   from src.control.geometric_controller import GeometricController
   from src.planning.se3_mpc_planner import SE3MPCPlanner
   from src.hardware.airsim_interface import AirSimInterface

   # Initialize components
   controller = GeometricController(tuning_profile="sitl_optimized")
   planner = SE3MPCPlanner()
   airsim = AirSimInterface()

   # Execute autonomous mission
   mission = Mission(waypoints=[(0, 0, 10), (10, 0, 10), (10, 10, 10)])
   airsim.execute_mission(mission, controller, planner)

For more detailed examples, see the :doc:`examples/index` section.

Installation
------------

Install DART-Planner and its dependencies:

.. code-block:: bash

   pip install .
   pip install "[.dev]"

For development setup, see the :doc:`../README` file.

Contributing
------------

We welcome contributions! Please see our :doc:`../CONTRIBUTING` guide for details on:

- Code style and formatting
- Testing requirements
- Pull request process
- Development setup

License
-------

DART-Planner is released under the MIT License. See the :doc:`../LICENSE` file for details. 