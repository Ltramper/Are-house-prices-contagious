# CO2 Decay Air Exchange Rate Measurement Manual

## Introduction

This manual guides you through measuring the **air exchange rate** (also called Air Changes per Hour, or ACH) of a room using CO2 decay curves. The air exchange rate tells you how many times per hour the air in a room is replaced with fresh outdoor air. A higher ACH means better ventilation.

### How It Works

When people occupy a room, they exhale CO2 and raise its concentration above outdoor levels. After everyone leaves, the CO2 concentration decays back toward the outdoor level. The rate of this decay is directly related to the ventilation rate. By measuring how quickly CO2 drops, we can calculate the air exchange rate.

The CO2 concentration follows an exponential decay:

```
C(t) = C_outdoor + (C_initial - C_outdoor) × e^(−n × t)
```

Where:
- **C(t)** — CO2 concentration (ppm) at time *t*
- **C_outdoor** — outdoor CO2 concentration (ppm)
- **C_initial** — CO2 concentration at the start of the measurement (ppm)
- **n** — air exchange rate (air changes per hour, ACH)
- **t** — time in hours since the start of the measurement

By taking multiple CO2 readings over time and fitting this exponential decay model, we solve for **n**, which is the air exchange rate.

---

## Equipment Needed

- **1 CO2 sensor** (measuring in ppm, with approximately ±50 ppm uncertainty)
- **A timer** (phone, watch, or any timekeeper)
- **A notepad** or the Python script to record measurements
- **Access to outdoor CO2 data** (e.g., from [CO2.Earth](https://www.co2.earth/) or a local monitoring station)

---

## Preparation

### 1. Determine the Outdoor CO2 Level

Before starting, look up the current approximate outdoor CO2 concentration. You can find this on websites such as:

- [CO2.Earth — Daily CO2](https://www.co2.earth/daily-co2)
- [NOAA Global Monitoring Laboratory](https://gml.noaa.gov/ccgg/trends/)

Typical outdoor CO2 concentrations are approximately **415–425 ppm** (as of 2024–2026), but can vary by location.

### 2. Identify Your Ventilation Modes

Determine how many ventilation modes your mechanical ventilation system supports. For example, many systems have 3 modes:
- **Mode 1** — Low (minimum ventilation)
- **Mode 2** — Medium (normal ventilation)
- **Mode 3** — High (maximum ventilation)

You will repeat the measurement process for each mode.

### 3. Raise the CO2 Level in the Room

Before each measurement session, the room needs an elevated CO2 level above the outdoor baseline. The easiest way is to have one or more people occupy the room with doors and windows closed for **30–60 minutes**. The more people and the smaller the room, the faster CO2 rises.

A good starting concentration for the decay measurement is at least **800–1000 ppm** (ideally above **1000 ppm**). Higher initial concentrations give more data points above the sensor noise floor.

---

## Measurement Procedure

### Important: Minimise Your CO2 Influence

**You breathe out CO2.** Each time you enter the room to take a reading, you add CO2 to the air. To minimise this effect:

- **Enter the room, read the sensor, and leave immediately.** Aim for **less than 30 seconds** per reading.
- **Do not stay in the room between readings.** Wait outside.
- **Do not breathe more than necessary** while in the room (breathe normally, but be swift).

### Step-by-Step for Each Ventilation Mode

Repeat the following for **each ventilation mode** you want to test:

#### Step 1 — Prepare the Room
1. Close all doors and windows.
2. Have people occupy the room until the CO2 concentration is above **1000 ppm** (at least 200 ppm above the first measurement you plan to record, to account for any initial delay).
3. Set the mechanical ventilation to the desired mode.

#### Step 2 — Everyone Leaves
1. **All people leave the room.** Close the door behind you.
2. Start your timer.

#### Step 3 — Take Measurements

Take CO2 readings at the following approximate intervals. Enter the room briefly (< 30 seconds), note the sensor reading and the exact time, then leave immediately.

| Measurement | Time After Leaving | Purpose |
|---|---|---|
| 1 | **2 minutes** | First baseline reading (let the room settle after the door was opened/closed) |
| 2 | **7 minutes** | Early decay |
| 3 | **15 minutes** | Early-to-mid decay |
| 4 | **30 minutes** | Mid decay |
| 5 | **50 minutes** | Mid-to-late decay |
| 6 | **75 minutes** | Late decay |
| 7 | **105 minutes** | Very late decay (if CO2 is still above outdoor + 100 ppm) |

> **When to stop:** You can stop measuring once the CO2 reading is within **100 ppm of the outdoor level**, or after about **2 hours**, whichever comes first. At that point, the remaining signal is within the noise of the sensor.

> **Timing guidance:** These intervals are suggestions. The key is to have **at least 5 readings** spread over the decay period, with more readings early on (when decay is fastest). If ventilation is very strong (high mode), the decay may be complete within 30–45 minutes. If ventilation is very weak (low mode), you may need to wait 2+ hours.

#### Step 4 — Record Results

For each reading, record:
- **Time** (minutes since all people left)
- **CO2 reading** (ppm)

#### Step 5 — Change Mode and Repeat

After completing measurements for one ventilation mode:
1. Re-occupy the room to raise CO2 above **1000 ppm** again.
2. Switch the ventilation system to the next mode.
3. Repeat Steps 2–4.

---

## Using the Python Script

The included Python script `co2_air_exchange_rate.py` automates the calculation and guides you through the process interactively.

### Prerequisites

- Python 3.7 or later
- Required packages: `numpy`, `scipy`, `matplotlib` (install via `pip install numpy scipy matplotlib`)

### Running the Script

```bash
python co2_air_exchange_rate.py
```

### What the Script Does

1. **Asks for the outdoor CO2 level** — Enter the value you looked up.
2. **Asks how many ventilation modes** your system has.
3. **For each ventilation mode:**
   - Guides you through the measurement process.
   - Suggests when to take the next measurement.
   - Asks you to enter each CO2 reading with its timestamp.
   - Fits an exponential decay curve to your data.
   - Calculates the air exchange rate (ACH) with an uncertainty estimate.
4. **Displays a summary** comparing all ventilation modes.
5. **Generates a plot** of the CO2 decay curves for each mode.

### Interpreting the Results

| ACH (air changes/hour) | Ventilation Quality |
|---|---|
| < 0.5 | Poor — inadequate ventilation |
| 0.5 – 1.0 | Minimal — may be acceptable for low occupancy |
| 1.0 – 3.0 | Moderate — typical for residential mechanical ventilation |
| 3.0 – 6.0 | Good — typical for well-ventilated spaces |
| > 6.0 | Excellent — high ventilation rate |

### Uncertainty

The script accounts for sensor uncertainty (±50 ppm) by propagating this through the curve fit. The reported uncertainty gives you a confidence range for the calculated ACH value.

---

## Tips for Accurate Measurements

1. **Keep doors and windows closed** throughout the measurement. Any opening will affect the result.
2. **Don't cook, burn candles, or run other CO2 sources** during the measurement.
3. **Place the sensor at breathing height** (~1.0–1.5 m) and away from walls and ventilation outlets (at least 1 m distance). This gives a more representative room average.
4. **Be quick** when entering to take readings — your breath adds approximately 40,000 ppm CO2 exhaled air, which mixes into the room.
5. **Start with the lowest ventilation mode** — this takes the longest, and you can do the faster modes afterwards in the same day.
6. **Ensure the room temperature is stable** — large temperature changes can affect air density and mixing patterns.
7. **Repeat the experiment** if you get unexpected results (e.g., very low R² fit quality reported by the script).

---

## Troubleshooting

| Problem | Possible Cause | Solution |
|---|---|---|
| CO2 doesn't rise above 800 ppm | Room is too large or too leaky | Add more people, occupy longer, or seal gaps |
| ACH is unexpectedly high | Air leaks, open window, or sensor near vent | Check seals, sensor placement |
| ACH is near zero | Ventilation system may be off or blocked | Verify system is running |
| Poor curve fit (low R²) | Too few data points or too much noise | Take more readings, start at higher CO2 |
| Negative ACH reported | Measurement error or CO2 source in room | Check for hidden CO2 sources, retake measurements |

---

## References

- ASTM E741 — Standard Test Method for Determining Air Change in a Single Zone by Means of a Tracer Gas Dilution
- Persily, A. K. (1997). *Evaluating building IAQ and ventilation with indoor carbon dioxide.* ASHRAE Transactions, 103(2).
- [CO2.Earth](https://www.co2.earth/) — Global CO2 monitoring data
