#!/usr/bin/env python3
"""
CO2 Decay-Based Air Exchange Rate Calculator

Calculates the air exchange rate (ACH - Air Changes per Hour) of a room
by analysing the decay of CO2 concentration after occupants have left.

The underlying model assumes first-order exponential decay:

    C(t) = C_outdoor + (C_initial - C_outdoor) * exp(-n * t)

where
    C(t)      = CO2 concentration at time t  [ppm]
    C_outdoor = outdoor (background) CO2 concentration  [ppm]
    C_initial = CO2 concentration at t = 0 (just after people left)  [ppm]
    n         = air exchange rate  [1/h]  (ACH)
    t         = elapsed time since start of decay  [h]

Usage:
    python co2_air_exchange_rate.py

The script interactively guides the user through the measurement process.
See co2_air_exchange_rate_manual.md for detailed instructions.
"""

import math
import sys
import datetime

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SENSOR_UNCERTAINTY_PPM = 50  # ±50 ppm sensor uncertainty

# Recommended measurement schedule (minutes after start)
# The first reading (t = 0) is taken when everyone has left the room.
# Subsequent readings are spaced to capture the exponential decay while
# keeping the time the user spends inside the room as short as possible.
SUGGESTED_MEASUREMENT_TIMES_MIN = [0, 10, 20, 30, 45, 60, 90, 120]

# Maximum seconds the user should stay inside the room per reading to
# avoid influencing the CO2 level significantly.
MAX_SECONDS_IN_ROOM = 30


def get_positive_int(prompt: str) -> int:
    """Prompt until a valid positive integer is entered."""
    while True:
        try:
            value = int(input(prompt))
            if value <= 0:
                print("Please enter a positive integer.")
                continue
            return value
        except ValueError:
            print("Invalid input. Please enter a positive integer.")


def get_positive_float(prompt: str) -> float:
    """Prompt until a valid positive float is entered."""
    while True:
        try:
            value = float(input(prompt))
            if value <= 0:
                print("Please enter a positive number.")
                continue
            return value
        except ValueError:
            print("Invalid input. Please enter a number.")


def get_non_negative_float(prompt: str) -> float:
    """Prompt until a valid non-negative float is entered."""
    while True:
        try:
            value = float(input(prompt))
            if value < 0:
                print("Please enter a non-negative number.")
                continue
            return value
        except ValueError:
            print("Invalid input. Please enter a number.")


def print_separator() -> None:
    print("\n" + "=" * 60 + "\n")


def print_measurement_tips() -> None:
    """Print tips for taking a measurement quickly."""
    print(
        f"  TIP: Enter the room, read the sensor, and leave within "
        f"{MAX_SECONDS_IN_ROOM} seconds\n"
        f"       to minimise the influence of your own breathing on the CO2 level."
    )


def suggest_schedule(measurement_times: list[int]) -> None:
    """Print the suggested measurement schedule.

    Parameters
    ----------
    measurement_times : list[int]
        List of measurement times in minutes from the start of the decay.
    """
    now = datetime.datetime.now()
    print("  Suggested measurement schedule:")
    for i, t in enumerate(measurement_times):
        target_time = now + datetime.timedelta(minutes=t)
        print(f"    Reading {i + 1}: t = {t:>4} min  (approx. {target_time.strftime('%H:%M')})")
    print()


def collect_measurements(mode_name: str) -> tuple[list[float], list[float]]:
    """
    Interactively collect CO2 measurements for one ventilation mode.

    Returns
    -------
    times_h : list[float]
        Elapsed time of each measurement in hours.
    concentrations : list[float]
        CO2 concentration at each measurement in ppm.
    """
    print(f"--- Collecting measurements for: {mode_name} ---\n")
    print(
        "You will now take a series of CO2 readings.\n"
        "The first reading (t = 0) should be taken immediately after\n"
        "everyone has left the room and the door is closed.\n"
    )
    print_measurement_tips()
    print()

    num_readings = get_positive_int(
        f"How many readings will you take for '{mode_name}'? "
        f"(recommended: {len(SUGGESTED_MEASUREMENT_TIMES_MIN)} or more): "
    )

    if num_readings < 3:
        print(
            "WARNING: At least 3 readings are recommended for a reliable fit.\n"
            "         Results may be unreliable with fewer readings."
        )

    print("\nWould you like to see a suggested measurement schedule? (y/n): ", end="")
    if input().strip().lower() in ("y", "yes"):
        # Scale suggested times to requested number of readings
        if num_readings <= len(SUGGESTED_MEASUREMENT_TIMES_MIN):
            schedule = SUGGESTED_MEASUREMENT_TIMES_MIN[:num_readings]
        else:
            max_time = SUGGESTED_MEASUREMENT_TIMES_MIN[-1]
            step = max_time / (num_readings - 1)
            schedule = [round(i * step) for i in range(num_readings)]
        suggest_schedule(schedule)

    times_min: list[float] = []
    concentrations: list[float] = []

    for i in range(num_readings):
        print(f"\n  --- Reading {i + 1} of {num_readings} ---")
        if i == 0:
            print("  (This is the initial reading at t = 0, right after the room is vacated.)")
            t = 0.0
        else:
            t = get_non_negative_float(
                f"  Enter elapsed time since start in minutes: "
            )
            if t <= times_min[-1]:
                print(
                    f"  WARNING: This time ({t} min) is not after the previous reading "
                    f"({times_min[-1]} min). Readings should be in chronological order."
                )

        co2 = get_positive_float("  Enter CO2 reading (ppm): ")
        times_min.append(t)
        concentrations.append(co2)

        if i < num_readings - 1:
            print_measurement_tips()

    times_h = [t / 60.0 for t in times_min]
    return times_h, concentrations


def calculate_ach_least_squares(
    times_h: list[float],
    concentrations: list[float],
    c_outdoor: float,
) -> tuple[float, float, float]:
    """
    Calculate the air exchange rate (ACH) using a least-squares fit of the
    linearised decay model.

    The model  C(t) = C_out + (C0 - C_out) * exp(-n * t)
    is linearised as:
        ln(C(t) - C_out) = ln(C0 - C_out) - n * t

    A simple linear regression on  y = ln(C - C_out)  vs.  x = t  gives
    the slope  -n  and intercept  ln(C0 - C_out).

    Parameters
    ----------
    times_h : list[float]
        Measurement times in hours.
    concentrations : list[float]
        CO2 concentrations in ppm.
    c_outdoor : float
        Outdoor / background CO2 concentration in ppm.

    Returns
    -------
    ach : float
        Air exchange rate in air changes per hour (1/h).
    ach_low : float
        Lower bound estimate considering sensor uncertainty.
    ach_high : float
        Upper bound estimate considering sensor uncertainty.
    """

    def _fit(concs: list[float]) -> float:
        """Return ACH from linear regression on log-transformed data."""
        xs: list[float] = []
        ys: list[float] = []
        for t, c in zip(times_h, concs):
            delta = c - c_outdoor
            if delta <= 0:
                # Cannot take log of non-positive value; skip this point.
                continue
            xs.append(t)
            ys.append(math.log(delta))

        n = len(xs)
        if n < 2:
            return float("nan")

        sum_x = sum(xs)
        sum_y = sum(ys)
        sum_xy = sum(x * y for x, y in zip(xs, ys))
        sum_x2 = sum(x * x for x in xs)

        denom = n * sum_x2 - sum_x * sum_x
        if abs(denom) < 1e-12:
            return float("nan")

        slope = (n * sum_xy - sum_x * sum_y) / denom
        return -slope  # ACH = -slope

    # Best estimate with raw readings
    ach = _fit(concentrations)

    # Uncertainty bounds: shift all readings by ±sensor uncertainty
    # Worst-case high ACH: initial reading high, later readings low
    # Worst-case low ACH:  initial reading low, later readings high
    concs_high_ach = []
    concs_low_ach = []
    for i, c in enumerate(concentrations):
        if i == 0:
            concs_high_ach.append(c + SENSOR_UNCERTAINTY_PPM)
            concs_low_ach.append(c - SENSOR_UNCERTAINTY_PPM)
        else:
            concs_high_ach.append(c - SENSOR_UNCERTAINTY_PPM)
            concs_low_ach.append(c + SENSOR_UNCERTAINTY_PPM)

    ach_high = _fit(concs_high_ach)
    ach_low = _fit(concs_low_ach)

    # Ensure low <= best <= high
    if not math.isnan(ach_low) and not math.isnan(ach_high):
        ach_low, ach_high = min(ach_low, ach_high), max(ach_low, ach_high)

    return ach, ach_low, ach_high


def compute_r_squared(
    times_h: list[float],
    concentrations: list[float],
    c_outdoor: float,
    ach: float,
) -> float:
    """
    Compute the coefficient of determination (R²) for the fitted model.

    Parameters
    ----------
    times_h : list[float]
        Measurement times in hours.
    concentrations : list[float]
        Measured CO2 concentrations in ppm.
    c_outdoor : float
        Outdoor / background CO2 concentration in ppm.
    ach : float
        Fitted air exchange rate in h⁻¹.

    Returns
    -------
    float
        R² value between 0 and 1, where 1 indicates a perfect fit.
    """
    c0 = concentrations[0]
    predicted = [
        c_outdoor + (c0 - c_outdoor) * math.exp(-ach * t) for t in times_h
    ]
    mean_c = sum(concentrations) / len(concentrations)
    ss_res = sum((o - p) ** 2 for o, p in zip(concentrations, predicted))
    ss_tot = sum((o - mean_c) ** 2 for o in concentrations)

    if ss_tot < 1e-12:
        return float("nan")
    return 1.0 - ss_res / ss_tot


def print_results(
    mode_name: str,
    ach: float,
    ach_low: float,
    ach_high: float,
    r_squared: float,
    room_volume: float | None,
) -> None:
    """Print the results for a single ventilation mode.

    Parameters
    ----------
    mode_name : str
        Name of the ventilation mode.
    ach : float
        Best-estimate air exchange rate in h⁻¹.
    ach_low : float
        Lower bound of ACH considering sensor uncertainty.
    ach_high : float
        Upper bound of ACH considering sensor uncertainty.
    r_squared : float
        Coefficient of determination for the fit.
    room_volume : float or None
        Room volume in m³, used to compute airflow rate. None to skip.
    """
    print(f"  Mode: {mode_name}")
    print(f"  Air Exchange Rate (ACH): {ach:.2f} h⁻¹")
    print(f"  Uncertainty range:       {ach_low:.2f} – {ach_high:.2f} h⁻¹")
    print(f"  R² (goodness of fit):    {r_squared:.4f}")

    if room_volume is not None and room_volume > 0 and not math.isnan(ach):
        flow_rate = ach * room_volume  # m³/h
        print(f"  Effective airflow:       {flow_rate:.1f} m³/h")
        print(f"                           {flow_rate / 3.6:.1f} L/s")

    if r_squared < 0.90 and not math.isnan(r_squared):
        print(
            "\n  ⚠ WARNING: R² is below 0.90 – the fit quality is poor.\n"
            "    Possible causes:\n"
            "    - Too few measurements\n"
            "    - CO2 had already dropped close to outdoor levels\n"
            "    - External disturbances (door opened, people entered)\n"
            "    - Sensor drift or malfunction"
        )
    print()


def main() -> None:
    print("=" * 60)
    print("  CO2 Decay-Based Air Exchange Rate Calculator")
    print("=" * 60)
    print()
    print(
        "This tool calculates the air exchange rate (ACH) of a room\n"
        "based on the decay of CO2 concentration after all occupants\n"
        "have left. You will be guided through the measurement process.\n"
    )
    print(
        "Before you begin, ensure the room has been occupied long enough\n"
        "for CO2 to rise well above outdoor levels (at least 200–300 ppm\n"
        "above outdoor concentration).\n"
    )

    # --- Outdoor CO2 ---
    print(
        "You can find the current global average CO2 concentration at:\n"
        "  https://www.co2.earth/  or  https://gml.noaa.gov/ccgg/trends/\n"
    )
    c_outdoor = get_positive_float(
        "Enter the outdoor CO2 concentration (ppm): "
    )

    # --- Room volume (optional, for airflow calculation) ---
    print(
        "\nOptionally, enter the room dimensions to calculate the\n"
        "effective airflow rate in m³/h. Press Enter to skip."
    )
    room_volume: float | None = None
    vol_input = input("Room volume in m³ (or press Enter to skip): ").strip()
    if vol_input:
        try:
            room_volume = float(vol_input)
            if room_volume <= 0:
                print("Invalid volume. Skipping airflow calculation.")
                room_volume = None
        except ValueError:
            print("Invalid input. Skipping airflow calculation.")

    print_separator()

    # --- Ventilation modes ---
    num_modes = get_positive_int(
        "How many ventilation modes does your mechanical ventilation have?\n"
        "(e.g. 3 for low/medium/high): "
    )

    mode_names: list[str] = []
    for i in range(num_modes):
        name = input(f"  Name for mode {i + 1} (e.g. 'Low', 'Medium', 'High'): ").strip()
        if not name:
            name = f"Mode {i + 1}"
        mode_names.append(name)

    print_separator()
    print("MEASUREMENT PROCEDURE OVERVIEW")
    print("-" * 40)
    print(
        f"For each of the {num_modes} ventilation mode(s) you will:\n"
        "  1. Set the ventilation to the desired mode.\n"
        "  2. Occupy the room until CO2 is elevated (≥ outdoor + 300 ppm).\n"
        "  3. Leave the room and close the door.\n"
        "  4. Take periodic CO2 readings by briefly entering the room.\n"
        f"     (Stay inside < {MAX_SECONDS_IN_ROOM} s per reading!)\n"
        "  5. Continue until CO2 is close to outdoor level or stops dropping.\n"
    )
    print(
        "Between ventilation modes, re-elevate the CO2 by occupying the\n"
        "room again before starting the next set of readings.\n"
    )

    input("Press Enter when you are ready to start measurements...")

    # --- Collect data for each mode ---
    results: list[dict] = []

    for i, mode_name in enumerate(mode_names):
        print_separator()
        print(f"VENTILATION MODE {i + 1} of {num_modes}: '{mode_name}'")
        print("-" * 40)
        print(
            f"\n  1. Set your ventilation system to '{mode_name}'.\n"
            f"  2. Make sure the room CO2 is elevated (well above {c_outdoor:.0f} ppm).\n"
            "  3. Have everyone leave the room and close the door.\n"
            "  4. Start taking readings as instructed below.\n"
        )
        input(f"Press Enter when the room is vacated and you are ready to measure '{mode_name}'...")
        print()

        times_h, concentrations = collect_measurements(mode_name)

        if concentrations[0] - c_outdoor < 100:
            print(
                f"\n  ⚠ WARNING: Initial CO2 ({concentrations[0]:.0f} ppm) is only "
                f"{concentrations[0] - c_outdoor:.0f} ppm above outdoor level.\n"
                "    Results will be less reliable. A difference of ≥ 300 ppm is recommended."
            )

        ach, ach_low, ach_high = calculate_ach_least_squares(
            times_h, concentrations, c_outdoor
        )
        r_squared = compute_r_squared(times_h, concentrations, c_outdoor, ach)

        results.append(
            {
                "mode": mode_name,
                "ach": ach,
                "ach_low": ach_low,
                "ach_high": ach_high,
                "r_squared": r_squared,
                "times_h": times_h,
                "concentrations": concentrations,
            }
        )

        if i < num_modes - 1:
            print(
                f"\n  Measurements for '{mode_name}' complete.\n"
                f"  Next mode: '{mode_names[i + 1]}'.\n"
                "  Please re-elevate the CO2 in the room before proceeding.\n"
                "  (Occupy the room for a while with the next ventilation mode active.)\n"
            )
            input("Press Enter when ready for the next mode...")

    # --- Summary ---
    print_separator()
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"  Outdoor CO2: {c_outdoor:.0f} ppm")
    print(f"  Sensor uncertainty: ±{SENSOR_UNCERTAINTY_PPM} ppm")
    if room_volume is not None:
        print(f"  Room volume: {room_volume:.1f} m³")
    print()

    for result in results:
        print_results(
            result["mode"],
            result["ach"],
            result["ach_low"],
            result["ach_high"],
            result["r_squared"],
            room_volume,
        )

    # --- Comparison table ---
    if num_modes > 1:
        print("-" * 60)
        print("  COMPARISON TABLE")
        print("-" * 60)
        header = f"  {'Mode':<20} {'ACH (h⁻¹)':>12} {'Range':>20} {'R²':>8}"
        print(header)
        print("  " + "-" * (len(header) - 2))
        for r in results:
            range_str = f"{r['ach_low']:.2f} – {r['ach_high']:.2f}"
            print(
                f"  {r['mode']:<20} {r['ach']:>12.2f} {range_str:>20} "
                f"{r['r_squared']:>8.4f}"
            )
        print()

        # Relative comparison
        baseline = results[0]
        if not math.isnan(baseline["ach"]) and baseline["ach"] > 0:
            print(f"  Relative to '{baseline['mode']}':")
            for r in results[1:]:
                if not math.isnan(r["ach"]) and baseline["ach"] > 0:
                    ratio = r["ach"] / baseline["ach"]
                    print(
                        f"    '{r['mode']}' provides {ratio:.1f}x the air exchange "
                        f"rate of '{baseline['mode']}'"
                    )
            print()

    # --- Raw data dump ---
    print("-" * 60)
    print("  RAW MEASUREMENT DATA")
    print("-" * 60)
    for result in results:
        print(f"\n  Mode: {result['mode']}")
        print(f"  {'Time (min)':>12}  {'CO2 (ppm)':>12}")
        for t, c in zip(result["times_h"], result["concentrations"]):
            print(f"  {t * 60:>12.1f}  {c:>12.1f}")
    print()

    print("=" * 60)
    print("  Analysis complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
