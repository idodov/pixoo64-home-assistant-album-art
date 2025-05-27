import logging
from typing import Any, Dict, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity # For persisting state

from .const import DOMAIN, CONF_SCRIPT_TOGGLE_ENABLED, CONF_PIXOO_FULL_CONTROL

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Pixoo64 Album Art switches from a config entry."""
    _LOGGER.debug(f"Setting up Pixoo64 Album Art switches for entry {entry.entry_id}")

    # Get the central data store for this config entry
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not entry_data:
        _LOGGER.error(
            f"Failed to set up Pixoo64 Album Art switches: entry data not found for {entry.entry_id}."
        )
        return

    config_instance = entry_data.get("config")
    if not config_instance:
        _LOGGER.error(
            f"Failed to set up Pixoo64 Album Art switches: config not found in entry_data for {entry.entry_id}."
        )
        return

    switches_to_add = []
    script_toggle_switch = None # Initialize to None

    # 1. Script Toggle Switch
    # Check if the user wants to create this switch
    if entry.options.get(CONF_SCRIPT_TOGGLE_ENABLED, True): # Default to True if option not set yet
        script_toggle_switch = PixooAlbumArtScriptToggleSwitch(hass, entry)
        switches_to_add.append(script_toggle_switch)
        _LOGGER.debug(f"Added PixooAlbumArtScriptToggleSwitch for entry {entry.entry_id}")
    else:
        _LOGGER.debug(f"Script toggle switch is disabled via config for entry {entry.entry_id}, not adding.")


    # 2. Full Control Switch
    full_control_switch = PixooAlbumArtFullControlSwitch(hass, entry, config_instance)
    switches_to_add.append(full_control_switch)
    _LOGGER.debug(f"Added PixooAlbumArtFullControlSwitch for entry {entry.entry_id}")

    if switches_to_add:
        async_add_entities(switches_to_add, True) # True for update_before_add
        # Store references in entry_data for easy access from __init__.py
        if script_toggle_switch and CONF_SCRIPT_TOGGLE_ENABLED in entry.options and entry.options.get(CONF_SCRIPT_TOGGLE_ENABLED, True): # check if script_toggle_switch was created
            entry_data["script_toggle_switch"] = script_toggle_switch
        entry_data["full_control_switch"] = full_control_switch
        _LOGGER.info(f"Pixoo64 Album Art switches for entry {entry.entry_id} added.")
    else:
        _LOGGER.info(f"No switches to add for entry {entry.entry_id}.")


class PixooAlbumArtScriptToggleSwitch(SwitchEntity, RestoreEntity):
    """Switch to toggle the Pixoo64 album art script execution."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the switch."""
        self.hass = hass
        self._entry = entry
        self._attr_name = f"{entry.title} Script Enabled"
        self._attr_unique_id = f"{entry.entry_id}_script_enabled"
        self._attr_icon = "mdi:play-pause"
        self._is_on = True  # Default to on

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state:
            self._is_on = last_state.state == "on"

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "Pixoo64 Album Art Integration",
        }

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        self._is_on = False
        self.async_write_ha_state()

    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return False


class PixooAlbumArtFullControlSwitch(SwitchEntity, RestoreEntity):
    """Switch to toggle the Pixoo64 'full_control' behavior."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, config_instance: Any):
        """Initialize the switch."""
        self.hass = hass
        self._entry = entry
        self._config_instance = config_instance 
        self._attr_name = f"{entry.title} Full Control"
        self._attr_unique_id = f"{entry.entry_id}_full_control"
        self._attr_icon = "mdi:cog-outline" # Using outline for consistency
        
        # Initial state from the configuration's original setting
        self._is_on = self._config_instance.original_pixoo_full_control
        # Update the operational config value based on this initial state
        self._config_instance.pixoo_full_control = self._is_on


    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state:
            self._is_on = last_state.state == "on"
        # Ensure the operational config value reflects the restored state
        self._config_instance.pixoo_full_control = self._is_on
        self.async_write_ha_state() # Update HA state if restored state differs from initial

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "Pixoo64 Album Art Integration",
        }

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self._is_on = True
        self._config_instance.pixoo_full_control = True
        self.async_write_ha_state()
        await self._trigger_config_update()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        self._is_on = False
        self._config_instance.pixoo_full_control = False
        self.async_write_ha_state()
        await self._trigger_config_update()
        
    async def _trigger_config_update(self) -> None:
        """Trigger a configuration update or refresh if necessary."""
        # This might involve calling the force update function stored in entry_data
        # or re-applying display mode settings if full_control affects them directly.
        entry_data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id)
        if entry_data and "force_update_function" in entry_data:
            _LOGGER.debug(f"Full Control switch toggled, calling force_update_function for entry {self._entry.title}")
            # Call the stored async_force_pixoo_update function
            await entry_data["force_update_function"](self.hass, self._entry)
        else:
            _LOGGER.warning(f"Could not find force_update_function for entry {self._entry.title} to react to Full Control toggle.")


    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return False
