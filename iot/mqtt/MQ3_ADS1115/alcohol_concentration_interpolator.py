import numpy as np
from scipy.interpolate import PchipInterpolator

class AlcoholConcentrationInterpolator:
    def __init__(self):
        # Data points from the original dataset (concentration in mg/L and Rs/Ro), reversed for increasing order
        self.concentration = np.array([10, 4, 2, 1, 0.5, 0.2, 0.1])  # mg/L
        self.rs_ro_ratio = np.array([0.11, 0.2, 0.33, 0.53, 0.9, 1.7, 2.1])  # Rs/Ro

        # Create a monotonic PCHIP interpolator
        self.interpolator = PchipInterpolator(self.rs_ro_ratio, self.concentration)

    def get_concentration(self, rs_ro_value):
        """
        Given an Rs/Ro value, returns the estimated concentration (mg/L) of alcohol.

        Parameters:
            rs_ro_value (float): The Rs/Ro ratio value.

        Returns:
            float: Estimated concentration in mg/L.
        """
        # Use the PCHIP interpolator to estimate the concentration
        return self.interpolator(rs_ro_value)

