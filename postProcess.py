import pandas as pd
import matplotlib.pyplot as plt

data = pd.read_csv('../data/bkm_integral.csv')
plt.figure(figsize=(8, 6))
colors = {
    'turbulentFlow': 'blue',
    'vortexRing': 'green',
    'kolmogorovFlow': 'red',
    'oscillatoryFlow': 'purple',
    'extremeGradientFlow': 'cyan',
    'nonPeriodicFlow': 'yellow',
    'turbulentFlow_s13': 'gray'
}
for case in data['Case'].unique():
    case_data = data[data['Case'] == case]
    plt.errorbar(case_data['Re'], case_data['BKM_Integral'], yerr=case_data['Error'], 
                 fmt='o', color=colors[case], label=case.replace('_', ' ').title())
plt.plot([100, 1000000], [6, 600], color='orange', label='Fit: 0.6 Re^0.5')
plt.xscale('log')
plt.yscale('log')
plt.xlabel('Reynolds Number (Re)')
plt.ylabel('∫₀¹⁰ ||ω||_L∞ dt')
plt.title('BKM Integral vs. Reynolds Number')
plt.legend()
plt.grid(True)
plt.savefig('../docs/bkm_plot.png')
plt.close()

# Placeholder for beta_j results
try:
    beta_data = pd.read_csv('../data/beta_j_results.csv')
    print("Beta_j results:")
    print(beta_data)
except FileNotFoundError:
    print("beta_j_results.csv not found. Run simulations to generate.")
