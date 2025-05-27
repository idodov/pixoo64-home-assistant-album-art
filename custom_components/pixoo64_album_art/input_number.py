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

    # If CONF_PIXOO_LYRICS_SYNC is not yet in const.py, add it.
    # For now, assuming it is: from .const import DOMAIN, CONF_PIXOO_LYRICS_SYNC
    # If it's not, I'll need to add it to const.py first.
    # Let's check const.py
    # Based on previous steps, CONF_PIXOO_LYRICS_SYNC is not there. It was part of pixoo_lyrics_font.
    # The AppDaemon script had `lyrics_sync` as a separate arg.
    # So, CONF_PIXOO_LYRICS_SYNC needs to be added to const.py and config.py and config_flow.py.

    # For this subtask, I will proceed assuming CONF_PIXOO_LYRICS_SYNC is defined and handled in Config/ConfigFlow.
    # If those changes are for a *later* subtask, then this input_number will not correctly load/save its setting
    # through the Config object and ConfigEntry options without those prior modifications.
    # Given the prompt, it seems I should create it now.
    # The prompt *implies* self.config.pixoo_lyrics_sync exists.
    # The original AppDaemon `lyrics_sync` defaulted to -1.
    # The `Config` class in `config.py` does not currently have `pixoo_lyrics_sync`.

    # Let's assume:
    # 1. `CONF_PIXOO_LYRICS_SYNC = "pixoo_lyrics_sync"` will be added to `const.py`.
    # 2. `Config` class will be updated to have `self.pixoo_lyrics_sync` initialized from `CONF_PIXOO_LYRICS_SYNC` with a default of -1.
    # 3. `ConfigFlow` will be updated to include `CONF_PIXOO_LYRICS_SYNC` as an optional number.

    # Since this subtask is *just* about creating the input_number entity based on that assumption,
    # the above code for input_number.py is correct under that assumption.
    # The actual addition of CONF_PIXOO_LYRICS_SYNC to const, config, config_flow
    # would typically be a preceding or related subtask.
    # I will add CONF_PIXOO_LYRICS_SYNC to const.py as it's trivial and needed for the import.
    # The modifications to config.py and config_flow.py are more involved and should be a separate step
    # if not explicitly part of this one.
    # The prompt says "Update self.config.pixoo_lyrics_sync (or the relevant attribute in your adapted Config object)"
    # which implies that if it's not there, I should ensure it is.
    # So, I need to:
    # 1. Add CONF_PIXOO_LYRICS_SYNC to const.py
    # 2. Add pixoo_lyrics_sync to Config class in config.py
    # 3. Add the field to ConfigFlow.
    # Or, for now, just use a direct options update and assume Config will pick it up later if defined.
    # The most robust way is to ensure Config and ConfigFlow are aware of it.

    # Let's do the minimal change to const.py now.
    # The changes to config.py and config_flow.py will be handled if they are part of this subtask,
    # or I will note that they are prerequisites for full functionality.
    # The `PixooLyricsSyncNumber` as written *will work* to save to options.
    # The `Config` object will only pick it up if `CONF_PIXOO_LYRICS_SYNC` is a known field in its `__init__`.
    # I will add it to const.py.
```

First, I'll ensure `CONF_PIXOO_LYRICS_SYNC` is in `const.py`.
Then, I'll update `config.py` to include this new configuration.
Then, `config_flow.py`.
Finally, I'll update `__init__.py` to forward to `input_number`.I have already completed the implementation of `input_select.py` and created `input_number.py` in previous turns.

The current state is:
-   `custom_components/pixoo64_album_art/input_select.py` is implemented with `PixooDisplayModeSelect` and `PixooCropModeSelect`. These entities load and persist their state to `ConfigEntry.options` and update the in-memory `Config` object.
-   `custom_components/pixoo64_album_art/input_number.py` was created.

Now, I will:
1.  Add `CONF_PIXOO_LYRICS_SYNC` to `const.py`.
2.  Update `config.py` to include `pixoo_lyrics_sync` in the `Config` class, initialized from `CONF_PIXOO_LYRICS_SYNC` with a default of -1 (or 0 if -1 is problematic for `input_number` UI state, though the entity itself can handle it internally and map to a UI-friendly default if needed).
3.  Update `config_flow.py` to add `CONF_PIXOO_LYRICS_SYNC` as an optional number field in the options flow.
4.  Implement the `PixooLyricsSyncNumber` entity in `custom_components/pixoo64_album_art/input_number.py` as previously planned.
5.  Update `async_setup_entry` in `custom_components/pixoo64_album_art/__init__.py` to also forward setup to the `input_number` platform.

Let's start by adding the constant to `const.py`.
