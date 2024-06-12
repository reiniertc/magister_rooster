import logging
from datetime import timedelta, datetime
import requests
from icalendar import Calendar
import voluptuous as vol
import re

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util.dt import now, get_time_zone, as_local

_LOGGER = logging.getLogger(__name__)

CONF_URL = "url"
CONF_REGEX_PATTERN = "regex_pattern"

DEFAULT_NAME = "Magister Rooster"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_URL): cv.url,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_REGEX_PATTERN): cv.string,
})

def setup_platform(hass, config, add_entities, discovery_info=None):
    url = config.get(CONF_URL)
    name = config.get(CONF_NAME)
    regex_pattern = config.get(CONF_REGEX_PATTERN)

    add_entities([
        VolgendeSchooldagSensor(hass, name, url, regex_pattern),
        InpakkenVoorMorgenSensor(hass, name, url, regex_pattern),
        BegintijdMorgenSensor(hass, name, url, regex_pattern),
        EindtijdMorgenSensor(hass, name, url, regex_pattern),
        BegintijdVandaagSensor(hass, name, url, regex_pattern),
        EindtijdVandaagSensor(hass, name, url, regex_pattern)
    ], True)

class MagisterRoosterBaseSensor(Entity):
    def __init__(self, hass, name, url, regex_pattern=None):
        self._name = name
        self._url = url
        self._state = None
        self._events = []
        self._next_school_day = None
        self._events_today = []
        self._events_tomorrow = []
        self.hass = hass
        self._regex_pattern = re.compile(regex_pattern) if regex_pattern else None

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
            today = now_utc.date()
            tomorrow = today + timedelta(days=1)
            self._next_school_day = self.get_next_school_day(today)

            self._events_today = []
            self._events_tomorrow = []
            for component in cal.walk():
                if component.name == "VEVENT":
                    event_start = component.get('dtstart').dt
                    event_end = component.get('dtend').dt
                    summary = component.get('summary')

                    # Alleen gebeurtenissen die geen hele dag zijn
                    if 'allday' not in component:
                        # Converteer naar lokale tijdzone
                        if isinstance(event_start, datetime):
                            event_start = as_local(event_start)
                        if isinstance(event_end, datetime):
                            event_end = as_local(event_end)

                        event_start_date = event_start.date() if isinstance(event_start, datetime) else event_start
                        event_end_date = event_end.date() if isinstance(event_end, datetime) else event_end

                        if event_start_date == today:
                            self._events_today.append((event_start, event_end, summary))
                        if event_start_date == self._next_school_day:
                            self._events_tomorrow.append((event_start, event_end, summary))

            self._events = self._events_today + self._events_tomorrow

        except requests.exceptions.RequestException as e:
            _LOGGER.error(f"Error fetching iCal feed: {e}")
            self._state = None

    def get_next_school_day(self, today):
        # Assuming a 5-day school week, no holidays
        if today.weekday() == 4:  # Friday
            return today + timedelta(days=3)
        elif today.weekday() == 5:  # Saturday
            return today + timedelta(days=2)
        else:
            return today + timedelta(days=1)

    def filter_summary(self, summary):
        if self._regex_pattern:
            match = self._regex_pattern.search(summary)
            if match:
                return match.group(1)
        return summary

class VolgendeSchooldagSensor(MagisterRoosterBaseSensor):
    def __init__(self, hass, name, url, regex_pattern=None):
        super().__init__(hass, name, url, regex_pattern)

    @property
    def name(self):
        return f"{self._name} Volgende Schooldag"

    def update(self):
        super().update()
        if self._next_school_day:
            self._state = self._next_school_day.strftime("%A %d %B")

class InpakkenVoorMorgenSensor(MagisterRoosterBaseSensor):
    @property
    def name(self):
        return f"{self._name} Inpakken voor morgen"

    def update(self):
        super().update()
        if self._events_tomorrow:
            unique_summaries = list(set(self.filter_summary(event[2]) for event in self._events_tomorrow))
            self._state = ", ".join(unique_summaries)
        else:
            self._state = None

class BegintijdMorgenSensor(MagisterRoosterBaseSensor):
    @property
    def name(self):
        return f"{self._name} Begintijd morgen"

    def update(self):
        super().update()
        if self._events_tomorrow:
            first_event = min(self._events_tomorrow, key=lambda event: event[0])
            self._state = first_event[0].strftime("%H:%M")
        else:
            self._state = None

class EindtijdMorgenSensor(MagisterRoosterBaseSensor):
    @property
    def name(self):
        return f"{self._name} Eindtijd morgen"

    def update(self):
        super().update()
        if self._events_tomorrow:
            last_event = max(self._events_tomorrow, key=lambda event: event[1])
            self._state = last_event[1].strftime("%H:%M")
        else:
            self._state = None

class BegintijdVandaagSensor(MagisterRoosterBaseSensor):
    @property
    def name(self):
        return f"{self._name} Begintijd vandaag"

    def update(self):
        super().update()
        if self._events_today:
            first_event = min(self._events_today, key=lambda event: event[0])
            self._state = first_event[0].strftime("%H:%M")
        else:
            self._state = None

class EindtijdVandaagSensor(MagisterRoosterBaseSensor):
    @property
    def name(self):
        return f"{self._name} Eindtijd vandaag"

    def update(self):
        super().update()
        if self._events_today:
            last_event = max(self._events_today, key=lambda event: event[1])
            self._state = last_event[1].strftime("%H:%M")
        else:
            self._state = None
