from typing import Optional

import numpy as np


class PIDController:
    """A simple Proportional-Integral-Derivative controller."""

    def __init__(
        self,
        Kp: float,
        Ki: float,
        Kd: float,
        setpoint: float = 0.0,
        integral_limit: Optional[float] = None,
    ) -> None:
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = setpoint
        self.integral = 0.0
        self.last_error = 0.0
        self.integral_limit = integral_limit

    def update(self, measured_value: float, dt: float) -> float:
        """Calculate the control variable."""
        if dt <= 0:
            return 0.0

        error = self.setpoint - measured_value

        # Proportional term
        P_out = self.Kp * error

        # Integral term
        self.integral += error * dt
        if self.integral_limit:
            self.integral = np.clip(
                self.integral, -self.integral_limit, self.integral_limit
            )
        I_out = self.Ki * self.integral

        # Derivative term
        derivative = (error - self.last_error) / dt if dt > 0 else 0.0
        D_out = self.Kd * derivative

        # Total output
        output = P_out + I_out + D_out

        self.last_error = error
        return output

    def reset(self) -> None:
        self.integral = 0.0
        self.last_error = 0.0
