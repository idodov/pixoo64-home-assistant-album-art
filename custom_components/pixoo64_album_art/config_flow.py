import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
# from homeassistant.helpers.aiohttp_client import async_get_clientsession # Unused
from homeassistant.helpers import selector # Import selector
import logging # Added

from .const import (
    DOMAIN,
    CONF_MEDIA_PLAYER,
    CONF_PIXOO_IP,
    # CONF_HA_URL, # Removed
    # CONF_TOGGLE_ENTITY, # Removed
    # CONF_PIXOO_SENSOR_ENTITY, # Removed
    # CONF_LYRICS_SYNC_ENTITY, # Removed
    # CONF_MODE_SELECT_ENTITY, # Removed
    # CONF_CROP_SELECT_ENTITY, # Removed
    CONF_TEMPERATURE_SENSOR_ENTITY,
    CONF_LIGHT_ENTITY,
    CONF_AI_FALLBACK_MODEL,
    CONF_FORCE_AI,
    CONF_MUSICBRAINZ_ENABLED,
    CONF_SPOTIFY_CLIENT_ID,
    CONF_SPOTIFY_CLIENT_SECRET,
    CONF_SCRIPT_TOGGLE_ENABLED, # Added
    CONF_TIDAL_CLIENT_ID,
    CONF_TIDAL_CLIENT_SECRET,
    CONF_LASTFM_API_KEY,
    CONF_DISCOGS_API_TOKEN,
    AI_FALLBACK_MODEL_OPTIONS,
    # Pixoo device settings
    CONF_PIXOO_FULL_CONTROL,
    CONF_PIXOO_CONTRAST,
    CONF_PIXOO_SHARPNESS,
    CONF_PIXOO_COLORS_ENHANCED,
    CONF_PIXOO_KERNEL_EFFECT,
    CONF_PIXOO_SPECIAL_MODE,
    CONF_PIXOO_INFO_FALLBACK,
    CONF_PIXOO_SHOW_CLOCK,
    CONF_PIXOO_CLOCK_ALIGN,
    CONF_PIXOO_TEMPERATURE_ENABLED,
    CONF_PIXOO_TV_ICON_ENABLED,
    CONF_PIXOO_SPOTIFY_SLIDE,
    CONF_PIXOO_IMAGES_CACHE_SIZE,
    CONF_PIXOO_LIMIT_COLORS,
    CONF_PIXOO_SHOW_LYRICS,
    CONF_PIXOO_LYRICS_FONT,
    CONF_PIXOO_SHOW_TEXT_ENABLED,
    CONF_PIXOO_TEXT_CLEAN_TITLE,
    CONF_PIXOO_TEXT_BACKGROUND_ENABLED,
    CONF_PIXOO_TEXT_SPECIAL_MODE_SPOTIFY_SLIDER,
    CONF_PIXOO_TEXT_FORCE_FONT_COLOR,
    CONF_PIXOO_CROP_BORDERS_ENABLED,
    CONF_PIXOO_CROP_BORDERS_EXTRA,
    # WLED settings
    CONF_WLED_IP,
    CONF_WLED_BRIGHTNESS,
    CONF_WLED_EFFECT_ID,
    CONF_WLED_EFFECT_SPEED,
    CONF_WLED_EFFECT_INTENSITY,
    CONF_WLED_PALETTE_ID,
    CONF_WLED_SOUND_EFFECT_ID,
    CONF_WLED_ONLY_AT_NIGHT,
    # Options for select fields
    CLOCK_ALIGN_OPTIONS,
    LYRICS_FONT_OPTIONS,
    CONF_PIXOO_LYRICS_SYNC,
    PREDEFINED_FONT_COLORS, # Added PREDEFINED_FONT_COLORS
    CONF_PIXOO_TEXT_FORCE_FONT_COLOR_PRESET, # Added CONF_PIXOO_TEXT_FORCE_FONT_COLOR_PRESET
)

_LOGGER = logging.getLogger(__name__)
_LOGGER.debug("config_flow.py successfully loaded and parsed by Python interpreter.")


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pixoo64 Album Art Display."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate user_input here if necessary before creating entry
            return self.async_create_entry(title="Pixoo64 Album Art", data=user_input)

        data_schema = vol.Schema(
            {
                # vol.Required(CONF_HA_URL, default="http://homeassistant.local:8123"): str, # Removed
                vol.Required(CONF_MEDIA_PLAYER, default="media_player.living_room"): str,
                vol.Required(CONF_PIXOO_IP): str,
                # vol.Optional(CONF_TOGGLE_ENTITY): str, # Removed
                # vol.Optional(CONF_PIXOO_SENSOR_ENTITY, default="sensor.pixoo64_media_data"): str, # Removed
                # vol.Optional(CONF_LYRICS_SYNC_ENTITY): str, # Removed
                # vol.Optional(CONF_MODE_SELECT_ENTITY): str, # Removed
                # vol.Optional(CONF_CROP_SELECT_ENTITY): str, # Removed
                vol.Optional(CONF_TEMPERATURE_SENSOR_ENTITY): str,
                vol.Optional(CONF_LIGHT_ENTITY): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        multiple=True,
                        entity_ids=[selector.SelectSelectorEntityFilterConfig(domain="light")],
                    )
                ),
                vol.Optional(CONF_SPOTIFY_CLIENT_ID): str,
                vol.Optional(CONF_SPOTIFY_CLIENT_SECRET): str,
                vol.Optional(CONF_TIDAL_CLIENT_ID): str,
                vol.Optional(CONF_TIDAL_CLIENT_SECRET): str,
                vol.Optional(CONF_LASTFM_API_KEY): str,
                vol.Optional(CONF_DISCOGS_API_TOKEN): str,
                vol.Optional(CONF_WLED_IP): str, # Added WLED IP to initial setup as it's essential if used
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )


class Pixoo64AlbumArtOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow for Pixoo64 Album Art Display."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            updated_options = {**self.config_entry.options, **user_input}
            return self.async_create_entry(title="", data=updated_options)

        current_options = self.config_entry.options
        current_data = self.config_entry.data

        options_schema = vol.Schema(
            {
                # Required from initial setup, but editable in options
                # CONF_HA_URL was here, removed from options flow as well
                vol.Required(
                    CONF_MEDIA_PLAYER,
                    default=current_options.get(CONF_MEDIA_PLAYER, current_data.get(CONF_MEDIA_PLAYER, "media_player.living_room"))
                ): str,
                vol.Required(
                    CONF_PIXOO_IP,
                    default=current_options.get(CONF_PIXOO_IP, current_data.get(CONF_PIXOO_IP))
                ): str,

                # Optional string fields from initial setup
                # Fields for CONF_TOGGLE_ENTITY, CONF_PIXOO_SENSOR_ENTITY, CONF_LYRICS_SYNC_ENTITY,
                # CONF_MODE_SELECT_ENTITY, CONF_CROP_SELECT_ENTITY were removed here.
                vol.Optional(
                    CONF_TEMPERATURE_SENSOR_ENTITY,
                    default=current_options.get(CONF_TEMPERATURE_SENSOR_ENTITY, "") # Default to empty string
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="temperature"),
                ),
                vol.Optional(
                    CONF_LIGHT_ENTITY,
                    default=current_options.get(CONF_LIGHT_ENTITY, []) # Default to empty list
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        multiple=True,
                        entity_ids=[selector.SelectSelectorEntityFilterConfig(domain="light")],
                    )
                ),
                vol.Optional(
                    CONF_SPOTIFY_CLIENT_ID,
                    default=current_options.get(CONF_SPOTIFY_CLIENT_ID, current_data.get(CONF_SPOTIFY_CLIENT_ID, ""))
                ): str,
                vol.Optional(
                    CONF_SPOTIFY_CLIENT_SECRET,
                    default=current_options.get(CONF_SPOTIFY_CLIENT_SECRET, current_data.get(CONF_SPOTIFY_CLIENT_SECRET, ""))
                ): str,
                vol.Optional(
                    CONF_TIDAL_CLIENT_ID,
                    default=current_options.get(CONF_TIDAL_CLIENT_ID, current_data.get(CONF_TIDAL_CLIENT_ID, ""))
                ): str,
                vol.Optional(
                    CONF_TIDAL_CLIENT_SECRET,
                    default=current_options.get(CONF_TIDAL_CLIENT_SECRET, current_data.get(CONF_TIDAL_CLIENT_SECRET, ""))
                ): str,
                vol.Optional(
                    CONF_LASTFM_API_KEY,
                    default=current_options.get(CONF_LASTFM_API_KEY, current_data.get(CONF_LASTFM_API_KEY, ""))
                ): str,
                vol.Optional(
                    CONF_DISCOGS_API_TOKEN,
                    default=current_options.get(CONF_DISCOGS_API_TOKEN, current_data.get(CONF_DISCOGS_API_TOKEN, ""))
                ): str,

                # Boolean and Select fields from previous step
                vol.Optional(
                    CONF_FORCE_AI,
                    default=current_options.get(CONF_FORCE_AI, False)
                ): bool,
                vol.Optional(
                    CONF_MUSICBRAINZ_ENABLED,
                    default=current_options.get(CONF_MUSICBRAINZ_ENABLED, True)
                ): bool,
                vol.Optional(
                    CONF_AI_FALLBACK_MODEL,
                    default=current_options.get(CONF_AI_FALLBACK_MODEL, "turbo")
                ): vol.In(AI_FALLBACK_MODEL_OPTIONS),
                vol.Optional(
                    CONF_PIXOO_LYRICS_SYNC,
                    default=current_options.get(CONF_PIXOO_LYRICS_SYNC, -1), # Ensure default is -1
                ): int, # Ensure it's treated as an integer directly
                vol.Optional(
                    CONF_SCRIPT_TOGGLE_ENABLED,
                    default=current_options.get(CONF_SCRIPT_TOGGLE_ENABLED, True)
                ): bool,

                # Pixoo Device Settings
                vol.Optional(CONF_PIXOO_FULL_CONTROL, default=current_options.get(CONF_PIXOO_FULL_CONTROL, True)): bool,
                vol.Optional(CONF_PIXOO_CONTRAST, default=current_options.get(CONF_PIXOO_CONTRAST, False)): bool,
                vol.Optional(CONF_PIXOO_SHARPNESS, default=current_options.get(CONF_PIXOO_SHARPNESS, False)): bool,
                vol.Optional(CONF_PIXOO_COLORS_ENHANCED, default=current_options.get(CONF_PIXOO_COLORS_ENHANCED, False)): bool,
                vol.Optional(CONF_PIXOO_KERNEL_EFFECT, default=current_options.get(CONF_PIXOO_KERNEL_EFFECT, False)): bool,
                vol.Optional(CONF_PIXOO_SPECIAL_MODE, default=current_options.get(CONF_PIXOO_SPECIAL_MODE, False)): bool,
                vol.Optional(CONF_PIXOO_INFO_FALLBACK, default=current_options.get(CONF_PIXOO_INFO_FALLBACK, False)): bool,
                vol.Optional(CONF_PIXOO_SHOW_CLOCK, default=current_options.get(CONF_PIXOO_SHOW_CLOCK, False)): bool,
                vol.Optional(
                    CONF_PIXOO_CLOCK_ALIGN, 
                    default=current_options.get(CONF_PIXOO_CLOCK_ALIGN, "Right")
                ): vol.In(CLOCK_ALIGN_OPTIONS),
                vol.Optional(CONF_PIXOO_TEMPERATURE_ENABLED, default=current_options.get(CONF_PIXOO_TEMPERATURE_ENABLED, False)): bool,
                vol.Optional(CONF_PIXOO_TV_ICON_ENABLED, default=current_options.get(CONF_PIXOO_TV_ICON_ENABLED, True)): bool,
                vol.Optional(CONF_PIXOO_SPOTIFY_SLIDE, default=current_options.get(CONF_PIXOO_SPOTIFY_SLIDE, False)): bool,
                vol.Optional(CONF_PIXOO_IMAGES_CACHE_SIZE, default=current_options.get(CONF_PIXOO_IMAGES_CACHE_SIZE, 25)): int,
                vol.Optional(
                    CONF_PIXOO_LIMIT_COLORS,
                    default=current_options.get(CONF_PIXOO_LIMIT_COLORS, 0) # Default to 0 (meaning no limit)
                ): int,
                vol.Optional(CONF_PIXOO_SHOW_LYRICS, default=current_options.get(CONF_PIXOO_SHOW_LYRICS, False)): bool,
                vol.Optional(
                    CONF_PIXOO_LYRICS_FONT, 
                    default=current_options.get(CONF_PIXOO_LYRICS_FONT, 190)
                ): vol.In(LYRICS_FONT_OPTIONS), # Ensure LYRICS_FONT_OPTIONS contains integers
                vol.Optional(CONF_PIXOO_SHOW_TEXT_ENABLED, default=current_options.get(CONF_PIXOO_SHOW_TEXT_ENABLED, False)): bool,
                vol.Optional(CONF_PIXOO_TEXT_CLEAN_TITLE, default=current_options.get(CONF_PIXOO_TEXT_CLEAN_TITLE, True)): bool,
                vol.Optional(CONF_PIXOO_TEXT_BACKGROUND_ENABLED, default=current_options.get(CONF_PIXOO_TEXT_BACKGROUND_ENABLED, True)): bool,
                vol.Optional(CONF_PIXOO_TEXT_SPECIAL_MODE_SPOTIFY_SLIDER, default=current_options.get(CONF_PIXOO_TEXT_SPECIAL_MODE_SPOTIFY_SLIDER, False)): bool,
                vol.Optional(
                    CONF_PIXOO_TEXT_FORCE_FONT_COLOR_PRESET,
                    default=current_options.get(CONF_PIXOO_TEXT_FORCE_FONT_COLOR_PRESET, "Automatic") # Changed default to "Automatic"
                ): vol.In(list(PREDEFINED_FONT_COLORS.keys())),
                vol.Optional(
                    CONF_PIXOO_TEXT_FORCE_FONT_COLOR, 
                    default=current_options.get(CONF_PIXOO_TEXT_FORCE_FONT_COLOR, "")
                ): str,
                vol.Optional(CONF_PIXOO_CROP_BORDERS_ENABLED, default=current_options.get(CONF_PIXOO_CROP_BORDERS_ENABLED, False)): bool,
                vol.Optional(CONF_PIXOO_CROP_BORDERS_EXTRA, default=current_options.get(CONF_PIXOO_CROP_BORDERS_EXTRA, False)): bool,

                # WLED Settings
                vol.Optional(
                    CONF_WLED_IP, 
                    default=current_options.get(CONF_WLED_IP, current_data.get(CONF_WLED_IP, "")) # Get from options or initial data
                ): str,
                vol.Optional(CONF_WLED_BRIGHTNESS, default=current_options.get(CONF_WLED_BRIGHTNESS, 255)): int,
                vol.Optional(CONF_WLED_EFFECT_ID, default=current_options.get(CONF_WLED_EFFECT_ID, 38)): int,
                vol.Optional(CONF_WLED_EFFECT_SPEED, default=current_options.get(CONF_WLED_EFFECT_SPEED, 60)): int,
                vol.Optional(CONF_WLED_EFFECT_INTENSITY, default=current_options.get(CONF_WLED_EFFECT_INTENSITY, 128)): int,
                vol.Optional(CONF_WLED_PALETTE_ID, default=current_options.get(CONF_WLED_PALETTE_ID, 0)): int,
                vol.Optional(CONF_WLED_SOUND_EFFECT_ID, default=current_options.get(CONF_WLED_SOUND_EFFECT_ID, 0)): int,
                vol.Optional(CONF_WLED_ONLY_AT_NIGHT, default=current_options.get(CONF_WLED_ONLY_AT_NIGHT, False)): bool,
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)


@callback
def async_get_options_flow(config_entry):
    """Return the options flow handler."""
    return Pixoo64AlbumArtOptionsFlowHandler(config_entry)
