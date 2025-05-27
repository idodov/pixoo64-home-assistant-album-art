"""The Pixoo64 Album Art Display integration."""
import logging
import asyncio # For asyncio.Lock
import base64 # For black screen image data
import io # For black screen image data
from typing import Tuple, Optional, List, Dict, Any # Added Dict, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, Event 
from homeassistant.helpers.event import async_track_state_change_event, async_call_later
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.components.light import (
    ATTR_RGB_COLOR, 
    ATTR_BRIGHTNESS_PCT,
)

from .config import Config
from .const import DOMAIN
from .pixoo import PixooDevice
from .image import ImageProcessor
from .media import MediaData
from .fallback_service import FallbackService
from .lyrics_provider import LyricsProvider
from .sensor import Pixoo64AlbumArtStatusSensor # For type hinting sensor

_LOGGER = logging.getLogger(__name__)

# --- Light Control Helper Functions ---
async def async_control_ha_light(
    hass: HomeAssistant, 
    light_entity_ids: Optional[List[str]],
    turn_on: bool, 
    rgb_color: Optional[Tuple[int, int, int]] = None, 
    brightness_pct: Optional[int] = None 
):
    """Control one or more Home Assistant light entities."""
    if not light_entity_ids:
        _LOGGER.debug("No light entity IDs provided to async_control_ha_light.")
        return

    actual_entity_ids: List[str]
    if isinstance(light_entity_ids, str):
        actual_entity_ids = [light_entity_ids] if light_entity_ids else []
    elif isinstance(light_entity_ids, list):
        actual_entity_ids = light_entity_ids
    else:
        _LOGGER.warning(f"Invalid type for light_entity_ids: {type(light_entity_ids)}. Expected str or list.")
        return
    
    if not actual_entity_ids:
        _LOGGER.debug("Empty list of light entity IDs after processing.")
        return

    service_to_call = "turn_on" if turn_on else "turn_off"
    
    for entity_id in actual_entity_ids:
        if not entity_id or not isinstance(entity_id, str):
            _LOGGER.warning(f"Invalid light entity ID in list: {entity_id}")
            continue

        service_data = {"entity_id": entity_id}
        if turn_on:
            if rgb_color:
                service_data[ATTR_RGB_COLOR] = rgb_color
            if brightness_pct is not None:
                service_data[ATTR_BRIGHTNESS_PCT] = brightness_pct
        
        _LOGGER.debug(f"Calling light.{service_to_call} for {entity_id} with data: {service_data}")
        try:
            await hass.services.async_call(
                "light", service_to_call, service_data, blocking=False
            )
        except Exception as e:
            _LOGGER.error(f"Error calling light service for {entity_id}: {e}")

async def async_control_wled_light(
    hass: HomeAssistant,
    config: Config, 
    turn_on: bool,
    color1: Optional[Tuple[int, int, int]] = None,
    brightness_override: Optional[int] = None,
    effect_id_override: Optional[int] = None,
    palette_id_override: Optional[int] = None,
    speed_override: Optional[int] = None,
    intensity_override: Optional[int] = None,
):
    """Control one or more WLED devices via their JSON API."""
    if not config.wled_ips:
        _LOGGER.debug("No WLED IP addresses configured.")
        return

    session = async_get_clientsession(hass)

    for ip_address in config.wled_ips:
        if not ip_address: 
            continue

        url = f"http://{ip_address}/json/state"
        payload: Dict[str, Any] = {"on": turn_on}

        if turn_on:
            payload["bri"] = brightness_override if brightness_override is not None else config.wled_brightness
            
            segment = {"id": 0}
            if color1: 
                segment["col"] = [list(color1)]
                segment["fx"] = effect_id_override if effect_id_override is not None else 0 
                segment["pal"] = palette_id_override if palette_id_override is not None else 0 
            else: 
                segment["fx"] = effect_id_override if effect_id_override is not None else config.wled_effect_id
                segment["pal"] = palette_id_override if palette_id_override is not None else config.wled_palette_id
            
            segment["sx"] = speed_override if speed_override is not None else config.wled_effect_speed
            segment["ix"] = intensity_override if intensity_override is not None else config.wled_effect_intensity
            
            if len(segment) > 1 or color1: 
                payload["seg"] = [segment]
            
        _LOGGER.debug(f"Controlling WLED light at {ip_address}: payload={payload}")
        try:
            async with session.post(url, json=payload, timeout=5) as response:
                response.raise_for_status()
                _LOGGER.debug(f"WLED response from {ip_address}: {await response.json()}")
        except Exception as e:
            _LOGGER.error(f"Error controlling WLED light at {ip_address}: {e}")


async def _async_execute_display_update(
    hass: HomeAssistant, 
    entry: ConfigEntry, 
    entry_data: dict
) -> None:
    """
    Core logic to update Pixoo display based on current media state and config.
    Assumes display_update_lock is already acquired.
    """
    config: Config = entry_data["config"]
    media_data_obj: MediaData = entry_data["media_data"]
    image_processor: ImageProcessor = entry_data["image_processor"]
    fallback_service: FallbackService = entry_data["fallback_service"]
    lyrics_provider: LyricsProvider = entry_data["lyrics_provider"]
    pixoo_device: PixooDevice = entry_data["pixoo_device"]
    status_sensor: Optional[Pixoo64AlbumArtStatusSensor] = entry_data.get("status_sensor")

    _LOGGER.info(f"Executing display update for media player: {config.media_player_entity_id} (or forced update)")

    await media_data_obj.update()

    # Handle case where player is off/idle even after forced update/mode change
    # This ensures black screen/clock if player is not actually active
    if not media_data_obj.is_playing and media_data_obj.media_player_state not in ["on", "paused"]:
        _LOGGER.info(f"Media player not actively playing (state: {media_data_obj.media_player_state}). Displaying black screen/clock.")
        if config.pixoo_full_control:
            black_screen_img_pil = fallback_service.create_black_screen_image()
            await fallback_service.send_info_img(black_screen_img_pil)
            
            item_list_for_off_state = []
            text_id_counter_off = 200 
            if config.pixoo_show_clock:
                text_id_counter_off +=1
                clock_item = {
                    "TextId": str(text_id_counter_off), "type": 3,
                    "x": 34 if config.pixoo_clock_align == "Right" else 2, "y": 57,
                    "font": 2, "color": config.pixoo_text_actual_force_font_color or "#FFFFFF"
                }
                item_list_for_off_state.append(clock_item)
            if config.pixoo_temperature_enabled:
                text_id_counter_off +=1
                temp_payload_part = {
                    "TextId": str(text_id_counter_off), "x": 2, "y": 57, "font": 2,
                    "color": config.pixoo_text_actual_force_font_color or "#FFFFFF"
                }
                if config.pixoo_clock_align == "Left" and config.pixoo_show_clock: temp_payload_part["x"] = 34
                if media_data_obj.temperature:
                    temp_payload_part.update({"type": 22, "TextString": media_data_obj.temperature})
                else:
                    temp_payload_part["type"] = 17
                item_list_for_off_state.append(temp_payload_part)
            if item_list_for_off_state:
                 await pixoo_device.send_command({"Command": "Draw/SendHttpItemList", "ItemList": item_list_for_off_state})
            elif not item_list_for_off_state and config.pixoo_full_control : 
                 await pixoo_device.send_command({"Command": "Draw/SendHttpItemList", "ItemList": []})
        else:
            _LOGGER.info("pixoo_full_control is false, not clearing display (during execute_display_update for off state).")
        
        await async_control_ha_light(hass, config.light_entity, turn_on=False)
        await async_control_wled_light(hass, config, turn_on=False)
        
        if status_sensor:
            status_sensor.schedule_update()
        return

    # Process active media display (TV icon, album art, fallbacks)
    if media_data_obj.current_mode == "TV" and config.pixoo_tv_icon_enabled and not media_data_obj.cover_url :
        _LOGGER.info("TV mode is active, no specific art. Displaying TV icon.")
        tv_icon_pil_image = fallback_service.create_tv_icon_image()
        await fallback_service.send_info_img(tv_icon_pil_image)
        await async_control_ha_light(hass, config.light_entity, turn_on=False) 
        await async_control_wled_light(hass, config, turn_on=False)
        if status_sensor: status_sensor.schedule_update()
        return

    image_source_url_or_action = await fallback_service.get_final_url(media_data_obj)

    processed_image_info: Optional[dict] = None
    base64_image_data: Optional[str] = None
    ha_light_rgb_color: Optional[Tuple[int,int,int]] = None
    wled_color1: Optional[Tuple[int,int,int]] = None
    image_brightness_for_light: Optional[int] = None

    if image_source_url_or_action in ["fallback_tv_icon_sent", "fallback_info_text_sent", "fallback_black_screen_sent"]:
        _LOGGER.info(f"FallbackService handled display directly: {image_source_url_or_action}")
        if image_source_url_or_action == "fallback_black_screen_sent":
            await async_control_ha_light(hass, config.light_entity, turn_on=False)
            await async_control_wled_light(hass, config, turn_on=False)
    elif image_source_url_or_action:
        _LOGGER.info(f"Processing image from URL: {image_source_url_or_action}")
        processed_image_info = await image_processor.get_image(media_data_obj, image_source_url_or_action)
        if processed_image_info:
            base64_image_data = processed_image_info.get("base64_gif")
            ha_light_rgb_color = processed_image_info.get("background_color_rgb")
            wled_color1 = processed_image_info.get("color1")
            raw_brightness = processed_image_info.get("brightness")
            if raw_brightness is not None:
                 image_brightness_for_light = int((raw_brightness / 255) * 100)
                 image_brightness_for_light = max(10, min(100, image_brightness_for_light))
        else:
             _LOGGER.warning(f"Image processing failed for URL: {image_source_url_or_action}")

    if not base64_image_data and image_source_url_or_action not in ["fallback_tv_icon_sent", "fallback_info_text_sent", "fallback_black_screen_sent"]:
        _LOGGER.warning("Failed to get final image data. Sending black screen as fallback.")
        black_screen_pil = fallback_service.create_black_screen_image()
        buffered = io.BytesIO()
        black_screen_pil.save(buffered, format="GIF") 
        base64_image_data = base64.b64encode(buffered.getvalue()).decode("utf-8")
        await async_control_ha_light(hass, config.light_entity, turn_on=False)
        await async_control_wled_light(hass, config, turn_on=False)

    should_turn_lights_on = bool(base64_image_data and image_source_url_or_action not in ["fallback_black_screen_sent"])
    
    await async_control_ha_light(
        hass, config.light_entity, turn_on=should_turn_lights_on, 
        rgb_color=ha_light_rgb_color, 
        brightness_pct=image_brightness_for_light if ha_light_rgb_color and should_turn_lights_on else 80 
    ) 
    await async_control_wled_light(
        hass, config, turn_on=should_turn_lights_on, 
        color1=wled_color1, 
        brightness_override=int((image_brightness_for_light / 100) * 255) if image_brightness_for_light is not None and should_turn_lights_on else None
    )

    if base64_image_data:
        _LOGGER.info("Sending image data to Pixoo device.")
        await pixoo_device.display_gif(base64_image_data)

    if config.pixoo_spotify_slide and media_data_obj.is_spotify: 
        _LOGGER.warning("Spotify slide show feature triggered but not fully implemented in event handler.")

    show_item_list = False
    if config.display_mode_setting in ["Clock", "Clock | Temperature", "Clock | Temperature | Text", "Temperature", "Temperature | Text", "Special Mode", "Special Mode | Text"] or \
       (config.pixoo_special_mode and (config.pixoo_show_clock or config.pixoo_temperature_enabled)) or \
       (not base64_image_data and (config.pixoo_show_clock or config.pixoo_temperature_enabled)):
        show_item_list = True
    
    if config.display_mode_setting in ["Album Art Only", "Lyrics Only", "Clean", "Burned"]:
        show_item_list = False

    if show_item_list:
        item_list_for_pixoo = []
        text_id_counter = 100 
        if config.pixoo_show_clock or "clock" in config.display_mode_setting.lower(): # Check display_mode_setting too
            text_id_counter += 1
            clock_item = {
                "TextId": str(text_id_counter), "type": 3,
                "x": 34 if config.pixoo_clock_align == "Right" else 2, "y": 57,
                "font": 2, "color": config.pixoo_text_actual_force_font_color or "#FFFFFF"
            }
            item_list_for_pixoo.append(clock_item)
        if config.pixoo_temperature_enabled or "temperature" in config.display_mode_setting.lower(): # Check display_mode_setting too
            text_id_counter += 1
            temperature_item_payload = {
                "TextId": str(text_id_counter), "x": 2, "y": 57, "font": 2, 
                "color": config.pixoo_text_actual_force_font_color or "#FFFFFF"
            }
            if config.pixoo_clock_align == "Left" and (config.pixoo_show_clock or "clock" in config.display_mode_setting.lower()):
                 temperature_item_payload["x"] = 34
            if media_data_obj.temperature:
                temperature_item_payload["type"] = 22
                temperature_item_payload["TextString"] = media_data_obj.temperature
            else:
                temperature_item_payload["type"] = 17
            item_list_for_pixoo.append(temperature_item_payload)
        
        if item_list_for_pixoo:
            list_payload = {"Command": "Draw/SendHttpItemList", "ItemList": item_list_for_pixoo}
            _LOGGER.debug(f"Sending ItemList to Pixoo: {list_payload}")
            await pixoo_device.send_command(list_payload)
        elif base64_image_data and not item_list_for_pixoo: 
             _LOGGER.debug("Clearing previous ItemList by sending empty list.")
             await pixoo_device.send_command({"Command": "Draw/SendHttpItemList", "ItemList": []})
    
    if config.pixoo_show_lyrics and media_data_obj.lyrics and media_data_obj.is_playing:
        if config.display_mode_setting not in ["Clock", "Temperature", "Album Art Only", "Clean"]: 
            current_media_player_state = hass.states.get(config.media_player_entity_id)
            if current_media_player_state and current_media_player_state.attributes.get("media_position") is not None:
                current_pos_sec = current_media_player_state.attributes.get("media_position", 0)
                await lyrics_provider.calculate_position(media_data_obj, int(current_pos_sec * 1000))
            elif media_data_obj.lyrics:
                 await lyrics_provider.calculate_position(media_data_obj, 0) 

    if status_sensor:
        status_sensor.schedule_update()
    _LOGGER.debug(f"Finished display update for {config.media_player_entity_id}.")


async def async_force_pixoo_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Force a complete refresh of the Pixoo display based on current media state and config."""
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not entry_data:
        _LOGGER.error("Pixoo64 data not found for entry %s during force update", entry.entry_id)
        return

    _LOGGER.info(f"Force updating Pixoo display for entry {entry.title} due to option change or service call.")
    
    async with entry_data["display_update_lock"]:
        await _async_execute_display_update(hass, entry, entry_data)


async def _async_handle_media_player_update(
    hass: HomeAssistant, 
    entry: ConfigEntry, 
    event: Event, 
    entry_data: dict 
) -> None:
    """Handle media player state changes and orchestrate display updates."""
    
    new_state = event.data.get("new_state")
    if not new_state:
        _LOGGER.debug(f"Media player ({event.data.get('entity_id')}) state update with no new_state.")
        return

    _LOGGER.debug(f"Handling state update for {new_state.entity_id}: state='{new_state.state}', old_state='{event.data.get('old_state', {}).get('state', 'unknown')}'")

    config: Config = entry_data["config"]
    media_data_obj: MediaData = entry_data["media_data"] # For updating its internal state
    status_sensor: Optional[Pixoo64AlbumArtStatusSensor] = entry_data.get("status_sensor") # For scheduling updates
    fallback_service: FallbackService = entry_data["fallback_service"] # For creating black screen image

    # Cancel any pending "off_state_delay_timer"
    if entry_data.get("off_state_delay_timer"):
        entry_data["off_state_delay_timer"].cancel()
        entry_data["off_state_delay_timer"] = None
        _LOGGER.debug("Cancelled previous off_state_delay_timer.")

    # --- Handle Media Player Off/Idle/Paused States ---
    if new_state.state in ["off", "idle", "paused", "standby"]:
        _LOGGER.info(f"Media player is {new_state.state}. Processing off/idle/paused state.")

        async def _delayed_off_processing_task():
            _LOGGER.info(f"Executing delayed off processing for {config.media_player_entity_id}")
            # Update MediaData object first for off/paused state
            await media_data_obj.update() # This will set is_playing to False, etc.
            
            # Now call the execute_display_update which will handle showing black screen/clock
            await _async_execute_display_update(hass, entry, entry_data)
            
            # Ensure lights are off (might be redundant if _async_execute_display_update handles it, but safe)
            await async_control_ha_light(hass, config.light_entity, turn_on=False)
            await async_control_wled_light(hass, config, turn_on=False)

            # The sensor update is now handled within _async_execute_display_update
            _LOGGER.info(f"Pixoo display and lights handled for '{new_state.state}' state.")

        delay_seconds = 0 
        if new_state.state == "paused": 
            delay_seconds = 5 
        
        if delay_seconds > 0:
            _LOGGER.debug(f"Delaying '{new_state.state}' processing by {delay_seconds} seconds.")
            entry_data["off_state_delay_timer"] = async_call_later(hass, delay_seconds, lambda _: hass.async_create_task(_delayed_off_processing_task()))
        else: 
            await _delayed_off_processing_task() 
        
        entry_data["last_media_player_state"] = new_state.state
        return

    # --- Process Active Media Player (Playing or On) ---
    # This part is now largely handled by _async_execute_display_update
    image_processor: ImageProcessor = entry_data["image_processor"] # For cache clearing
    if entry_data.get("last_media_player_state") in ["off", "idle", "paused", "standby"] and new_state.state == "playing":
        _LOGGER.info(f"Media player started playing (was {entry_data.get('last_media_player_state')}). Clearing image cache.")
        image_processor.clear_cache() 

    entry_data["last_media_player_state"] = new_state.state
    
    # Call the core display update logic
    await _async_execute_display_update(hass, entry, entry_data)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pixoo64 Album Art Display from a config entry."""
    _LOGGER.debug(f"Setting up Pixoo64 Album Art Display for entry {entry.entry_id}")

    config = Config(entry)
    pixoo_device = PixooDevice(hass, config)
    image_processor = ImageProcessor(hass, config)
    media_data = MediaData(hass, config, image_processor) 
    fallback_service = FallbackService(config, hass, image_processor, pixoo_device)
    lyrics_provider = LyricsProvider(config, hass, image_processor, pixoo_device)

    # Initial device communication / validation
    try:
        _LOGGER.debug(f"Attempting to connect to Pixoo64 device at {config.pixoo_ip} for initial check.")
        channel_index = await pixoo_device.get_current_channel_index()
        if channel_index is not None:
            _LOGGER.info(f"Successfully connected to Pixoo64 device at {config.pixoo_ip}. Current channel index: {channel_index}")
        else:
            _LOGGER.warning(f"Connected to Pixoo64 device at {config.pixoo_ip}, but failed to get channel index. Continuing setup.")
    except Exception as e:
        _LOGGER.error(f"Failed to connect to Pixoo64 device at {config.pixoo_ip} during setup: {e}")
        raise ConfigEntryNotReady(f"Could not connect to Pixoo device: {e}") from e

    hass.data.setdefault(DOMAIN, {})
    entry_data_payload = {
        "config": config,
        "pixoo_device": pixoo_device,
        "image_processor": image_processor,
        "media_data": media_data,
        "fallback_service": fallback_service,
        "lyrics_provider": lyrics_provider,
        "media_player_listener": None, 
        "status_sensor": None, 
        "display_update_lock": asyncio.Lock(), 
        "last_media_player_state": None, 
        "off_state_delay_timer": None, 
        "force_update_function": async_force_pixoo_update # Store the refresh function
    }
    hass.data[DOMAIN][entry.entry_id] = entry_data_payload

    if config.media_player_entity_id:
        async def wrapped_event_handler(event: Event): 
            current_entry_data = hass.data[DOMAIN].get(entry.entry_id)
            if not current_entry_data:
                _LOGGER.warning(f"Event handler triggered for {entry.entry_id} but entry_data not found.")
                return
            
            async with current_entry_data["display_update_lock"]:
                await _async_handle_media_player_update(hass, entry, event, current_entry_data)

        entry_data_payload["media_player_listener"] = async_track_state_change_event(
            hass,
            [config.media_player_entity_id], 
            wrapped_event_handler 
        )
        _LOGGER.info(f"Registered listener for media player: {config.media_player_entity_id}")
        
        initial_state = hass.states.get(config.media_player_entity_id)
        if initial_state:
            _LOGGER.debug(f"Triggering initial update for {config.media_player_entity_id} with state: {initial_state.state}")
            mock_event_data = {
                "entity_id": config.media_player_entity_id,
                "old_state": None, 
                "new_state": initial_state,
            }
            hass.async_create_task(wrapped_event_handler(Event("state_changed", mock_event_data)))
        else:
            _LOGGER.warning(f"Media player {config.media_player_entity_id} not found for initial update.")
    else:
        _LOGGER.warning("No media_player_entity_id configured, cannot listen for media updates or perform initial update.")

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "input_select", "input_number"])

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    _LOGGER.info(f"Pixoo64 Album Art Display for entry {entry.entry_id} set up successfully.")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug(f"Unloading Pixoo64 Album Art Display for entry {entry.entry_id}")

    platforms_to_unload = ["sensor", "input_select", "input_number"] 
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, platforms_to_unload)
    
    entry_data = hass.data[DOMAIN].get(entry.entry_id)
    if entry_data:
        listener_canceller = entry_data.get("media_player_listener")
        if listener_canceller:
            listener_canceller()
            _LOGGER.debug("Cancelled media player state change listener.")

        off_timer_canceller = entry_data.get("off_state_delay_timer")
        if off_timer_canceller:
            off_timer_canceller.cancel()
            _LOGGER.debug("Cancelled off_state_delay_timer.")

        if "image_processor" in entry_data:
            image_processor: ImageProcessor = entry_data["image_processor"]
            await hass.async_add_executor_job(image_processor.shutdown)
        
        if "fallback_service" in entry_data:
            fallback_service: FallbackService = entry_data["fallback_service"]
            await fallback_service.shutdown()
        
        if "lyrics_provider" in entry_data:
            lyrics_provider: LyricsProvider = entry_data["lyrics_provider"]
            await lyrics_provider.shutdown()

    if unload_ok:
        if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.info(f"Pixoo64 Album Art Display for entry {entry.entry_id} unloaded successfully.")
    else:
        _LOGGER.error(f"Failed to unload platforms for Pixoo64 Album Art Display entry {entry.entry_id}.")

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug(f"Reloading Pixoo64 Album Art Display for entry {entry.entry_id} due to options update.")
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
