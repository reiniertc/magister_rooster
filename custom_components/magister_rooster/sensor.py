import logging
from datetime import timedelta, datetime
import requests
from icalendar import Calendar
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util.dt import now

_LOGGER = logging.getLogger(__name__)

CONF_URL = "url"

DEFAULT_NAME = "Inpakken voor morgen"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_URL): cv.url,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

def setup_platform(hass, config, add_entities, discovery_info=None):
    url = config.get(CONF_URL)
    name = config.get(CONF_NAME)

    add_entities([MagisterRoosterSensor(name, url)], True)

class MagisterRoosterSensor(Entity):
    def __init__(self, name, url):
        self._name = name
        self._url = url
        self._state = None
        self._events = []

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    def update(self):
        try:
            response = requests.get(self._url)
            response.raise_for_status()
            cal = Calendar.from_ical(response.text)
            now_utc = now()
            tomorrow = (now_utc + timedelta(days=1)).date()
            
            events = []
            for component in cal.walk():
                if component.name == "VEVENT":
                    event_start = component.get('dtstart').dt
                    if isinstance(event_start, datetime):
                        event_start = event_start.date()
                    
                    if event_start == tomorrow:
                        summary = component.get('summary')
                        events.append(summary)
            
            self._events = events
            self._state = ", ".join(events)

        except requests.exceptions.RequestException as e:
            _LOGGER.error(f"Error fetching iCal feed: {e}")
            self._state = None
