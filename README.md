# HTTP Garage Toggle (Home Assistant)

Home Assistant custom integration für ein Garagentor mit **HTTP-Toggle**:
- `open/close/stop` senden denselben Request (z. B. `GET /?switch=1`)
- Status wird per Polling aus einer Seite gelesen, die `Door Status: OPEN|CLOSED` enthält
- `device_class: garage`, funktioniert mit HomeKit Bridge

## Installation
1. Ordner `custom_components/http_garage_toggle` in dein HA `config/` kopieren (oder über HACS als Custom Repo).
2. Home Assistant neu starten.
3. **Einstellungen → Geräte & Dienste → Integration hinzufügen** → „HTTP Garage Toggle“.

## Konfiguration (UI)
- **Base URL**: z. B. `http://192.168.1.xx`
- **Toggle path**: `/?switch=1`
- **Status path**: `/`
- **Scan interval**: `35`
- Optional: **Username / Password** (Basic Auth)

## Credits / License
Inspired by / based on [apexad/homebridge-garagedoor-command](https://github.com/apexad/homebridge-garagedoor-command).  
MIT License – siehe `LICENSE`.
