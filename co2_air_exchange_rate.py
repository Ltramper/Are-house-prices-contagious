#!/usr/bin/env python3
"""
CO2 Decay Air Exchange Rate Calculator

Calculates the air exchange rate (ACH) of a room by fitting an exponential
decay model to CO2 concentration measurements taken after occupants leave.

Usage:
    python co2_air_exchange_rate.py

Requirements:
    - Python 3.7+
    - numpy, scipy, matplotlib
"""

import sys
import math
import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt


# Sensor uncertainty in ppm
SENSOR_UNCERTAINTY_PPM = 50

# Suggested measurement times in minutes after leaving the room
SUGGESTED_TIMES_MINUTES = [2, 7, 15, 30, 50, 75, 105]

# Minimum number of measurements for a reliable fit
MIN_MEASUREMENTS = 3

# Minimum excess CO2 above outdoor level to consider the measurement valid (ppm)
MIN_EXCESS_PPM = 100

# Average CO2 emission rate of a person at rest (m³ CO2 per hour)
# Approximately 0.005 m³/h ≈ 200 mL/min exhaled CO2
HUMAN_CO2_EMISSION_RATE = 0.005


def co2_decay_model(t_hours, c_initial_excess, ach):
    """
    Model for CO2 decay: excess CO2 above outdoor level decays exponentially.

    C(t) - C_outdoor = (C_initial - C_outdoor) * exp(-ACH * t)

    Parameters
    ----------
    t_hours : array-like
        Time in hours since start of measurement.
    c_initial_excess : float
        Initial excess CO2 above outdoor level (ppm).
    ach : float
        Air changes per hour.

    Returns
    -------
    array-like
        Excess CO2 concentration (ppm) above outdoor level at each time.
    """
    return c_initial_excess * np.exp(-ach * t_hours)


def get_positive_float(prompt, min_val=None, max_val=None):
    """Prompt the user for a positive float within optional bounds."""
    while True:
        try:
            value = float(input(prompt))
            if value <= 0:
                print("Please enter a positive number.")
                continue
            if min_val is not None and value < min_val:
                print(f"Value must be at least {min_val}.")
                continue
            if max_val is not None and value > max_val:
                print(f"Value must be at most {max_val}.")
                continue
            return value
        except ValueError:
            print("Invalid input. Please enter a number.")


def get_positive_int(prompt, min_val=1, max_val=None):
    """Prompt the user for a positive integer within optional bounds."""
    while True:
        try:
            value = int(input(prompt))
            if value < min_val:
                print(f"Value must be at least {min_val}.")
                continue
            if max_val is not None and value > max_val:
                print(f"Value must be at most {max_val}.")
                continue
            return value
        except ValueError:
            print("Invalid input. Please enter a whole number.")


def calculate_r_squared(y_observed, y_predicted):
    """Calculate the coefficient of determination (R²)."""
    ss_res = np.sum((y_observed - y_predicted) ** 2)
    ss_tot = np.sum((y_observed - np.mean(y_observed)) ** 2)
    if ss_tot == 0:
        return 0.0
    return 1.0 - (ss_res / ss_tot)


def estimate_ach_uncertainty(times_hours, excess_co2, ach_fit, c0_fit, c_outdoor):
    """
    Estimate uncertainty in ACH from sensor uncertainty propagation.

    Uses a Monte Carlo approach: perturb each measurement by the sensor
    uncertainty and refit, then report the standard deviation of ACH values.
    """
    n_simulations = 1000
    rng = np.random.default_rng(seed=42)
    ach_samples = []

    for _ in range(n_simulations):
        # Add random noise within sensor uncertainty
        noise = rng.normal(0, SENSOR_UNCERTAINTY_PPM, size=len(excess_co2))
        perturbed_co2 = excess_co2 + noise

        # Ensure all perturbed values remain positive
        perturbed_excess = perturbed_co2
        if np.any(perturbed_excess <= 0):
            continue

        try:
            popt, _ = curve_fit(
                co2_decay_model,
                times_hours,
                perturbed_excess,
                p0=[c0_fit, ach_fit],
                bounds=([0, 0], [np.inf, 50]),
                maxfev=5000,
            )
            ach_samples.append(popt[1])
        except (RuntimeError, ValueError):
            continue

    if len(ach_samples) < 100:
        return float("nan")

    return float(np.std(ach_samples))


def collect_measurements(mode_name, c_outdoor):
    """
    Guide the user through taking CO2 measurements for one ventilation mode.

    Returns
    -------
    times_minutes : list of float
        Times in minutes since all people left.
    co2_readings : list of float
        CO2 readings in ppm.
    """
    print(f"\n{'='*60}")
    print(f"  MEASUREMENT SESSION: {mode_name}")
    print(f"{'='*60}")
    print()
    print("PREPARATION:")
    print(f"  1. Close all doors and windows.")
    print(f"  2. Ensure the CO2 level is above {c_outdoor + 400:.0f} ppm")
    print(f"     (at least {c_outdoor + MIN_EXCESS_PPM:.0f} ppm, ideally above "
          f"{c_outdoor + 600:.0f} ppm).")
    print(f"  3. Set the ventilation system to: {mode_name}")
    print(f"  4. Have ALL people leave the room and close the door.")
    print()
    input("Press Enter when everyone has left the room and you are ready "
          "to start timing...")
    print()
    print("MEASUREMENT PHASE:")
    print("  Enter the room BRIEFLY (< 30 seconds), read the sensor, then")
    print("  leave immediately. Record the time and CO2 reading below.")
    print()
    print("Suggested measurement times (minutes after leaving):")
    print(f"  {SUGGESTED_TIMES_MINUTES}")
    print()

    times_minutes = []
    co2_readings = []
    measurement_num = 0

    while True:
        measurement_num += 1

        # Suggest a time for the next measurement
        if measurement_num <= len(SUGGESTED_TIMES_MINUTES):
            suggested = SUGGESTED_TIMES_MINUTES[measurement_num - 1]
            print(f"--- Measurement #{measurement_num} "
                  f"(suggested at ~{suggested} minutes) ---")
        else:
            print(f"--- Measurement #{measurement_num} (additional) ---")

        # Get time
        time_min = get_positive_float(
            "  Enter time in minutes since everyone left: ",
            min_val=0.1
        )

        # Check if this time is after the previous measurement
        if times_minutes and time_min <= times_minutes[-1]:
            print(f"  Warning: This time ({time_min} min) is not after the "
                  f"previous measurement ({times_minutes[-1]} min).")
            print(f"  Please enter a later time.")
            measurement_num -= 1
            continue

        # Get CO2 reading
        co2_ppm = get_positive_float(
            "  Enter CO2 reading (ppm): ",
            min_val=100,
            max_val=10000
        )

        times_minutes.append(time_min)
        co2_readings.append(co2_ppm)

        # Calculate excess above outdoor
        excess = co2_ppm - c_outdoor
        print(f"  -> Excess above outdoor: {excess:.0f} ppm")

        if excess < SENSOR_UNCERTAINTY_PPM:
            print(f"  -> CO2 is within sensor uncertainty of outdoor level.")
            print(f"     No more measurements needed for this mode.")
            break

        if excess < MIN_EXCESS_PPM:
            print(f"  -> CO2 is approaching outdoor level "
                  f"(excess < {MIN_EXCESS_PPM} ppm).")
            print(f"     You may stop or take one more measurement.")

        # Check if we have enough measurements
        if measurement_num >= MIN_MEASUREMENTS:
            if excess < MIN_EXCESS_PPM:
                print()
                cont = input("  Take another measurement? (y/n): ").strip().lower()
                if cont != "y":
                    break
            else:
                print()
                cont = input("  Take another measurement? (y/n, default y): "
                             ).strip().lower()
                if cont == "n":
                    break
        else:
            remaining = MIN_MEASUREMENTS - measurement_num
            print(f"  (Need at least {remaining} more measurement(s))")

        # Estimate when the next measurement should be taken
        if len(times_minutes) >= 2:
            # Quick linear regression on log(excess) to estimate decay rate
            valid = [(t, c - c_outdoor) for t, c in
                     zip(times_minutes, co2_readings) if c - c_outdoor > 0]
            if len(valid) >= 2:
                t_arr = np.array([v[0] for v in valid]) / 60.0  # hours
                log_excess = np.log([v[1] for v in valid])
                if len(t_arr) >= 2:
                    slope = ((log_excess[-1] - log_excess[0]) /
                             (t_arr[-1] - t_arr[0]))
                    if slope < 0:
                        # Estimate time to drop by ~50 ppm from current level
                        ach_est = -slope
                        current_excess = co2_readings[-1] - c_outdoor
                        target_excess = max(current_excess - 80,
                                            MIN_EXCESS_PPM)
                        if target_excess > 0 and current_excess > target_excess:
                            dt_hours = (math.log(current_excess / target_excess)
                                        / ach_est)
                            next_time = times_minutes[-1] + dt_hours * 60
                            print(f"\n  >> Suggested next measurement at "
                                  f"~{next_time:.0f} minutes")
                            print(f"     (estimated drop to ~"
                                  f"{target_excess + c_outdoor:.0f} ppm)")

        print()

    if len(times_minutes) < MIN_MEASUREMENTS:
        print(f"\nWarning: Only {len(times_minutes)} measurement(s) taken. "
              f"At least {MIN_MEASUREMENTS} are needed for a reliable fit.")
        print("Results for this mode may be unreliable.\n")

    return times_minutes, co2_readings


def fit_decay_curve(times_minutes, co2_readings, c_outdoor):
    """
    Fit the CO2 decay model to the measurements.

    Returns
    -------
    dict with keys:
        ach : float — air changes per hour
        ach_uncertainty : float — uncertainty in ACH
        c0_excess : float — fitted initial excess CO2 (ppm)
        r_squared : float — goodness of fit
        times_hours : ndarray — measurement times in hours
        excess_co2 : ndarray — measured excess CO2 (ppm)
        fitted_excess : ndarray — fitted excess CO2 (ppm)
    """
    times_hours = np.array(times_minutes) / 60.0
    co2_array = np.array(co2_readings)
    excess_co2 = co2_array - c_outdoor

    # Initial guesses
    c0_guess = excess_co2[0]
    # Rough ACH guess from first and last points
    if excess_co2[-1] > 0 and excess_co2[0] > 0:
        dt = times_hours[-1] - times_hours[0]
        if dt > 0:
            ach_guess = max(0.1,
                           -math.log(excess_co2[-1] / excess_co2[0]) / dt)
        else:
            ach_guess = 1.0
    else:
        ach_guess = 1.0

    try:
        popt, pcov = curve_fit(
            co2_decay_model,
            times_hours,
            excess_co2,
            p0=[c0_guess, ach_guess],
            bounds=([0, 0], [np.inf, 50]),
            maxfev=10000,
        )
    except RuntimeError as e:
        print(f"\nError: Could not fit decay curve: {e}")
        print("The measurements may not follow an exponential decay pattern.")
        return None

    c0_fit, ach_fit = popt
    fitted_excess = co2_decay_model(times_hours, c0_fit, ach_fit)
    r_squared = calculate_r_squared(excess_co2, fitted_excess)

    # Estimate uncertainty via Monte Carlo
    ach_unc = estimate_ach_uncertainty(
        times_hours, excess_co2, ach_fit, c0_fit, c_outdoor
    )

    return {
        "ach": float(ach_fit),
        "ach_uncertainty": ach_unc,
        "c0_excess": float(c0_fit),
        "r_squared": float(r_squared),
        "times_hours": times_hours,
        "excess_co2": excess_co2,
        "fitted_excess": fitted_excess,
    }


def print_result(mode_name, result):
    """Print the results for one ventilation mode."""
    print(f"\n  {mode_name}:")
    print(f"    Air Exchange Rate (ACH): {result['ach']:.2f} "
          f"± {result['ach_uncertainty']:.2f} changes/hour")
    print(f"    Fitted initial excess CO2: {result['c0_excess']:.0f} ppm")
    print(f"    Goodness of fit (R²): {result['r_squared']:.4f}")

    if result["r_squared"] < 0.85:
        print(f"    ⚠ Warning: Low R² indicates a poor fit. Consider retaking "
              f"measurements.")
    elif result["r_squared"] < 0.95:
        print(f"    ⚠ Note: Moderate fit quality. Results are approximate.")


def classify_ventilation(ach):
    """Return a qualitative description of the ventilation rate."""
    if ach < 0.5:
        return "Poor — inadequate ventilation"
    elif ach < 1.0:
        return "Minimal — may be acceptable for low occupancy"
    elif ach < 3.0:
        return "Moderate — typical residential mechanical ventilation"
    elif ach < 6.0:
        return "Good — well-ventilated space"
    else:
        return "Excellent — high ventilation rate"


def plot_results(results, c_outdoor):
    """
    Generate a plot of CO2 decay curves for all ventilation modes.

    Saves the plot to 'co2_decay_results.png'.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    colours = plt.cm.tab10(np.linspace(0, 1, len(results)))

    for idx, (mode_name, result) in enumerate(results.items()):
        colour = colours[idx]
        times_min = result["times_hours"] * 60

        # Left plot: CO2 concentration over time
        ax1.errorbar(
            times_min,
            result["excess_co2"] + c_outdoor,
            yerr=SENSOR_UNCERTAINTY_PPM,
            fmt="o",
            color=colour,
            label=f"{mode_name} (measured)",
            capsize=3,
            markersize=5,
        )

        # Fitted curve (smooth)
        t_smooth = np.linspace(0, times_min.max() * 1.05, 200)
        fitted_smooth = co2_decay_model(
            t_smooth / 60.0, result["c0_excess"], result["ach"]
        )
        ax1.plot(
            t_smooth,
            fitted_smooth + c_outdoor,
            "-",
            color=colour,
            alpha=0.7,
            label=f"{mode_name} (fit, ACH={result['ach']:.2f})",
        )

        # Right plot: ln(excess CO2) — linearised view
        valid_mask = result["excess_co2"] > 0
        ax2.plot(
            times_min[valid_mask],
            np.log(result["excess_co2"][valid_mask]),
            "o",
            color=colour,
            label=f"{mode_name} (measured)",
            markersize=5,
        )
        valid_fitted = result["fitted_excess"] > 0
        ax2.plot(
            times_min[valid_fitted],
            np.log(result["fitted_excess"][valid_fitted]),
            "-",
            color=colour,
            alpha=0.7,
            label=f"{mode_name} (fit)",
        )

    ax1.axhline(y=c_outdoor, color="green", linestyle="--", alpha=0.5,
                label=f"Outdoor CO2 ({c_outdoor:.0f} ppm)")
    ax1.set_xlabel("Time (minutes)")
    ax1.set_ylabel("CO2 Concentration (ppm)")
    ax1.set_title("CO2 Decay Curves")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)

    ax2.set_xlabel("Time (minutes)")
    ax2.set_ylabel("ln(Excess CO2) [ln(ppm)]")
    ax2.set_title("Linearised CO2 Decay (log scale)")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    filename = "co2_decay_results.png"
    plt.savefig(filename, dpi=150, bbox_inches="tight")
    print(f"\nPlot saved to: {filename}")
    plt.close()


def main():
    """Main entry point for the CO2 air exchange rate calculator."""
    print("=" * 60)
    print("  CO2 DECAY AIR EXCHANGE RATE CALCULATOR")
    print("=" * 60)
    print()
    print("This script guides you through measuring the air exchange")
    print("rate (ACH) of a room using CO2 decay after occupants leave.")
    print()
    print("Before starting, please have:")
    print("  - Your CO2 sensor ready (measuring in ppm)")
    print("  - A timer (phone or watch)")
    print("  - The room pre-occupied to raise CO2 above ~1000 ppm")
    print()
    print("For more details, see: co2_air_exchange_rate_manual.md")
    print()

    # Get outdoor CO2 level
    print("OUTDOOR CO2 LEVEL")
    print("-" * 40)
    print("Check a website for the current global CO2 concentration,")
    print("for example: https://www.co2.earth/daily-co2")
    print()
    c_outdoor = get_positive_float(
        "Enter the outdoor CO2 concentration (ppm): ",
        min_val=300,
        max_val=600,
    )
    print(f"  Outdoor CO2 level set to: {c_outdoor:.0f} ppm")
    print()

    # Get number of ventilation modes
    print("VENTILATION MODES")
    print("-" * 40)
    print("How many ventilation modes does your mechanical ventilation")
    print("system have? (e.g., 3 for low/medium/high)")
    print()
    num_modes = get_positive_int(
        "Enter the number of ventilation modes: ",
        min_val=1,
        max_val=10,
    )
    print()

    # Get names for each mode
    mode_names = []
    for i in range(num_modes):
        default_name = f"Mode {i + 1}"
        name = input(f"  Name for ventilation mode {i + 1} "
                     f"(press Enter for '{default_name}'): ").strip()
        if not name:
            name = default_name
        mode_names.append(name)

    print()
    print(f"You will measure {num_modes} ventilation mode(s): "
          f"{', '.join(mode_names)}")
    print()

    # Collect measurements and calculate ACH for each mode
    results = {}
    for i, mode_name in enumerate(mode_names):
        if i > 0:
            print(f"\n{'#'*60}")
            print(f"  NEXT MODE: {mode_name}")
            print(f"{'#'*60}")
            print()
            print("Before proceeding, you need to raise the CO2 level again.")
            print("Have people re-occupy the room with doors/windows closed")
            print(f"until CO2 is above {c_outdoor + 400:.0f} ppm.")
            print()
            input("Press Enter when the room CO2 is elevated and you are "
                  "ready to proceed...")

        times_minutes, co2_readings = collect_measurements(mode_name, c_outdoor)

        if len(times_minutes) < MIN_MEASUREMENTS:
            print(f"\nSkipping {mode_name}: insufficient measurements "
                  f"({len(times_minutes)} < {MIN_MEASUREMENTS}).")
            continue

        # Check that at least the first measurement is above the minimum excess
        if co2_readings[0] - c_outdoor < MIN_EXCESS_PPM:
            print(f"\nWarning: Initial CO2 excess for {mode_name} is only "
                  f"{co2_readings[0] - c_outdoor:.0f} ppm.")
            print(f"Results may be unreliable with such a small initial excess.")
            print()

        result = fit_decay_curve(times_minutes, co2_readings, c_outdoor)
        if result is not None:
            results[mode_name] = result

    # Print summary
    if not results:
        print("\nNo valid results were obtained. Please check your "
              "measurements and try again.")
        sys.exit(1)

    print()
    print("=" * 60)
    print("  RESULTS SUMMARY")
    print("=" * 60)
    print(f"\n  Outdoor CO2: {c_outdoor:.0f} ppm")
    print(f"  Sensor uncertainty: ±{SENSOR_UNCERTAINTY_PPM} ppm")

    for mode_name, result in results.items():
        print_result(mode_name, result)

    # Print comparison table
    print(f"\n  {'—'*50}")
    print(f"  {'Mode':<20} {'ACH':<15} {'Quality'}")
    print(f"  {'—'*50}")
    for mode_name, result in results.items():
        quality = classify_ventilation(result["ach"])
        ach_str = f"{result['ach']:.2f} ± {result['ach_uncertainty']:.2f}"
        print(f"  {mode_name:<20} {ach_str:<15} {quality}")
    print(f"  {'—'*50}")

    # Calculate room volume equivalent if the user is interested
    print()
    print("OPTIONAL: Estimate ventilation flow rate")
    print("-" * 40)
    print("If you know the room volume, the ventilation flow rate can be")
    print("estimated: Flow rate (m³/h) = ACH × Room volume (m³)")
    print()
    estimate = input("Would you like to estimate flow rates? (y/n): "
                     ).strip().lower()
    if estimate == "y":
        room_volume = get_positive_float(
            "Enter the room volume in m³ "
            "(length × width × height in metres): ",
            min_val=1,
            max_val=10000,
        )
        print()
        print(f"  {'Mode':<20} {'ACH':<12} {'Flow rate'}")
        print(f"  {'—'*45}")
        for mode_name, result in results.items():
            flow = result["ach"] * room_volume
            flow_unc = result["ach_uncertainty"] * room_volume
            print(f"  {mode_name:<20} {result['ach']:<12.2f} "
                  f"{flow:.1f} ± {flow_unc:.1f} m³/h")
        print(f"  {'—'*45}")

    # Generate plot
    print()
    print("Generating plot...")
    try:
        plot_results(results, c_outdoor)
    except Exception as e:
        print(f"Could not generate plot: {e}")
        print("Results have been printed above.")

    print()
    print("Measurement complete. Thank you!")
    print()


if __name__ == "__main__":
    main()
