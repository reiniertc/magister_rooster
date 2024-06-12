# Magister Rooster

Dit is een custom component voor Home Assistant dat een iCal feed leest van Magister en een sensor aanmaakt met de afspraken voor morgen.

## Installatie

1. Voeg deze repository toe aan HACS.
2. Voeg de volgende configuratie toe aan je `configuration.yaml`:

```yaml
sensor:
  - platform: magister_rooster
    url: 'URL_VAN_DE_ICAL_FEED'
    name: 'Inpakken voor morgen'
