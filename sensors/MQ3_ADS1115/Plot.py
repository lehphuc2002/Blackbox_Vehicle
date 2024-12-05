# -*- coding: utf-8 -*-
import numpy as np
import matplotlib.pyplot as plt
from alcohol_concentration_interpolator import AlcoholConcentrationInterpolator


interpolator = AlcoholConcentrationInterpolator()


rs_ro_values = np.linspace(0.1, 2.2, 100)  
concentration_values = interpolator.get_concentration(rs_ro_values)


original_rs_ro = np.array([0.11, 0.2, 0.33, 0.53, 0.9, 1.7, 2.1])
original_concentration = np.array([10, 4, 2, 1, 0.5, 0.2, 0.1])


plt.figure(figsize=(8, 6))
plt.plot(original_rs_ro, original_concentration, 'ro', label='Original Data Points')
plt.plot(rs_ro_values, concentration_values, 'b-', label='Interpolated Curve')


plt.xscale('log')
plt.yscale('log')
plt.xlabel('Rs/Ro')
plt.ylabel('Concentration (mg/L)')
plt.title('Alcohol Concentration Interpolation')
plt.legend()
plt.grid(True, which="both", linestyle="--")
plt.show()
