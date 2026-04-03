</p>
<h1 align="center">
  <a name="logo" href="http://nightdestiny.com"><img src="https://github.com/simplemice/home_assistant/blob/main/screenshots/casa_de_ratton.png" alt="Casa de Rattón" width="500"></a>
  <br>
  Casa de Rattón
  <br>
  Home Assistant Configuration (Testing Instance with Fully Realistic Simulation Packages)
</h1>

<h2>PLEASE READ LICENSE</h2>

***

Like all other Home Assistant instances this is also a Work in Progress :D

***

This repo contains the tested, working [Home Assistant](https://home-assistant.io/) configuration for **Casa de Rattón**. Below are links to the devices currently being used, blog posts, and other HA enthusists that provided inspiration and configs to help build this config.

#### Casa de Rattón's Three Laws of Home Automation:

When designing Casa de Rattón's automations I have made every effort to prioritize the solution based on the following three laws. 

**First Law: Every automation or action should be the result of a passive sensor or indirect action**.

**Second Law: An automation can be triggered by voice command only when Law 1 cannot be achieved**.

**Third Law: An automation or action can be trigger by a physical switch or as the result of a direct iteraction only when Law 1 and Law 2 cannot be achieved.**

## Some statistics about Test Installation:

Description | value
-- | --
Number of entities | 2861
Number of sensors | 1677
Current Version | 2026.4.0
Total Automations | 118
Total Scripts | 30
Total Lights | 41
Total Switches | 207
Total Scenes | 14
Total Players | 19

## Current installed extensions:

### Add-ons
- Advanced SSH & Web Terminal
- Matter Server
- Matterbridge
- Music Assistant
- Network UPS Tools
- openWakeWord
- Piper
- Samba share
- Studio Code Server
- Whisper
- Zircon3D Proxy

### Custom integrations
- [Adaptive Lighting](https://github.com/basnijholt/adaptive-lighting)
- [Alarmo](https://github.com/nielsfaber/alarmo)
- [Astroweather](https://github.com/mawinkler/astroweather)
- [Audiobookshelf](https://github.com/wolffshots/hass-audiobookshelf)
- [Bermuda Ble Trilateration](https://github.com/agittins/bermuda)
- [Better Thermostat](https://github.com/KartoffelToby/better_thermostat)
- [Blitzortung.Org Lightning Detector](https://github.com/mrk-its/homeassistant-blitzortung)
- [Browser Mod](https://github.com/thomasloven/hass-browser_mod)
- [Chime Tts](https://github.com/nimroddolev/chime_tts)
- [Cloudflare Speed Test](https://github.com/DigitallyRefined/ha-cloudflare-speed-test)
- [Flightradar24](https://github.com/AlexandrErohin/home-assistant-flightradar24)
- [Fontawesome](https://github.com/thomasloven/hass-fontawesome)
- [Frigate](https://github.com/blakeblackshear/frigate-hass-integration)
- [Frosted Glass Theme Manager](https://github.com/wessamlauf/frosted-glass-manager)
- [Generate Readme](https://github.com/custom-components/readme)
- [HACS](https://github.com/hacs/integration)
- [Hass Favicon](https://github.com/thomasloven/hass-favicon)
- [Hyperhdr](https://github.com/mjoshd/hyperhdr-ha)
- [Ing Stocks Plus](https://github.com/Sundancer78/hacs_ingstocksplus)
- [Jellyha](https://github.com/zupancicmarko/JellyHA)
- [Llm Vision](https://github.com/valentinfrlch/ha-llmvision)
- [Mikrotik Router](https://github.com/tomaae/homeassistant-mikrotik_router)
- [Mqtt Media Player](https://github.com/bkbilly/mqtt_media_player)
- [Multiscrape](https://github.com/danieldotnl/ha-multiscrape)
- [Music Assistant Jukebox](https://github.com/DJS91/HAMusicAssistantJukebox)
- [Noaa Space Weather](https://github.com/tcarwash/home-assistant_noaa-space-weather)
- [Node Red Companion](https://github.com/zachowj/hass-node-red)
- [Passive Ble Monitor Integration](https://github.com/custom-components/ble_monitor)
- [Pirate Weather](https://github.com/Pirate-Weather/pirate-weather-ha)
- [Powercalc](https://github.com/bramstroker/homeassistant-powercalc)
- [Proxmoxve](https://github.com/dougiteixeira/proxmoxve)
- [Radarr Upcoming Media](https://github.com/custom-components/sensor.radarr_upcoming_media)
- [Remote Home Assistant](https://github.com/custom-components/remote_homeassistant)
- [Smartir](https://github.com/smartHomeHub/SmartIR)
- [Sonarr Upcoming Media](https://github.com/custom-components/sensor.sonarr_upcoming_media)
- [Spook 👻 Your Homie](https://github.com/frenck/spook)
- [Sun2](https://github.com/pnbruckner/ha-sun2)
- [Thermal Comfort](https://github.com/dolezsa/thermal_comfort)
- [Tvoverlay Ui](https://github.com/manjotsc/ha-tvoverlay_ui)
- [Watchman](https://github.com/dummylabs/thewatchman)
- [Windy Webcams](https://github.com/earendil06/Windy-Webcams)
- [Xai Grok Conversation](https://github.com/braytonstafford/grok_conversation)
- [Xiaomi Gateway 3](https://github.com/AlexxIT/XiaomiGateway3)
- [Xiaomi Miot](https://github.com/al-one/hass-xiaomi-miot)
- [Youtube](https://github.com/custom-components/youtube)

### Lovelace plugins
- [Adguard Card](https://github.com/homeassistant-extras/adguard-card)
- [Advanced Camera Card](https://github.com/dermotduffy/advanced-camera-card)
- [Apexcharts Card](https://github.com/RomRider/apexcharts-card)
- [Astroweather Card](https://github.com/mawinkler/astroweather-card)
- [Atomic Calendar Revive](https://github.com/totaldebug/atomic-calendar-revive)
- [Auto Entities](https://github.com/thomasloven/lovelace-auto-entities)
- [Battery State Card / Entity Row](https://github.com/maxwroc/battery-state-card)
- [Better Moment Card](https://github.com/ibz0q/better-moment-card)
- [Better Thermostat Ui](https://github.com/KartoffelToby/better-thermostat-ui-card)
- [Blitzortung Lightning Card](https://github.com/timmaurice/lovelace-blitzortung-lightning-card)
- [Bubble Card](https://github.com/Clooos/Bubble-Card)
- [Button Card](https://github.com/custom-cards/button-card)
- [Compass Card](https://github.com/tomvanswam/compass-card)
- [Config Template Card](https://github.com/iantrich/config-template-card)
- [Entity Progress Card](https://github.com/francois-le-ko4la/lovelace-entity-progress-card)
- [Flex Table   Highly Customizable, Data Visualization](https://github.com/custom-cards/flex-table-card)
- [Flightradar Flight Card](https://github.com/plckr/flightradar-flight-card)
- [Hass Hue Icons](https://github.com/arallsopp/hass-hue-icons)
- [Horizon Card](https://github.com/rejuvenate/lovelace-horizon-card)
- [Layout Card](https://github.com/thomasloven/lovelace-layout-card)
- [Logbook Card](https://github.com/royto/logbook-card)
- [Lovelace Bubble Room](https://github.com/mon3y78/Lovelace-Bubble-room)
- [Mediarr Card](https://github.com/Vansmak/mediarr-card)
- [Mediocre Hass Media Player Cards](https://github.com/antontanderup/mediocre-hass-media-player-cards)
- [Mini Climate Card](https://github.com/artem-sedykh/mini-climate-card)
- [Mini Graph Card](https://github.com/kalkih/mini-graph-card)
- [Mushroom](https://github.com/piitaya/lovelace-mushroom)
- [Navbar Card](https://github.com/joseluis9595/lovelace-navbar-card)
- [Power Flow Card Plus](https://github.com/flixlix/power-flow-card-plus)
- [Powerpilz](https://github.com/gregor-autischer/PowerPilz)
- [Simple Swipe Card](https://github.com/nutteloost/simple-swipe-card)
- [Solar Card](https://github.com/victorigualada/lovelace-solar-card)
- [Stack In Card](https://github.com/custom-cards/stack-in-card)
- [Trashcard](https://github.com/idaho/hassio-trash-card)
- [Trend Analysis Card](https://github.com/Riscue/trend-analysis-card)
- [Tv Remote Card](https://github.com/marrobHD/tv-card)
- [Universal Remote Card](https://github.com/Nerwyn/universal-remote-card)
- [Upcoming Media Card](https://github.com/NemesisRE/upcoming-media-card)
- [Upcoming Media Card](https://github.com/custom-cards/upcoming-media-card)
- [Vertical Stack In Card](https://github.com/ofekashery/vertical-stack-in-card)
- [Wallpanel](https://github.com/j-a-n/lovelace-wallpanel)
- [Weather Alerts Card](https://github.com/seevee/weather_alerts_card)
- [Wind Rose Card](https://github.com/aukedejong/lovelace-windrose-card)

### Themes
- [Frosted Glass Theme](https://github.com/wessamlauf/homeassistant-frosted-glass-themes)


***

Copyright @2026 [Nightdestiny Group](https://nightdestiny.com) and [Casa De Ratton](https://social.nightdestiny.com/@house)

This README.md generated automaticaly after each update, by the [custom readme integration](https://github.com/custom-components/readme)