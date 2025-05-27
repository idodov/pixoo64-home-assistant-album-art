"""Sensor entity for Pixoo64 Album Art Display."""
import logging
from typing import Any, Dict, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, Entity # SensorEntity is implicitly Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import SensorEntity # Explicitly import SensorEntity

from .const import DOMAIN
from .media import MediaData
# Import other data classes if directly needed by the sensor, though usually passed in entry_data
# from .config import Config
# from .pixoo import PixooDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    _LOGGER.debug(f"Setting up sensor for Pixoo64 Album Art entry: {entry.entry_id}")
    
    # Get the central data store for this config entry
    # This data is prepared in __init__.py's async_setup_entry
    entry_data = hass.data[DOMAIN].get(entry.entry_id)

    if not entry_data:
        _LOGGER.error(
            f"Failed to set up Pixoo64 Album Art sensor: entry data not found for {entry.entry_id}. "
            "This might happen if the main integration setup failed or was interrupted."
        )
        return

    # Extract the MediaData instance (and Config if needed directly by sensor)
    media_data_instance = entry_data.get("media_data")
    # config_instance = entry_data.get("config") # If sensor needs direct config access

    if not media_data_instance: # or not config_instance:
        _LOGGER.error(
            f"Failed to set up Pixoo64 Album Art sensor: media_data (or config) not found in entry_data for {entry.entry_id}."
        )
        return

    # entry_data is hass.data[DOMAIN][entry.entry_id]
    # Ensure it exists (it should have been created by __init__.py's async_setup_entry)
    if DOMAIN not in hass.data or entry.entry_id not in hass.data[DOMAIN]:
        _LOGGER.error(f"Pixoo64 domain or entry data not found in hass.data for sensor setup of {entry.entry_id}.")
        return # Cannot proceed
        
    domain_entry_data = hass.data[DOMAIN][entry.entry_id]

    # Extract the MediaData instance (and Config if needed directly by sensor)
    media_data_instance = domain_entry_data.get("media_data")
    config_instance = domain_entry_data.get("config") 

    if not media_data_instance or not config_instance:
        _LOGGER.error(
            f"Failed to set up Pixoo64 Album Art sensor: media_data or config not found in domain_entry_data for {entry.entry_id}."
        )
        return

    sensor = Pixoo64AlbumArtStatusSensor(hass, entry, config_instance, media_data_instance) # Pass config
    
    # Store the sensor instance in the shared entry_data
    domain_entry_data['status_sensor'] = sensor
    _LOGGER.debug(f"Stored status_sensor instance in domain_entry_data for {entry.entry_id}")

    async_add_entities([sensor], True) # True for update_before_add
    _LOGGER.info(f"Pixoo64 Album Art Status Sensor for entry {entry.entry_id} added.")


class Pixoo64AlbumArtStatusSensor(SensorEntity):
    """Representation of a Pixoo64 Album Art Status sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        config: Config, # Added config
        media_data: MediaData,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._entry = entry
        self._config = config # Store config
        self._media_data = media_data

        self._attr_name = f"Pixoo64 Album Art Status - {entry.title}" 
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_icon = "mdi:image-album"  # Default icon

        # Initialize state and attributes
        self._attr_native_value: Optional[str] = "Initializing"
        self._attr_extra_state_attributes: Dict[str, Any] = {}
        
        _LOGGER.debug(f"Pixoo64AlbumArtStatusSensor '{self._attr_name}' initialized.")

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title or "Pixoo64 Album Art", # Use entry title if available
            manufacturer="Divoom Custom Integration", # Or your GitHub username/org
            model="Pixoo64 Integration",
            # sw_version=self._entry.data.get("version"), # If you store version in entry data
            # configuration_url= # Link to config entry in HA UI if applicable
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # For now, assume available if setup succeeded.
        # Could be tied to pixoo_device.is_connected or similar status if available.
        # Or if media_player entity exists
        if self._media_data and self._media_data.config.media_player_entity_id:
            media_player_state = self.hass.states.get(self._media_data.config.media_player_entity_id)
            return media_player_state is not None # Available if media player entity exists
        return True # Fallback, refine later

    async def async_update(self) -> None:
        """Update the state of the sensor."""
        _LOGGER.debug(f"Updating sensor state for {self.name}")
        
        # The MediaData object should be updated by the main listener in __init__.py
        # This sensor just reads from it.
        if not self._media_data:
            _LOGGER.debug(f"Sensor {self.name}: MediaData not available for update.")
            self._attr_native_value = "Unavailable"
            self._attr_extra_state_attributes = {}
            return

        # Update based on MediaData state
        if self._media_data.is_playing:
            title = self._media_data.title or "Unknown Title"
            artist = self._media_data.artist or "Unknown Artist"
            self._attr_native_value = f"{artist} - {title}"
            if self._media_data.is_tv:
                self._attr_icon = "mdi:television-classic"
            elif self._media_data.is_radio:
                self._attr_icon = "mdi:radio"
            else: # Music or other
                self._attr_icon = "mdi:music-note"

        elif self._media_data.media_player_state == "paused":
            self._attr_native_value = "Paused"
            self._attr_icon = "mdi:pause-circle-outline"
        elif self._media_data.media_player_state == "off" or self._media_data.media_player_state == "idle":
             self._attr_native_value = self._media_data.current_mode or "Idle" # current_mode might be "Clock"
             if self._media_data.current_mode == "Clock":
                 self._attr_icon = "mdi:clock-outline"
             else:
                 self._attr_icon = "mdi:speaker-off" # Or a generic off/idle icon
        else: # Unknown, unavailable, or initializing
            self._attr_native_value = self._media_data.media_player_state or "Unknown"
            self._attr_icon = "mdi:help-circle-outline"


        # Populate attributes from MediaData's dictionary representation
        self._attr_extra_state_attributes = self._media_data.as_dict()
        
        # Remove some potentially redundant or overly verbose attributes if desired
        self._attr_extra_state_attributes.pop("lyrics_available", None) # Example
        # Or select specific attributes to include:
        # selected_attrs = {
        #     "artist": self._media_data.artist,
        #     "album": self._media_data.album,
        #     # ... etc.
        # }
        # self._attr_extra_state_attributes = selected_attrs

        _LOGGER.debug(f"Sensor {self.name} updated. State: {self._attr_native_value}, Attrs: {len(self._attr_extra_state_attributes)} items")

    # If the main update loop in __init__.py calls `media_data.update()` and then
    # needs to tell this sensor to refresh its state from `media_data`,
    # it can call `self.async_schedule_update_ha_state(True)` on the sensor instance.
    # The sensor instance needs to be accessible for that, e.g., stored in hass.data.
    # This is handled by the `async_add_entities([sensor], True)` in async_setup_entry
    # and the fact that the listener in __init__ will trigger updates that HA picks up.
    # However, for more immediate updates after the listener logic, explicit scheduling might be wanted.
    # The listener in __init__.py will need access to the sensor entity instance.
    # A common pattern is to store entities in a list in entry_data if they need to be manipulated post-creation.
    # For now, relying on HA's periodic updates or the effect of state changes being picked up.
    # The _async_handle_media_player_update in __init__.py will eventually call media_data.update(),
    # and then could schedule this sensor's update.

    # To allow external triggering of update (e.g., from the main coordinator/listener):
    def schedule_update(self):
        """Schedule an update for the sensor.
           Can be called from other parts of the integration after MediaData is updated.
        """
        _LOGGER.debug(f"Scheduling HA state update for sensor {self.name}")
        self.async_schedule_update_ha_state(True) # True forces a refresh from the entity's async_update
