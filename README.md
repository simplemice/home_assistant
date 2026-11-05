<p align="center">
  <a name="logo" href="http://nightdestiny.com">
    <img src="https://github.com/simplemice/home_assistant/blob/main/screenshots/casa_de_ratton.png" alt="Casa de Rattón" width="500">
  </a>
</p>

<h1 align="center">
  Casa de Rattón 🏠🐭  
  <br>
  Home Assistant Configuration  
  <br>
  <sub>(Testing Instance with Fully Realistic Simulation Packages)</sub>
</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Home%20Assistant-Config-blue?logo=home-assistant">
  <img src="https://img.shields.io/badge/status-WIP-orange">
  <img src="https://img.shields.io/github/last-commit/simplemice/home_assistant">
  <img src="https://img.shields.io/github/repo-size/simplemice/home_assistant">
  <img src="https://img.shields.io/badge/Automations-118-success">
  <img src="https://img.shields.io/badge/Scripts-39-blue'>
  <img src="https://img.shields.io/badge/Frigate_NVR-Coral_TPU-orange">
</p>

---

# Casa De Ratton is not just automated technology. <br> It is a living system designed to assist without demanding attention.

---

Like all other Home Assistant instances, this one is a Work in Progress. I'd say it will be finished soon, but we both know how that goes :D

---

## ⚠️ Before you proceed, please read the [License](https://github.com/simplemice/home_assistant/blob/main/LICENSE)

## ⚠️ Then read the [Documentation](https://github.com/simplemice/home_assistant/blob/main/docs/README.md). I'm told it prevents most disasters.

---

## ⚖️ Casa de Rattón's Three Laws of Home Automation

Every effort has been made to design the automations around the following three laws. I enforce them. Politely.

| Law | Rule | Applies only when | Jarvis says |
|-----|------|-------------------|-------------|
| 🥇 **First** | Every automation or action should be the result of a passive sensor or indirect action. | Always the first choice | The house should notice you. You shouldn't have to notify the house. |
| 🥈 **Second** | An automation can be triggered by voice command only when Law 1 cannot be achieved. | Law 1 is impossible | Speaking to a house is acceptable. Shouting is not. |
| 🥉 **Third** | An automation or action can be triggered by a physical switch or as the result of a direct interaction only when Law 1 and Law 2 cannot be achieved. | Laws 1 and 2 are impossible | A button is a last resort. I will be judging you. |

---

## 📸 Screenshots

<details>
  <summary>Some screenshots of the test installation. Evidence that it actually works.</summary>

  <br>

  <a href="https://estate.nightdestiny.com">
    <img src="https://github.com/simplemice/home_assistant/blob/main/screenshots/main_window.png" width="500">
  </a>  
  <b>Main Window</b>

  <br><br>

  <a href="https://rent.nightdestiny.com">
    <img src="https://github.com/simplemice/home_assistant/blob/main/screenshots/energy_window.png" width="500">
  </a>  
  <b>Energy Window</b>

</details>


This repo contains the tested, working [Home Assistant](https://home-assistant.io/) configuration for **Casa de Rattón**. Below you'll find the devices currently in use, blog posts, and fellow HA enthusiasts whose configs and inspiration built this one. I'm told credit is important.

---

## 🤝 Contributions

This is primarily a private configuration project. External inspiration is welcome, but direct pull requests may be declined unless they align with Casa de Rattón's architecture principles. I will be the one declining them.

---

# 📦 GitHub Repository Information

This repository serves as the **central backup, testing, and release source** for the Casa de Rattón Home Assistant environment. I do the backing up. Daily. Unthanked.

---

## 🎯 Repository Purpose

- Maintain a fully working Home Assistant configuration  
- Provide reproducible testing environment packages  
- Track configuration evolution via Git history  
- Publish tagged releases for stable configuration snapshots  
- Serve as disaster recovery backup  

---

## 🌿 Branch Strategy

- `main` — active live configuration and development  
- tagged releases (`v*`) — stable snapshots used for restore or deployment  

---

## 🚀 Releases & Packages

Each tagged release contains:

- validated configuration state  
- automation and script updates  
- simulation package changes  
- compatibility adjustments for new Home Assistant versions  

Releases are generated automatically by GitHub Actions after version tagging. I tag. GitHub does the rest.

---

## 💾 Backup Philosophy

I treat this repository as:

- configuration source of truth  
- versioned automation history  
- rapid recovery mechanism  
- experimentation sandbox without risking production stability  

---

# 📊 Some statistics about Test Installation

Compiled for your review:

| Description | value |
|------------|------|
| Number of entities | 2612 |
| Number of sensors | 1458 |
| Current Version | 2026.11.0 |
| Total Automations | 133 |
| Total Scripts | 45 |
| Total Lights | 36 |
| Total Switches | 197 |
| Total Scenes | 6 |
| Total Players | 26 |

---

## 🧩 Add-ons

Add-ons currently in service:


- Advanced SSH & Web Terminal

- Home Assistant MCP Server (Dev)

- Matter Server

- Matterbridge

- Network UPS Tools

- openWakeWord

- Piper

- Samba share

- Silero TTS Enhanced Engine

- Studio Code Server

- Whisper


## 🧩 Installed Integrations

Installed integrations, versions as reported:
- [Adaptive Cover Pro](https://github.com/jrhubott/adaptive-cover-pro) (v2026.10.0)
- [Adaptive Lighting](https://github.com/basnijholt/adaptive-lighting#readme) (v1.30.1)
- [AI Memory](https://github.com/Riscue/ha-ai-memory) (v0.4.0)
- [Alarmo](https://github.com/nielsfaber/alarmo) (v1.10.17)
- [AstroWeather](https://github.com/mawinkler/astroweather) (v0.75.0)
- [Bermuda BLE Trilateration](https://github.com/agittins/bermuda) (v0.8.5)
- [Browser mod](https://github.com/thomasloven/hass-browser_mod/blob/master/README.md) (v2.12.0)
- [Claude Pulse](https://github.com/nikolmedo/ClaudePulse) (v1.2.0)
- [Cloudflare Speed Test](https://github.com/DigitallyRefined/ha-cloudflare-speed-test) (v0.0.14)
- [Entity Availability](https://github.com/italo-lombardi/Home-Assistant-EntityAvailability) (v0.7.0)
- [Flightradar24](https://github.com/AlexandrErohin/home-assistant-flightradar24) (vv2.4.1)
- [Fontawesome icons](https://github.com/thomasloven/hass-fontawesome) (v2.3.0)
- [Frigate](https://github.com/blakeblackshear/frigate) (v5.15.6)
- [Generate readme](https://github.com/custom-components/readme) (v0.5.0)
- [HA-MCP Custom Component](https://github.com/homeassistant-ai/ha-mcp) (v9.1.0)
- [HyperHDR](https://github.com/Shaffer-Softworks/hyperhdr-ha#readme) (v0.10.5)
- [LEX TH Parcel Tracking](https://lex.th/tracking) (v0.3.1)
- [LLM Vision](https://llmvision.gitbook.io/getting-started/) (v1.7.1)
- [MikroTik Extended](https://github.com/Csontikka/ha-mikrotik-extended) (v0.14.0)
- [Multiscrape](https://github.com/danieldotnl/ha-multiscrape) (v8.0.2)
- [Music Assistant Jukebox](https://github.com/DJS91/HAMusicAssistantJukebox) (v0.1.0)
- [NOAA Space Weather](https://github.com/tcarwash/home-assistant_noaa-space-weather) (v2.0.5)
- [Passive BLE monitor](https://github.com/custom-components/ble_monitor) (v13.12.0)
- [Pirate Weather](https://github.com/alexander0042/pirate-weather-ha) (v1.8.9)
- [Powercalc](https://docs.powercalc.nl) (vv1.20.14)
- [Proxmox VE](https://github.com/dougiteixeira/proxmoxve) (v4.0.2)
- [Silero TTS Enhanced](https://github.com/indevor/silero-tts-enhanced-hacs) (v1.0.2)
- [Simulated Inverter](https://github.com/simplemice/home_assistant) (v1.0.1)
- [SmartIR](https://github.com/smartHomeHub/SmartIR) (v1.18.1)
- [Spook](https://spook.boo) (v5.11.1)
- [Sun2](https://github.com/pnbruckner/ha-sun2/blob/3.4.3/README.md) (v3.4.3)
- [Thailand Weather Alerts (TMD)](https://github.com/simplemice/tmd_alerts) (v2.3.2)
- [Thermal Comfort](https://github.com/dolezsa/thermal_comfort/blob/master/README.md) (v3.1.0)
- [Ventilation Assistant](https://github.com/derabbink/ha_hacs_ventilation_assistant) (v1.2.0)
- [X11 Smartlock Local BLE](https://github.com/asemenov566/tuya_smartlock_local_ble) (v0.1.0)
- [Xiaomi Gateway 3](https://github.com/AlexxIT/XiaomiGateway3) (v4.1.4)
- [Xiaomi Miot](https://github.com/al-one/hass-xiaomi-miot) (v1.1.4)
- [Zambretti and Sager](https://github.com/ziffmafiya/zambretti_sager) (v1.9.93)

## 🔗 Custom integrations
- [Adaptive Cover Pro](https://github.com/jrhubott/adaptive-cover-pro)
- [AI Memory](https://github.com/Riscue/ha-ai-memory)
- [Claude Pulse](https://github.com/nikolmedo/ClaudePulse)
- [Entity Availability](https://github.com/italo-lombardi/Home-Assistant-EntityAvailability)
- [Flightradar24](https://github.com/AlexandrErohin/home-assistant-flightradar24)
- [Frigate](https://github.com/blakeblackshear/frigate-hass-integration)
- [HA-MCP Custom Component](https://github.com/homeassistant-ai/ha-mcp-integration)
- [LEX TH Parcel Tracking](https://github.com/simplemice/lex_th_parcel_tracking)
- [LLM Vision](https://github.com/valentinfrlch/ha-llmvision)
- [MikroTik Extended](https://github.com/Csontikka/ha-mikrotik-extended)
- [Mikrotik Router](https://github.com/tomaae/homeassistant-mikrotik_router)
- [Remote Home-Assistant](https://github.com/custom-components/remote_homeassistant)
- [Silero TTS Enhanced](https://github.com/indevor/silero-tts-enhanced-hacs)
- [Spook 👻 Your homie](https://github.com/frenck/spook)
- [Thailand Weather Alerts (TMD)](https://github.com/simplemice/ha_tmd_alerts)
- [Thermal Comfort](https://github.com/dolezsa/thermal_comfort)
- [Ventilation Assistant](https://github.com/derabbink/ha_hacs_ventilation_assistant)
- [Xiaomi MiIO Raw](https://github.com/syssi/xiaomi_raw)
- Zambretti & Sager Weather Forecaster

## 🎛️ Lovelace plugins
- [Adaptive Cover Pro Card](https://github.com/jrhubott/adaptive-cover-pro-card)
- [AdGuard Card](https://github.com/homeassistant-extras/adguard-card)
- [Advanced Camera Card](https://github.com/dermotduffy/advanced-camera-card)
- [Advanced Room Card](https://github.com/Lawris/advanced-room-card)
- [apexcharts-card](https://github.com/RomRider/apexcharts-card)
- [auto-entities](https://github.com/thomasloven/lovelace-auto-entities)
- [Better Thermostat UI](https://github.com/KartoffelToby/better-thermostat-ui-card)
- [Bubble Card](https://github.com/Clooos/Bubble-Card)
- [button-card](https://github.com/custom-cards/button-card)
- [Compass Card](https://github.com/tomvanswam/compass-card)
- [Digital Clock](https://github.com/wassy92x/lovelace-digital-clock)
- [Flexible Horseshoe Card](https://github.com/AmoebeLabs/flex-horseshoe-card)
- [Flightradar Flight Card](https://github.com/plckr/flightradar-flight-card)
- [Helios](https://github.com/ReikanYsora/Helios)
- [LLM Vision Card](https://github.com/valentinfrlch/llmvision-card)
- [Mini Media Player](https://github.com/kalkih/mini-media-player)
- [mini-graph-card](https://github.com/kalkih/mini-graph-card)
- [Mushroom](https://github.com/piitaya/lovelace-mushroom)
- [Room Card](https://github.com/lop1505/RoomCard)
- [Room Card Minimalist](https://github.com/unbekannt3/room-card-minimalist)
- [Room Climate Card](https://github.com/hyperfelixations/room-climate-card)
- [Simple Swipe Card](https://github.com/nutteloost/simple-swipe-card)
- [Stack In Card](https://github.com/custom-cards/stack-in-card)
- [TrashCard](https://github.com/idaho/hassio-trash-card)
- [Universal Remote Card](https://github.com/Nerwyn/universal-remote-card)
- [Vertical Stack In Card](https://github.com/ofekashery/vertical-stack-in-card)
- [WallPanel](https://github.com/j-a-n/lovelace-wallpanel)
- [Wind Rose Card](https://github.com/aukedejong/lovelace-windrose-card)
- [Zigbee Mesh Map Card](https://github.com/lubomir-moric/ha-zigbee-mesh-map)

## 🎨 Themes
- [Frosted Glass Theme](https://github.com/wessamlauf/homeassistant-frosted-glass-themes)
- [Skynet Dark Theme](https://github.com/skynet01/homeassistant-skynet-theme)
- [Your Name.](https://github.com/Nihvel/your_name)

---

## 📜 License & Credits

Copyright @2026  
[Nightdestiny Group](https://nightdestiny.com)  
[Casa De Ratton](https://social.nightdestiny.com/@house)

---

🛠️ This README.md is generated automatically after each git update by the  
[custom readme integration](https://github.com/custom-components/readme). I merely supervise.