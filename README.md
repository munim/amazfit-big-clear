# Big Clear: Amazfit watch face

Zepp OS 3.0+ round face for 466×466 (GTR 4, Active 2 Round, Cheetah 2 Pro, T-Rex 3 Pro 44) and 480×480 (Balance family, Cheetah Pro). Layout comes from `amazfit-face-round-v2.html`.

## Low-power design

- Declarative widgets only (`IMG_TIME`, `IMG_DATE`, `IMG_WEEK`, `TEXT_IMG`, `IMG_LEVEL`, `IMG_STATUS`). The OS redraws them. The face has no `setInterval`, `setTimeout` or sensor subscription, so no JS runs after `build()`.
- Heart rate, steps, calories, battery and weather use `data_type` bindings. The face never starts its own sampling.
- Pure black ground. Oxanium glyphs are pre-rendered to PNG sprites, so there is no font engine at runtime.
- **Always-on display:** dim outline time, date and battery only. No weather, calorie, heart rate or steps. No burn-in shift, because that would need a JS wake-up each minute.
- **Sleep:** Zepp enables Do Not Disturb in sleep mode. Black `IMG_STATUS` (DISTURB) overlays hide every data slot and dim the time to about 70%.

## Features kept

Stacked hour/minute time, AM/PM tag, weather icon + temperature + high/low, date, calorie, battery (icon turns amber below 20%), heart rate, steps with a goal bar.

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
- The battery amber icon assumes level 0 covers the lowest bucket (5 levels, 0-20%).
- The Do Not Disturb overlay depends on the watch enabling DND during sleep mode.
- The step goal bar assumes `IMG_LEVEL` with `type: STEP` scales to the step goal.
- Edit-mode titles for the custom options are English, Simplified and Traditional Chinese only.
