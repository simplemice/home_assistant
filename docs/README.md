# 🏠 Casa De Ratton — Fully Automated Smart Home

---

## What This Is

Casa De Ratton is a fully autonomous smart home running on Home Assistant. It manages presence, climate, security, energy, media, and social automation without manual input. An AI persona named **JARVIS** handles all voice announcements and notifications, routing them to the right output — speaker, phone, or screen — based on time, context, and occupancy state.

---

## How It Works

<b>🚶 Presence & Arrival</b>
<br>

The house tracks when the occupant leaves and returns using GPS zone detection. On departure, it stamps a timestamp, arms the alarm, and adjusts lighting and climate for an empty house. On return, it calculates how long away, delivers a personalised welcome announcement, disarms, and restores the home to its normal active state.

Inside the home, Bluetooth proxy triangulation (Bermuda) detects which room the occupant is in. This enables targeted speaker routing and room-aware automations across the bedroom, livingroom, and kitchen.

---

<b>🌅 Morning Wake-Up</b>
<br>

At a configured alarm time, music starts in the bedroom — with a readiness check to let the Chromecast finish launching before the play command fires. Once the occupant gets up, playback transfers automatically to the rest of the house. The wake-up sequence only runs when the house is in sleep mode and the occupant is home.

---

<b>🌡️ Climate</b>
<br>

A custom season sensor tracks Phuket's wet/dry seasons and feeds into all climate automations. The bedroom AC adjusts its thresholds based on season — lower during the high-humidity rainy months to prevent mold, slightly higher during the dry season. The AC only runs at night when the occupant is home and sleep mode is active.

Lighting and scene automations also respond to weather conditions — rainy or overcast days trigger warmer ambient scenes automatically.

---

<b>💡 Lighting</b>
<br>

Lights adapt to time of day, occupancy, TV state, and weather with no manual switching needed under normal operation. Colour temperature shifts from warm at night to cool-white during the day via Adaptive Lighting. The livingroom responds to which TV app is active — movie apps dim the lights to cinema mode; the TV turning off restores ambient. Outdoor lights run on sunrise/sunset schedules with presence awareness.

---

<b>🔒 Security</b>
<br>

[Frigate NVR](https://frigate.video/) runs on the local server with a Coral TPU for real-time object detection across all cameras. Camera events are processed by a Gemini AI vision model, which produces a plain-language description of what it saw. These are bundled into a notification with a camera snapshot rather than raw motion alerts.

A full security sweep script runs on demand or on schedule: it snapshots all cameras, analyses each with AI vision, then combines the camera report with door/window, leak, gas, and smoke sensor states into a single JARVIS announcement.

A scheduled daily security summary reviews the previous 24 hours of camera activity and delivers it as a concise report before sleep time.

---

<b>🔔 Notifications</b>
<br>

All notifications in the house go through a single routing script that decides the right output channel based on current state:

- **Speaker (TTS)** — voice announcement via JARVIS, volume automatically lowered during evening or sleep mode
- **Phone** — push notification to the occupant's mobile
- **TV overlay** — on-screen notification when the TV is on
- **Persistent** — stored in the HA notification centre

This means every automation — security alerts, timers, presence events, weather warnings — uses the same pipeline and consistently reaches the right place at the right volume.

---

<b>🎵 Media</b>
<br>

[Music Assistant](https://music-assistant.io/) manages all speakers as a multiroom system. Music follows the occupant between rooms based on detected location. Before any TTS announcement fires, the current music state is saved and restored automatically after the announcement ends. The morning wake-up and evening wind-down sequences are fully automated music scenes.

</details>

---

<b>🚿 Bathroom</b>
<br>

Occupancy is tracked session-by-session. A watchdog timer fires an alert if a bathroom session runs unusually long, and all helpers reset cleanly at session end.

---

<b>🍳 Kitchen</b>
<br>

A full automatic kitchen timer system supports start, pause, resume, and auto-alert on completion. A gas cylinder weight sensor (HX711 load cell on the gas bottle) monitors remaining LPG and alerts before it runs out. Water also monitored.

</details>

---

<b>🧺 Laundry</b>
<br>

Laundry sessions are tracked via zone detection at laundry facilities in the area. When the occupant enters a laundry zone, a session timer starts. When they leave, the session is closed and logged.

---

<b>⚡ Energy</b>
<br>

Electricity is tracked against time-of-use tariff — peak (weekday daytime) and off-peak (evenings, weekends) rates are applied automatically. Utility meters track daily, monthly, and yearly consumption in each tariff band. Water consumption is tracked separately. Solar and wind simulation sensors allow energy modelling on the dashboard.

---

<b>🌿 Nature & Social</b>
<br>

Bird detections from the garden cameras are automatically identified and posted to the connected [Mastodon](https://social.nightdestiny.com/@house) account and a public [Telegram channel](https://t.me/live_phuket). The house also generates and posts periodic AI-written status updates about its own state.

---

<b>🔧 System Health</b>
<br>

On every Home Assistant restart, a safety reset automation runs immediately: it resets all boolean helpers that could be left in a wrong state by a crash, and resyncs utility meter tariff selectors to the correct current period.

The full configuration is automatically committed to this repository on a schedule, with AI-generated commit messages and tagged releases that include a changelog and a zipped config archive.

---