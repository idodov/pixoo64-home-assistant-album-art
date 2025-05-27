from .const import (
    CONF_MEDIA_PLAYER, CONF_PIXOO_IP,
    CONF_TEMPERATURE_SENSOR_ENTITY, CONF_LIGHT_ENTITY,
    CONF_AI_FALLBACK_MODEL, CONF_FORCE_AI, CONF_MUSICBRAINZ_ENABLED,
    CONF_SPOTIFY_CLIENT_ID, CONF_SPOTIFY_CLIENT_SECRET, CONF_TIDAL_CLIENT_ID,
    CONF_TIDAL_CLIENT_SECRET, CONF_LASTFM_API_KEY, CONF_DISCOGS_API_TOKEN,
    CONF_PIXOO_FULL_CONTROL, CONF_PIXOO_CONTRAST, CONF_PIXOO_SHARPNESS,
    CONF_PIXOO_COLORS_ENHANCED, CONF_PIXOO_KERNEL_EFFECT, CONF_PIXOO_SPECIAL_MODE,
    CONF_PIXOO_INFO_FALLBACK, CONF_PIXOO_SHOW_CLOCK, CONF_PIXOO_CLOCK_ALIGN,
    CONF_PIXOO_TEMPERATURE_ENABLED, CONF_PIXOO_TV_ICON_ENABLED,
    CONF_PIXOO_SPOTIFY_SLIDE, CONF_PIXOO_IMAGES_CACHE_SIZE, CONF_PIXOO_LIMIT_COLORS,
    CONF_PIXOO_SHOW_LYRICS, CONF_PIXOO_LYRICS_FONT, CONF_PIXOO_SHOW_TEXT_ENABLED,
    CONF_PIXOO_TEXT_CLEAN_TITLE, CONF_PIXOO_TEXT_BACKGROUND_ENABLED,
    CONF_PIXOO_TEXT_SPECIAL_MODE_SPOTIFY_SLIDER, CONF_PIXOO_TEXT_FORCE_FONT_COLOR,
    CONF_PIXOO_CROP_BORDERS_ENABLED, CONF_PIXOO_CROP_BORDERS_EXTRA, CONF_WLED_IP,
    CONF_WLED_BRIGHTNESS, CONF_WLED_EFFECT_ID, CONF_WLED_EFFECT_SPEED,
    CONF_WLED_EFFECT_INTENSITY, CONF_WLED_PALETTE_ID, CONF_WLED_SOUND_EFFECT_ID,
    CONF_WLED_ONLY_AT_NIGHT, AI_FALLBACK_MODEL_OPTIONS, CLOCK_ALIGN_OPTIONS,
    LYRICS_FONT_OPTIONS, CONF_PIXOO_LYRICS_SYNC,
    PREDEFINED_FONT_COLORS, 
    CONF_PIXOO_TEXT_FORCE_FONT_COLOR_PRESET,
    CONF_DISPLAY_MODE_SETTING, 
    CONF_CROP_MODE_SETTING, 
)
import re 
import logging 
from typing import Optional 

_LOGGER = logging.getLogger(__name__)

class Config:
    def __init__(self, config_entry):
        options = config_entry.options
        data = config_entry.data 

        self.media_player_entity_id = options.get(CONF_MEDIA_PLAYER, data.get(CONF_MEDIA_PLAYER))
        self.pixoo_ip = options.get(CONF_PIXOO_IP, data.get(CONF_PIXOO_IP))
        
        self.temperature_sensor_entity = options.get(CONF_TEMPERATURE_SENSOR_ENTITY, None)
        
        raw_light_entities = options.get(CONF_LIGHT_ENTITY, []) 
        if isinstance(raw_light_entities, str):
            self.light_entity = [raw_light_entities] if raw_light_entities else []
        elif isinstance(raw_light_entities, list):
            self.light_entity = raw_light_entities
        else:
            self.light_entity = []

        self.spotify_client_id = options.get(CONF_SPOTIFY_CLIENT_ID, data.get(CONF_SPOTIFY_CLIENT_ID))
        self.spotify_client_secret = options.get(CONF_SPOTIFY_CLIENT_SECRET, data.get(CONF_SPOTIFY_CLIENT_SECRET))
        self.tidal_client_id = options.get(CONF_TIDAL_CLIENT_ID, data.get(CONF_TIDAL_CLIENT_ID))
        self.tidal_client_secret = options.get(CONF_TIDAL_CLIENT_SECRET, data.get(CONF_TIDAL_CLIENT_SECRET))
        self.lastfm_api_key = options.get(CONF_LASTFM_API_KEY, data.get(CONF_LASTFM_API_KEY))
        self.discogs_api_token = options.get(CONF_DISCOGS_API_TOKEN, data.get(CONF_DISCOGS_API_TOKEN))
        self.musicbrainz_enabled = options.get(CONF_MUSICBRAINZ_ENABLED, True)

        # Master AI Settings from config options
        self.master_force_ai = options.get(CONF_FORCE_AI, False)
        self.master_ai_fallback_model = options.get(CONF_AI_FALLBACK_MODEL, "turbo")

        # Store original settings for "Default" mode
        self.original_pixoo_full_control = options.get(CONF_PIXOO_FULL_CONTROL, True)
        self.original_pixoo_contrast = options.get(CONF_PIXOO_CONTRAST, False)
        self.original_pixoo_sharpness = options.get(CONF_PIXOO_SHARPNESS, False)
        self.original_pixoo_colors_enhanced = options.get(CONF_PIXOO_COLORS_ENHANCED, False)
        self.original_pixoo_kernel_effect = options.get(CONF_PIXOO_KERNEL_EFFECT, False)
        self.original_pixoo_special_mode = options.get(CONF_PIXOO_SPECIAL_MODE, False)
        self.original_pixoo_info_fallback = options.get(CONF_PIXOO_INFO_FALLBACK, False)
        self.original_pixoo_show_clock = options.get(CONF_PIXOO_SHOW_CLOCK, False)
        self.original_pixoo_clock_align = options.get(CONF_PIXOO_CLOCK_ALIGN, "Right")
        self.original_pixoo_temperature_enabled = options.get(CONF_PIXOO_TEMPERATURE_ENABLED, False)
        self.original_pixoo_tv_icon_enabled = options.get(CONF_PIXOO_TV_ICON_ENABLED, True)
        self.original_pixoo_spotify_slide = options.get(CONF_PIXOO_SPOTIFY_SLIDE, False)
        self.original_pixoo_show_lyrics = options.get(CONF_PIXOO_SHOW_LYRICS, False)
        self.original_pixoo_show_text_enabled = options.get(CONF_PIXOO_SHOW_TEXT_ENABLED, False) # For ItemList text
        self.original_pixoo_text_background_enabled = options.get(CONF_PIXOO_TEXT_BACKGROUND_ENABLED, True)
        self.original_force_ai = self.master_force_ai # Use the master AI setting for original
        self.original_ai_fallback_model = self.master_ai_fallback_model # Use the master AI setting for original
        self.original_pixoo_burned = False # "Burned" is mode-driven, not a direct original setting

        # Current operational values (will be set by _apply_display_mode_settings)
        self.pixoo_full_control = self.original_pixoo_full_control
        self.pixoo_contrast = self.original_pixoo_contrast
        self.pixoo_sharpness = self.original_pixoo_sharpness
        self.pixoo_colors_enhanced = self.original_pixoo_colors_enhanced
        self.pixoo_kernel_effect = self.original_pixoo_kernel_effect
        self.pixoo_special_mode = self.original_pixoo_special_mode
        self.pixoo_info_fallback = self.original_pixoo_info_fallback
        self.pixoo_show_clock = self.original_pixoo_show_clock
        self.pixoo_clock_align = self.original_pixoo_clock_align
        self.pixoo_temperature_enabled = self.original_pixoo_temperature_enabled
        self.pixoo_tv_icon_enabled = self.original_pixoo_tv_icon_enabled
        self.pixoo_spotify_slide = self.original_pixoo_spotify_slide
        self.pixoo_show_lyrics = self.original_pixoo_show_lyrics
        self.pixoo_show_text_enabled = self.original_pixoo_show_text_enabled # For ItemList text
        self.pixoo_text_background_enabled = self.original_pixoo_text_background_enabled
        self.force_ai = self.original_force_ai
        self.ai_fallback_model = self.original_ai_fallback_model
        self.pixoo_burned: bool = False # This will be set by _apply_display_mode_settings

        self.pixoo_images_cache_size = options.get(CONF_PIXOO_IMAGES_CACHE_SIZE, 25)
        self.pixoo_limit_colors = options.get(CONF_PIXOO_LIMIT_COLORS, "") 
        self.pixoo_lyrics_font = options.get(CONF_PIXOO_LYRICS_FONT, 190)
        self.pixoo_text_clean_title = options.get(CONF_PIXOO_TEXT_CLEAN_TITLE, True)
        self.pixoo_text_special_mode_spotify_slider = options.get(CONF_PIXOO_TEXT_SPECIAL_MODE_SPOTIFY_SLIDER, False)
        
        self.pixoo_text_force_font_color_preset = options.get(CONF_PIXOO_TEXT_FORCE_FONT_COLOR_PRESET, "Automatic")
        self.pixoo_text_force_font_color = options.get(CONF_PIXOO_TEXT_FORCE_FONT_COLOR, "").strip()
        self.pixoo_text_actual_force_font_color: Optional[str] = None
        if self.pixoo_text_force_font_color:
            if re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", self.pixoo_text_force_font_color):
                self.pixoo_text_actual_force_font_color = self.pixoo_text_force_font_color
            else:
                _LOGGER.warning(f"Invalid custom hex color string: '{self.pixoo_text_force_font_color}'.")
        if self.pixoo_text_actual_force_font_color is None:
            selected_color_hex = PREDEFINED_FONT_COLORS.get(self.pixoo_text_force_font_color_preset)
            if selected_color_hex and selected_color_hex not in ["custom", "none"]:
                self.pixoo_text_actual_force_font_color = selected_color_hex

        self.original_pixoo_crop_borders_enabled = options.get(CONF_PIXOO_CROP_BORDERS_ENABLED, False)
        self.original_pixoo_crop_borders_extra = options.get(CONF_PIXOO_CROP_BORDERS_EXTRA, False)
        self.pixoo_crop_borders_enabled = self.original_pixoo_crop_borders_enabled
        self.pixoo_crop_borders_extra = self.original_pixoo_crop_borders_extra

        self.pixoo_lyrics_sync = int(options.get(CONF_PIXOO_LYRICS_SYNC, -1))

        self.display_mode_setting: str = options.get(CONF_DISPLAY_MODE_SETTING, "Default")
        self.crop_mode_setting: str = options.get(CONF_CROP_MODE_SETTING, "Default")

        wled_ip_string = options.get(CONF_WLED_IP, "")
        self.wled_ips = []
        if wled_ip_string:
            potential_ips = [ip.strip() for ip in wled_ip_string.split(',')]
            ip_pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
            for ip_str in potential_ips:
                if ip_str and ip_pattern.match(ip_str):
                    self.wled_ips.append(ip_str)
                elif ip_str:
                    _LOGGER.warning(f"Invalid WLED IP address format ignored: '{ip_str}'")

        self.wled_brightness = options.get(CONF_WLED_BRIGHTNESS, 255)
        self.wled_effect_id = options.get(CONF_WLED_EFFECT_ID, 38)
        self.wled_effect_speed = options.get(CONF_WLED_EFFECT_SPEED, 60)
        self.wled_effect_intensity = options.get(CONF_WLED_EFFECT_INTENSITY, 128)
        self.wled_palette_id = options.get(CONF_WLED_PALETTE_ID, 0)
        self.wled_sound_effect_id = options.get(CONF_WLED_SOUND_EFFECT_ID, 0)
        self.wled_only_at_night = options.get(CONF_WLED_ONLY_AT_NIGHT, False)

        self._fix_config_args()
        self._validate_config()
        self._apply_display_mode_settings() # Apply initial display mode
        self._apply_crop_mode_settings()   # Apply initial crop mode

    def _apply_crop_mode_settings(self, crop_mode_string: Optional[str] = None):
        if crop_mode_string is None:
            crop_mode_string = self.crop_mode_setting
        mode = crop_mode_string.lower()
        _LOGGER.debug(f"Applying crop mode: {crop_mode_string}")
        if mode == "no crop":
            self.pixoo_crop_borders_enabled = False
            self.pixoo_crop_borders_extra = False
        elif mode == "crop":
            self.pixoo_crop_borders_enabled = True
            self.pixoo_crop_borders_extra = False
        elif mode == "extra crop":
            self.pixoo_crop_borders_enabled = True
            self.pixoo_crop_borders_extra = True
        elif mode == "default":
            self.pixoo_crop_borders_enabled = self.original_pixoo_crop_borders_enabled
            self.pixoo_crop_borders_extra = self.original_pixoo_crop_borders_extra
        else:
            _LOGGER.warning(f"Unknown crop mode: {crop_mode_string}. Applying Default.")
            self.pixoo_crop_borders_enabled = self.original_pixoo_crop_borders_enabled
            self.pixoo_crop_borders_extra = self.original_pixoo_crop_borders_extra
        _LOGGER.debug(f"Applied crop mode '{crop_mode_string}': enabled={self.pixoo_crop_borders_enabled}, extra={self.pixoo_crop_borders_extra}")

    def _apply_display_mode_settings(self, mode_string: Optional[str] = None):
        if mode_string is None:
            mode_string = self.display_mode_setting
        
        m = mode_string.lower()
        _LOGGER.debug(f"Applying display mode: '{mode_string}' (parsed as '{m}')")

        # Start by resetting to a known state (e.g., "Clean" or "Default" base)
        # For "Default", we revert to saved original settings
        if m == "default":
            self.pixoo_show_lyrics = self.original_pixoo_show_lyrics
            self.pixoo_spotify_slide = self.original_pixoo_spotify_slide
            self.pixoo_special_mode = self.original_pixoo_special_mode
            self.pixoo_show_clock = self.original_pixoo_show_clock
            self.pixoo_temperature_enabled = self.original_pixoo_temperature_enabled
            self.pixoo_show_text_enabled = self.original_pixoo_show_text_enabled # ItemList text
            self.pixoo_text_background_enabled = self.original_pixoo_text_background_enabled
            self.force_ai = self.original_force_ai
            self.ai_fallback_model = self.original_ai_fallback_model
            self.pixoo_burned = self.original_pixoo_burned # Revert to original burned state
        else:
            # For any other mode, start with a "clean slate" (all features off)
            # then enable features based on the mode string.
            self.pixoo_show_lyrics = False
            self.pixoo_spotify_slide = False
            self.pixoo_special_mode = False
            self.pixoo_show_clock = False
            self.pixoo_temperature_enabled = False
            self.pixoo_show_text_enabled = False # ItemList text
            self.pixoo_text_background_enabled = False
            self.force_ai = False
            self.ai_fallback_model = self.original_ai_fallback_model # Default AI model
            self.pixoo_burned = False

            # Enable features based on keywords in the mode string
            if "lyrics" in m: self.pixoo_show_lyrics = True
            if "spotify slider" in m: self.pixoo_spotify_slide = True # Exact phrase
            if "special mode" in m: self.pixoo_special_mode = True # Exact phrase
            if "clock" in m: self.pixoo_show_clock = True
            if "temperature" in m: self.pixoo_temperature_enabled = True
            if "text" in m: self.pixoo_show_text_enabled = True # ItemList text
            if "background" in m: self.pixoo_text_background_enabled = True
            if "ai generation" in m: self.force_ai = True # Exact phrase
            if "burned" in m: self.pixoo_burned = True

            if self.force_ai: # Only set AI model if AI generation is active
                if "flux" in m: self.ai_fallback_model = "flux"
                elif "turbo" in m: self.ai_fallback_model = "turbo"
                # If neither "flux" nor "turbo" is specified with "ai generation", it defaults to self.original_ai_fallback_model

            # Specific "clean" like modes
            if m == "clean": # Already handled by the else block's initial reset
                pass 
            elif m == "album art only": # Explicitly ensure everything else is off
                self.pixoo_show_lyrics = False; self.pixoo_show_clock = False; self.pixoo_temperature_enabled = False
                self.pixoo_show_text_enabled = False; self.pixoo_text_background_enabled = False
                self.pixoo_special_mode = False; self.pixoo_spotify_slide = False; self.pixoo_burned = False
                self.force_ai = False
            elif m == "lyrics only": # Explicitly ensure everything else is off, but lyrics true
                self.pixoo_show_lyrics = True
                self.pixoo_spotify_slide = False; self.pixoo_special_mode = False; self.pixoo_show_clock = False
                self.pixoo_temperature_enabled = False; self.pixoo_show_text_enabled = False
                self.pixoo_text_background_enabled = False; self.force_ai = False; self.pixoo_burned = False
        
        # Ensure background for ItemList text is only enabled if some ItemList text is actually shown
        if not (self.pixoo_show_clock or self.pixoo_temperature_enabled or (self.pixoo_show_text_enabled and m not in ["lyrics only", "album art only"])):
            self.pixoo_text_background_enabled = False
        
        # Update dependent combined flag
        self.special_mode_spotify_slider = bool(
            self.pixoo_spotify_slide and self.pixoo_special_mode and self.pixoo_show_text_enabled
        )
        _LOGGER.debug(f"Applied mode '{mode_string}': lyrics={self.pixoo_show_lyrics}, clock={self.pixoo_show_clock}, temp={self.pixoo_temperature_enabled}, ItemList text={self.pixoo_show_text_enabled}, burned text={self.pixoo_burned}, force_ai={self.force_ai}, ai_model={self.ai_fallback_model}, text_bg={self.pixoo_text_background_enabled}, special_mode={self.pixoo_special_mode}, spotify_slide={self.pixoo_spotify_slide}")


    def _fix_config_args(self):
        if isinstance(self.pixoo_limit_colors, str) and self.pixoo_limit_colors.lower() == "false":
            self.pixoo_limit_colors = False
        elif isinstance(self.pixoo_limit_colors, str):
            try:
                self.pixoo_limit_colors = int(self.pixoo_limit_colors)
            except ValueError:
                self.pixoo_limit_colors = False

        if not self.temperature_sensor_entity: self.temperature_sensor_entity = None
        if not self.spotify_client_id: self.spotify_client_id = None
        if not self.spotify_client_secret: self.spotify_client_secret = None
        if not self.tidal_client_id: self.tidal_client_id = None
        if not self.tidal_client_secret: self.tidal_client_secret = None
        if not self.lastfm_api_key: self.lastfm_api_key = None
        if not self.discogs_api_token: self.discogs_api_token = None
        if not self.pixoo_text_force_font_color: self.pixoo_text_force_font_color = None 

    def _validate_config(self):
        if not self.media_player_entity_id:
            raise ValueError("media_player_entity_id is required")
        if not self.pixoo_ip:
            raise ValueError("pixoo_ip is required")

        if self.ai_fallback_model not in AI_FALLBACK_MODEL_OPTIONS:
            self.ai_fallback_model = "turbo"
        if self.pixoo_clock_align not in CLOCK_ALIGN_OPTIONS:
            self.pixoo_clock_align = "Right"
        try:
            font = int(self.pixoo_lyrics_font)
            if font not in LYRICS_FONT_OPTIONS: self.pixoo_lyrics_font = 190
            else: self.pixoo_lyrics_font = font
        except ValueError: self.pixoo_lyrics_font = 190

    def get(self, key, default=None):
        return getattr(self, key, default)

    def report_config_issues(self):
        pass
