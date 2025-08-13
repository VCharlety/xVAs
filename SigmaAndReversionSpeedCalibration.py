import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt

def estimate_hull_white_params(rates: pd.Series, dt: float):
    """
    Estimates Hull-White model parameters (a, mu, sigma) from a time series of short rates
    using Ordinary Least Squares (OLS) on the discretized model.

    The discretized model is:
    r(t_i+1) = c + b * r(t_i) + error
    where:
    b = 1 - a * dt
    c = a * mu * dt

    From which we derive the annualized parameters:
    a = (1 - b) / dt
    mu = c / (a * dt) = c / (1 - b)
    sigma = std(residuals) / sqrt(dt)

    Args:
        rates (pd.Series): A time series of short-term interest rates.
        dt (float): The time step in years (e.g., 1/252 for daily, 1/12 for monthly).

    Returns:
        tuple: A tuple containing the estimated (a, mu, sigma).
    """
    # Prepare the data for regression
    # y = r(t_i+1)
    y = rates.iloc[1:].values
    # x = r(t_i)
    x = rates.iloc[:-1].values

    # Add a constant (intercept) to the independent variable
    x_with_const = sm.add_constant(x)

    # Perform the OLS regression
    model = sm.OLS(y, x_with_const)
    results = model.fit()

    # Extract coefficients from the fitted model
    c, b = results.params

    # Volatility 'sigma'
    # Get the standard deviation of the residuals
    residuals_std = np.std(results.resid)
    sigma = residuals_std / np.sqrt(dt)

    # Check for non-mean-reverting behavior in the data
    if b >= 1.0:
        print("\n--- WARNING: Non-Mean-Reverting Data Detected ---")
        print(f"The regression slope 'b' is {b:.4f}, which is >= 1.")
        print("This indicates the historical data does not exhibit mean reversion and may have a strong trend.")
        print("As a result, the calculated mean reversion speed 'a' will be negative, which is financially unsound for this model.")
        print("The long-term mean 'mu' is not well-defined in this case.")
        print("Consider using a different historical period for calibration or a different model.\n")
        a = (1 - b) / dt
        mu = np.nan  # mu is not meaningful for a non-reverting process
    else:
        # Standard case for mean-reverting data
        a = (1 - b) / dt
        mu = c / (1 - b)

    return a, mu, sigma

if __name__ == '__main__':
    # --- Example 1: Estimation from Simulated Data (Correct Usage) ---
    # This example shows how the function works with ideal, mean-reverting data.
    # Known parameters
    a_true = 0.20      # Mean reversion speed
    mu_true = 0.04     # Long-run mean (4%)
    sigma_true = 0.015 # Volatility
    r0 = 0.02          # Initial rate (2%)
    T = 15             # 15 years
    N = 252 * T        # Number of daily steps
    dt_daily = 1/252   # Time step (daily)

    # Simulate the rate path using an exact discretization for accuracy
    rates_sim = [r0]
    for _ in range(N - 1):
        prev_r = rates_sim[-1]
        # The term theta(t)/a is our mu
        new_r = prev_r * np.exp(-a_true * dt_daily) + mu_true * (1 - np.exp(-a_true * dt_daily)) + \
                sigma_true * np.sqrt((1 - np.exp(-2 * a_true * dt_daily)) / (2 * a_true)) * np.random.normal()
        rates_sim.append(new_r)

    simulated_rates = pd.Series(rates_sim)

    # Estimate parameters from the simulated data
    a_est, mu_est, sigma_est = estimate_hull_white_params(simulated_rates, dt_daily)

    print("--- Parameter Estimation from Simulated Data ---")
    print(f"True parameters:      a = {a_true:.4f}, mu = {mu_true:.4f}, sigma = {sigma_true:.4f}")
    print(f"Estimated parameters: a = {a_est:.4f}, mu = {mu_est:.4f}, sigma = {sigma_est:.4f}")
    print("\nNote: The estimated parameters should be reasonably close to the true parameters.")

    # --- Example 2: Applying to Real Historical Data (Template) ---
    # The following block demonstrates how to apply this to your own historical data.
    # It is commented out because we don't have the historical data file.
    
    # IMPORTANT: You correctly identified that using a forward curve ('ForwardData.csv') is not the
    # right approach for this historical calibration. The OLS method requires a TIME SERIES of a
    # single short-term interest rate (e.g., 3-month EURIBOR, SOFR, T-Bill rate) over time.

    try:
        # 1. Load your historical data from 'Historical Levels.CSV'
        # We specify the separator, tell pandas to parse the 'Date' column as dates and use it as the index.
        hist_data = pd.read_csv(
            'Historical Levels.CSV',
            sep=',',
            index_col='Date',
            parse_dates=True,
            # dayfirst=True  # Assuming DD/MM/YYYY format, change if not the case
        )

        # 2. Select the correct column and prepare the data
        # Ensure rates are numeric and in decimal form (e.g., 3.0 -> 0.03)
        hist_rates = pd.to_numeric(hist_data['EUR Swap Euribor 3M'], errors='coerce') / 100.0
        hist_rates.sort_index(inplace=True)  # Ensure data is in chronological order
        hist_rates.dropna(inplace=True)      # Remove any missing values
        
        # 3. Define the time step based on data frequency. Assuming daily business day data.
        # If your data is weekly, use 1/52. If monthly, use 1/12.
        dt_hist = 1/252
        
        # 4. Plot the data to visually check for stationarity/trends
        hist_rates.plot(title='Historical EUR Swap Euribor 3M', grid=True, figsize=(12, 6))
        plt.show()
        
        # 5. Estimate parameters
        a_real, mu_real, sigma_real = estimate_hull_white_params(hist_rates, dt=dt_hist)
        print("\n--- Estimated Parameters from 'Historical Levels.CSV' ---")
        print(f"Mean Reversion (a): {a_real:.4f}, Long-Run Mean (mu): {mu_real:.4f}, Volatility (sigma): {sigma_real:.4f}")
    
    except FileNotFoundError:
        print("\nCould not find 'Historical Levels.CSV'. Skipping real data estimation example.")
    except KeyError:
        print("\nError: Could not find the required columns ('Date', 'EUR Swap Euribor 3M') in the CSV.")
        print("Please check the column names in 'Historical Levels.CSV'.")
