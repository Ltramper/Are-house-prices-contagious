# CO₂ Decay-Based Air Exchange Rate Manual

## Overview

This manual guides you through measuring the **air exchange rate** (ACH — Air Changes per Hour) of a room using CO₂ concentration decay curves. The method exploits the fact that CO₂ produced by human breathing accumulates indoors; once everyone leaves, the ventilation system gradually replaces indoor air with outdoor air, causing the CO₂ level to decay exponentially toward the outdoor background concentration.

By recording this decay you can calculate how quickly the room's air is being replaced, and compare different ventilation modes side-by-side.

---

## Theory

### Exponential Decay Model

When a room with elevated CO₂ is vacated, the concentration follows:

```
C(t) = C_outdoor + (C₀ − C_outdoor) × e^(−n × t)
```

| Symbol       | Meaning                                            | Unit  |
| ------------ | -------------------------------------------------- | ----- |
| `C(t)`       | CO₂ concentration at time *t*                      | ppm   |
| `C_outdoor`  | Outdoor (background) CO₂ concentration             | ppm   |
| `C₀`         | CO₂ concentration at *t = 0* (room just vacated)   | ppm   |
| `n`          | Air exchange rate (**ACH**)                         | h⁻¹   |
| `t`          | Elapsed time since start of decay                  | h     |

By linearising (`ln(C − C_outdoor)` vs. time) and performing a least-squares fit, the script determines `n` — the air exchange rate.

### Interpreting ACH

| ACH (h⁻¹) | Meaning                                  |
| ---------- | ---------------------------------------- |
| 0.5        | Air fully replaced every 2 hours         |
| 1.0        | Air fully replaced every hour            |
| 3.0        | Air fully replaced every 20 minutes      |
| 5.0+       | Very high ventilation rate               |

If you also know the room volume (*V* in m³), the effective airflow rate is:

```
Q = n × V   [m³/h]
```

---

## What You Need

1. **A CO₂ sensor** that reads in **ppm** (parts per million).
   - Assumed sensor uncertainty: **±50 ppm**.
2. **A timer** (phone stopwatch or clock).
3. **A notepad** (or just run the script and enter readings interactively).
4. **The outdoor CO₂ concentration** — check one of these websites before you start:
   - [co2.earth](https://www.co2.earth/)
   - [NOAA GML](https://gml.noaa.gov/ccgg/trends/)
   - Typical global average: ~420 ppm (as of 2024). Use a local measurement if available.
5. (Optional) **Room dimensions** (length × width × height in metres) to compute airflow in m³/h.

---

## Step-by-Step Measurement Guide

### Phase 0 — Preparation

1. **Identify ventilation modes.** Check your mechanical ventilation system for its available modes (e.g., *Low*, *Medium*, *High*, or numbered settings such as *1*, *2*, *3*).
2. **Note the outdoor CO₂ level** from one of the websites above.
3. **Place the CO₂ sensor** in the centre of the room at roughly breathing height (1.0 – 1.5 m), away from windows, doors, and air vents, so it measures a representative room average.
4. **Decide how many readings you will take.** A minimum of **5–8 readings** spread over 1–2 hours gives good results. More is better.

### Phase 1 — Elevate CO₂

1. **Set the ventilation to the mode you want to test first** (e.g., *Low*).
2. **Occupy the room normally.** One or two people breathing in a closed room for 30–60 minutes typically raises CO₂ to 800–1500 ppm.
3. **Target:** CO₂ should be at least **300 ppm above** the outdoor level before you begin measurements.

### Phase 2 — Measure the Decay

> **Important — minimise your influence on the measurement!**
>
> Every time you enter the room to read the sensor, you exhale CO₂. To keep this influence negligible:
>
> - **Enter, read the sensor, and leave within 30 seconds.**
> - **Hold your breath** while near the sensor if possible.
> - Do **not** stay in the room between readings — wait outside.

1. **t = 0 min** — Everyone leaves the room and closes the door. Immediately take the first reading (this is `C₀`). Record the value and the time.
2. **t = 10 min** — Enter briefly, read the sensor, leave.
3. **t = 20 min** — Enter briefly, read the sensor, leave.
4. **t = 30 min** — Enter briefly, read the sensor, leave.
5. **t = 45 min** — Enter briefly, read the sensor, leave.
6. **t = 60 min** — Enter briefly, read the sensor, leave.
7. **t = 90 min** — Enter briefly, read the sensor, leave.
8. **t = 120 min** — Enter briefly, read the sensor, leave.

The schedule above is a suggestion. You may adapt it:

| Situation | Adjustment |
| --------- | ---------- |
| CO₂ drops very fast (high ventilation) | Use shorter intervals (every 5 min for the first 30 min) |
| CO₂ drops slowly (low ventilation) | Extend to 3–4 hours with longer intervals |
| CO₂ is already near outdoor level | Stop — further readings add no information |

**Stop measuring** when the CO₂ reading is within ~100 ppm of the outdoor level or when it stops decreasing between readings.

### Phase 3 — Repeat for Other Ventilation Modes

For each additional ventilation mode:

1. **Switch** the ventilation to the next mode.
2. **Re-elevate CO₂** by occupying the room again (Phase 1).
3. **Repeat Phase 2** with fresh measurements.

### Phase 4 — Run the Script

```bash
python co2_air_exchange_rate.py
```

The script will prompt you for:

1. The outdoor CO₂ concentration.
2. (Optional) Room volume in m³.
3. Number of ventilation modes.
4. Names for each mode.
5. CO₂ readings and their elapsed times for each mode.

It then calculates and displays:

- **ACH** (air changes per hour) for each mode with uncertainty range.
- **R²** (goodness-of-fit) — values above 0.95 indicate an excellent fit.
- **Airflow rate** in m³/h and L/s (if room volume was provided).
- A **comparison table** across all modes.

---

## Understanding the Results

### Air Exchange Rate (ACH)

The ACH tells you how many times per hour the room's air volume is replaced. Higher ACH means faster ventilation.

### Uncertainty Range

Because the sensor has an uncertainty of ±50 ppm, the true ACH lies somewhere within the reported range. The script computes worst-case bounds by shifting all readings by the sensor uncertainty.

### R² (Coefficient of Determination)

| R² value  | Interpretation                     |
| --------- | ---------------------------------- |
| > 0.98    | Excellent — very clean decay curve |
| 0.95–0.98 | Good — reliable result             |
| 0.90–0.95 | Fair — usable but check for issues |
| < 0.90    | Poor — results may be unreliable   |

A low R² may indicate:
- External disturbances (door opened, someone entered).
- CO₂ was already too close to outdoor level.
- Sensor malfunction or drift.
- Non-uniform air mixing in the room.

---

## Practical Tips

- **Temperature and wind** affect natural ventilation. Try to measure under consistent conditions (close windows, keep doors shut).
- **Sensor warm-up**: Some CO₂ sensors need 5–10 minutes after power-on to stabilise. Turn it on early.
- **Sensor placement**: Avoid placing the sensor directly in front of a vent or near the floor; this biases the reading.
- **Repeatability**: If results seem off, repeat the measurement for the same mode. Consistent results across runs increase confidence.
- **Time of day**: Outdoor CO₂ can vary by ±20 ppm between morning and evening. Try to complete all modes within the same day.

---

## Example Session

```
============================================================
  CO2 Decay-Based Air Exchange Rate Calculator
============================================================

Enter the outdoor CO2 concentration (ppm): 422
Room volume in m³ (or press Enter to skip): 36

How many ventilation modes does your mechanical ventilation have?
(e.g. 3 for low/medium/high): 3
  Name for mode 1: Low
  Name for mode 2: Medium
  Name for mode 3: High

--- Collecting measurements for: Low ---
How many readings will you take for 'Low'? (recommended: 8 or more): 6
  Reading 1 of 6
  Enter CO2 reading (ppm): 980
  Reading 2 of 6
  Enter elapsed time since start in minutes: 15
  Enter CO2 reading (ppm): 870
  ...

RESULTS SUMMARY
============================================================
  Outdoor CO2: 422 ppm
  Sensor uncertainty: ±50 ppm
  Room volume: 36.0 m³

  Mode: Low
  Air Exchange Rate (ACH): 0.65 h⁻¹
  Uncertainty range:       0.52 – 0.78 h⁻¹
  R² (goodness of fit):    0.9873
  Effective airflow:       23.4 m³/h
                           6.5 L/s
```

---

## Troubleshooting

| Problem | Solution |
| ------- | -------- |
| All readings are nearly the same | CO₂ was not elevated enough. Occupy the room longer before measuring. |
| R² is very low | Check for disturbances. Ensure no one entered the room. |
| ACH is negative | Data may be out of order or CO₂ was rising (someone was in the room). |
| Readings fluctuate wildly | The sensor may need calibration or is affected by drafts. |

---

## References

- ASHRAE Standard 62.1 — Ventilation for Acceptable Indoor Air Quality
- EN 16798-1:2019 — Energy performance of buildings (ventilation)
- Sherman, M.H. (1990). *Tracer-gas techniques for measuring ventilation in a single zone*. Building and Environment, 25(4), 365–374.
