# Motor Mixing Safety Guide

This document summarises the safety mechanisms, failure‐detection logic, and
recommended pre-flight checks for the quadrotor motor-mixer subsystem.

## 1. Configuration Validation

* A Pydantic schema (`MotorMixingModel`) validates the *motor_mixing* section in
  `config/hardware.yaml`.  Any typo, out-of-range parameter, or shape mismatch
  raises a `ValidationError` at start-up.
* Critical fields:
  * `layout`, `motor_positions`, `motor_directions`
  * `pwm_*` limits + `pwm_scaling_factor`
  * Physical coefficients (`thrust_coefficient`, `torque_coefficient`)

## 2. Runtime Guards

| Check | Condition | Action |
|-------|-----------|--------|
| **Non-finite detection** | `np.isfinite(motor_thrusts).all()` | Raise `RuntimeError` |
| **Pre-clip overrun** | Any raw PWM > 110 % of `pwm_max` | Log *warning*, continue with saturation |
| **Idle-while-thrust** | All motors saturated to `pwm_idle` while requested thrust > 0.2 N | Log *error* │ possible actuator fault |

## 3. Saturation Metrics

* `saturation_events` counter increments every time clipping modifies a PWM
  command.
* Call `reset_saturation_counter()` between mission phases or tests to keep
  statistics meaningful.

## 4. Pre-flight Procedure

1. **Schema Validation** – Load `hardware.yaml` and run `MotorMixingModel`.
2. **Self-Test** – Run `MotorMixer.validate_configuration()`; no issues expected.
3. **Idle Spin Check** – Arm motors, confirm RPM > 0 at `pwm_idle`.
4. **Low-Throttle Lift Test** – Apply 10 % collective thrust; vehicle should
   start unloading weight but remain grounded.
5. **Full-Range Sweep** – Slowly ramp thrust 0 → 100 % while monitoring for
   saturation warnings; no *idle-while-thrust* errors should appear.
6. **Torque Excursions** – Inject ±0.5 N·m roll/pitch/yaw commands; verify
   motor PWMs diverge as expected and remain within limits.

## 5. Failure Modes & Mitigations

| Failure Mode | Detection | Mitigation |
|--------------|-----------|------------|
| ESC signal lost | Idle-while-thrust error | Auto-land / shut-down |
| Config typo | Schema `ValidationError` | Block start-up |
| Command NaN | Runtime `RuntimeError` | Emergency stop |
| Motor PWM clipping | Saturation counter > threshold | Reduce demand / land |

## 6. Future Enhancements

* Lookup-table or quadratic thrust↔PWM model with calibration data.
* Rolling window statistics and flight-data recorder integration.
* Online motor health estimation using current draw and RPM feedback. 