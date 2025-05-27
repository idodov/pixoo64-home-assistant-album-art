"""InputNumber entity for Pixoo64 Album Art Display."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.input_number import InputNumberEntity, MODE_SLIDER
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import UnitOfTime # Import UnitOfTime

from .const import DOMAIN, CONF_PIXOO_LYRICS_SYNC 
from .config import Config

_LOGGER = logging.getLogger(__name__)

# Define default min/max/step for lyrics sync in SECONDS
LYRICS_SYNC_MIN_S = -10  # seconds
LYRICS_SYNC_MAX_S = 10   # seconds
LYRICS_SYNC_STEP_S = 1   # second
LYRICS_SYNC_DEFAULT_S = 0 # Default for the entity state in seconds (config might still use -1 for auto)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the input_number platform."""
    _LOGGER.debug(f"Setting up input_number for Pixoo64 Album Art entry: {entry.entry_id}")
    
    entry_data = hass.data[DOMAIN].get(entry.entry_id)
    if not entry_data:
        _LOGGER.error(f"Failed to set up input_number: entry data not found for {entry.entry_id}.")
        return

    config: Config = entry_data["config"]
    # pixoo_device: PixooDevice = entry_data["pixoo_device"] # Not directly needed by this entity

    lyrics_sync_number = PixooLyricsSyncNumber(hass, entry, config)
    async_add_entities([lyrics_sync_number], True)
    _LOGGER.info(f"Pixoo64 Lyrics Sync input_number for entry {entry.entry_id} added.")


class PixooLyricsSyncNumber(InputNumberEntity):
    """Representation of a Pixoo64 Lyrics Sync number entity."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, config: Config):
        """Initialize the lyrics sync number entity."""
        self.hass = hass
        self._entry = entry
        self._config = config # Live config object

        self._attr_name = f"Pixoo64 Lyrics Sync Offset - {entry.title}"
        self._attr_unique_id = f"{entry.entry_id}_lyrics_sync_offset" 
        self._attr_icon = "mdi:timer-sync-outline" 
        
        self._attr_native_min_value = LYRICS_SYNC_MIN_S
        self._attr_native_max_value = LYRICS_SYNC_MAX_S
        self._attr_native_step = LYRICS_SYNC_STEP_S
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS # Set unit to seconds
        self._attr_mode = MODE_SLIDER 

        # The Config object stores pixoo_lyrics_sync in milliseconds with -1 as default.
        # This entity will display and operate in seconds.
        current_value_ms = getattr(self._config, CONF_PIXOO_LYRICS_SYNC, -1) # Get value in ms from config
        
        if current_value_ms == -1: # Special "auto" value from config
            self._attr_native_value = LYRICS_SYNC_DEFAULT_S # Display as 0 seconds in UI
        else:
            # Convert ms from config to seconds for the entity state
            self._attr_native_value = float(current_value_ms / 1000.0)

        # Clamp the initial value to be within the defined min/max for the entity
        self._attr_native_value = max(LYRICS_SYNC_MIN_S, min(LYRICS_SYNC_MAX_S, self._attr_native_value))
        
        _LOGGER.debug(f"Initialized lyrics_sync_offset (seconds) to: {self._attr_native_value} (from config ms value: {current_value_ms})")

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title or "Pixoo64 Album Art",
            manufacturer="Divoom Custom Integration",
            model="Pixoo64 Integration",
        )

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        clamped_value = max(self._attr_native_min_value, min(self._attr_native_max_value, value))
        _LOGGER.debug(f"Lyrics sync offset changed to: {clamped_value} for {self.unique_id}")
        self._attr_native_value = clamped_value
        
        # Update the live config object (still expecting milliseconds, or -1 for auto)
        # If the UI value is 0 and the original default was -1 (auto), save -1.
        # Otherwise, convert seconds back to milliseconds.
        value_to_save_ms: int
        if clamped_value == LYRICS_SYNC_DEFAULT_S and getattr(self._config, CONF_PIXOO_LYRICS_SYNC, -1) == -1 : # Check original default
             value_to_save_ms = -1 # Preserve -1 if UI is set to 0 and config was -1 (auto)
        else:
            value_to_save_ms = int(clamped_value * 1000) # Convert seconds to ms

        setattr(self._config, CONF_PIXOO_LYRICS_SYNC, value_to_save_ms)

        # Persist this selection in ConfigEntry options (still in milliseconds)
        new_options = {**self._entry.options, CONF_PIXOO_LYRICS_SYNC: value_to_save_ms}
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        
        _LOGGER.info(f"Lyrics sync offset for {self.unique_id} set to {clamped_value}s ({value_to_save_ms}ms). Config updated.")
        self.async_write_ha_state() 

