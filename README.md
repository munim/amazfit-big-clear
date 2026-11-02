# Big & Clear: Amazfit watch face

<p align="center">
  <img src="docs/marketing-features-350.gif" alt="Big & Clear watch face features: active, outline, 10K steps, sleep and always-on display" width="350">
</p>

Zepp OS 3.0+ round face for 466×466 (GTR 4, Active 2 Round, Cheetah 2 Pro, T-Rex 3 Pro 44) and 480×480 (Balance family, Cheetah Pro). Layout comes from `amazfit-face-round-v2.html`.

## Low-power design

- Declarative widgets only (`IMG_TIME`, `IMG_DATE`, `IMG_WEEK`, `TEXT_IMG`, `IMG_LEVEL`, `IMG_STATUS`). The OS redraws them. The face has no `setInterval` or `setTimeout`. The only JS after `build()` is a step-change callback that swaps the step text to `10.4K` style at 10,000 steps and above (floored, so it never reads high).
- Heart rate, steps, calories, battery and weather use `data_type` bindings. The face never starts its own sampling.
- Pure black ground. Oxanium glyphs are pre-rendered to PNG sprites, so there is no font engine at runtime.
- **Always-on display:** dim outline time, date and battery only. No weather, calorie, heart rate or steps. No burn-in shift, because that would need a JS wake-up each minute.
- **Sleep:** Zepp enables Do Not Disturb in sleep mode. Black `IMG_STATUS` (DISTURB) overlays hide every data slot and dim the time to about 70%.

## Features kept

Stacked hour/minute time, AM/PM tag, weather icon + temperature + high/low, date, calorie, battery (icon fills to the nearest quarter: 100/75/50/25/0%, amber below 20%; the number stays exact), heart rate, steps with a goal bar.

## On-watch options (long-press → Edit)

Time style (solid/outline), weather (with high/low, temperature only, off), date, calorie, battery, heart rate and steps (each on/off). 12/24-hour follows the system setting.

## Build

```
python3 tools/gen_assets.py   # regenerate sprites + layouts (needs fonttools, Pillow, numpy, librsvg)
zeus build                    # writes dist/*.zab
zeus preview                  # or install through the Zepp app in developer mode
```

Previews rendered by the generator are in `docs/`. Oxanium is under the SIL OFL (`tools/fonts/OFL-Oxanium.txt`).

## Not verified

No simulator or watch was available. Only `zeus build` and the generator's own preview renders were checked. Test on a device before trusting these:

- Weather icon mapping uses the Zepp condition ids 0-28 (`WEATHER_MAP` in the generator).
- The battery icon assumes `IMG_LEVEL` picks image `floor(percent × 40 / 100)` (40 buckets of 2.5%). If the OS rounds differently, the fill can be one quarter off near the thresholds.
- The 10K+ step text assumes `IMG` widgets accept `setProperty(prop.MORE, { src, x, w, h })` and that the `Step` sensor needs the `data:user.hd.step` permission (added to `app.json`).
- The Do Not Disturb overlay depends on the watch enabling DND during sleep mode.
- The step goal bar assumes `IMG_LEVEL` with `type: STEP` scales to the step goal.
- Edit-mode titles for the custom options are English, Simplified and Traditional Chinese only.
