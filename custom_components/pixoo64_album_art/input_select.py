"""InputSelect entities for Pixoo64 Album Art Display."""
import logging
from typing import Any, Dict, Optional, List

from homeassistant.components.input_select import InputSelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN, 
    CONF_DISPLAY_MODE_SETTING, 
    DISPLAY_MODE_OPTIONS,      
    SPOTIFY_SLIDER_OPTIONS,
    CONF_CROP_MODE_SETTING,  # Fixed constant name
    CROP_MODE_OPTIONS             # Added from previous subtask's const.py work
)
from .config import Config
from .pixoo import PixooDevice
from .image import ImageProcessor 

_LOGGER = logging.getLogger(__name__)

# CROP_MODES local definition is removed as it's now imported via CROP_MODE_OPTIONS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the input_select platform."""
    _LOGGER.debug(f"Setting up input_selects for Pixoo64 Album Art entry: {entry.entry_id}")
    
    entry_data = hass.data[DOMAIN].get(entry.entry_id)
    if not entry_data:
        _LOGGER.error(f"Failed to set up input_selects: entry data not found for {entry.entry_id}.")
        return

    config: Config = entry_data["config"]
    pixoo_device: PixooDevice = entry_data["pixoo_device"]
    image_processor: ImageProcessor = entry_data["image_processor"] # Get ImageProcessor

    display_mode_select = PixooDisplayModeSelect(hass, entry, config, pixoo_device, image_processor) # Pass image_processor
    crop_mode_select = PixooCropModeSelect(hass, entry, config, pixoo_device, image_processor) # Pass image_processor
    
    async_add_entities([display_mode_select, crop_mode_select], True)
    _LOGGER.info(f"Pixoo64 input_selects for entry {entry.entry_id} added.")

class PixooDisplayModeSelect(InputSelectEntity):
    """Representation of a Pixoo64 Display Mode select entity."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, config: Config, pixoo_device: PixooDevice, image_processor: ImageProcessor): # Added image_processor
        """Initialize the display mode select."""
        self.hass = hass
        self._entry = entry
        self._config = config 
        self._pixoo_device = pixoo_device 
        self._image_processor = image_processor # Store ImageProcessor

        self._attr_name = f"Pixoo64 Display Mode - {entry.title}"
        self._attr_unique_id = f"{entry.entry_id}_display_mode"
        self._attr_icon = "mdi:form-select"
        
        current_options = list(DISPLAY_MODE_OPTIONS) # Use imported constant
        if self._config.spotify_client_id and self._config.spotify_client_secret:
            current_options.extend(SPOTIFY_SLIDER_OPTIONS) # Use imported constant
        self._attr_options = current_options
        
        # Current option is now sourced from the Config object, which loads it from entry.options
        self._attr_current_option = self._config.display_mode_setting


    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title or "Pixoo64 Album Art",
            manufacturer="Divoom Custom Integration",
            model="Pixoo64 Integration",
        )

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        _LOGGER.debug(f"Display mode selected: {option} for {self.unique_id}")
        self._attr_current_option = option
        
        # Persist the selected mode string to ConfigEntry.options
        new_options = {**self._entry.options, CONF_DISPLAY_MODE_SETTING: option}
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        
        # Update the live Config object by applying the new mode settings
        self._config.display_mode_setting = option # Update the attribute in Config
        self._config._apply_display_mode_settings(option) # Call the method in Config
        
        # Clear image cache as display mode change might affect image rendering (e.g. burned text)
        self._image_processor.clear_cache()
        _LOGGER.debug("Image cache cleared due to display mode change.")

        _LOGGER.info(f"Display mode for {self.unique_id} set to {option}. Config updated. Triggering force update.")
        self.async_write_ha_state() 

        # Force a refresh of the display
        force_update_function = self.hass.data[DOMAIN][self._entry.entry_id].get('force_update_function')
        if force_update_function:
            await force_update_function(self.hass, self._entry)
        else:
            _LOGGER.warning("force_update_function not found in hass.data. Cannot force Pixoo update for display mode change.")

class PixooCropModeSelect(InputSelectEntity):
    """Representation of a Pixoo64 Crop Mode select entity."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, config: Config, pixoo_device: PixooDevice, image_processor: ImageProcessor): # Added image_processor
        """Initialize the crop mode select."""
        self.hass = hass
        self._entry = entry
        self._config = config
        self._pixoo_device = pixoo_device
        self._image_processor = image_processor # Store ImageProcessor

        self._attr_name = f"Pixoo64 Crop Mode - {entry.title}"
        self._attr_unique_id = f"{entry.entry_id}_crop_mode"
        self._attr_icon = "mdi:crop"
        self._attr_options = CROP_MODE_OPTIONS # Use imported constant
        
        # Current option is now sourced from the Config object
        self._attr_current_option = self._config.crop_mode_setting

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title or "Pixoo64 Album Art",
            manufacturer="Divoom Custom Integration",
            model="Pixoo64 Integration",
        )

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        _LOGGER.debug(f"Crop mode selected: {option} for {self.unique_id}")
        self._attr_current_option = option
        
        # Persist the selected mode string to ConfigEntry.options
        new_options = {**self._entry.options, CONF_CROP_MODE_SETTING: option}
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)

        # Update the live Config object by applying the new mode settings
        self._config.crop_mode_setting = option # Update the attribute in Config
        self._config._apply_crop_mode_settings(option) # Call the method in Config
        
        # Clear image cache as crop mode change will affect image processing
        self._image_processor.clear_cache()
        _LOGGER.debug("Image cache cleared due to crop mode change.")

        _LOGGER.info(f"Crop mode for {self.unique_id} set to {option}. Config updated. Triggering force update.")
        self.async_write_ha_state()

        # Force a refresh of the display
        force_update_function = self.hass.data[DOMAIN][self._entry.entry_id].get('force_update_function')
        if force_update_function:
            await force_update_function(self.hass, self._entry)
        else:
            _LOGGER.warning("force_update_function not found in hass.data. Cannot force Pixoo update for crop mode change.")
