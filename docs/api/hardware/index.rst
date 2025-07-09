Hardware Integration
====================

The hardware integration system provides interfaces for AirSim simulation and PX4 flight controllers.

.. toctree::
   :maxdepth: 2

   airsim_interface
   airsim_adapter
   px4_interface
   motor_mixer

Overview
--------

The hardware integration system provides seamless interfaces between DART-Planner and various hardware platforms, including simulation environments and real flight controllers.

Key Features
------------

- **AirSim Integration**: Full AirSim simulation support
- **PX4 Interface**: Direct PX4 flight controller communication
- **Motor Mixing**: Advanced motor mixing algorithms
- **Hardware Abstraction**: Platform-independent hardware interfaces

Core Components
---------------

AirSim Interface
~~~~~~~~~~~~~~~

The main AirSim interface for simulation:

.. automodule:: src.hardware.airsim_interface
   :members:
   :undoc-members:
   :show-inheritance:

AirSim Adapter
~~~~~~~~~~~~~

AirSim adapter for hardware abstraction:

.. automodule:: src.hardware.airsim_adapter
   :members:
   :undoc-members:
   :show-inheritance:

PX4 Interface
~~~~~~~~~~~~

PX4 flight controller interface:

.. automodule:: src.hardware.px4_interface
   :members:
   :undoc-members:
   :show-inheritance:

Motor Mixer
~~~~~~~~~~

Advanced motor mixing algorithms:

.. automodule:: src.hardware.motor_mixer
   :members:
   :undoc-members:
   :show-inheritance: 