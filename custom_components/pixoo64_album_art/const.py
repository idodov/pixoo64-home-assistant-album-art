DOMAIN = "pixoo64_album_art"
CONF_MEDIA_PLAYER = "media_player"
CONF_PIXOO_IP = "pixoo_ip"
# CONF_HA_URL = "ha_url" # Removed

# Existing constants
CONF_TEMPERATURE_SENSOR_ENTITY = "temperature_sensor_entity"
CONF_LIGHT_ENTITY = "light_entity"
CONF_AI_FALLBACK_MODEL = "ai_fallback_model"
CONF_FORCE_AI = "force_ai"
CONF_MUSICBRAINZ_ENABLED = "musicbrainz_enabled"
CONF_SPOTIFY_CLIENT_ID = "spotify_client_id"
CONF_SPOTIFY_CLIENT_SECRET = "spotify_client_secret"
CONF_TIDAL_CLIENT_ID = "tidal_client_id"
CONF_TIDAL_CLIENT_SECRET = "tidal_client_secret"
CONF_LASTFM_API_KEY = "lastfm_api_key"
CONF_DISCOGS_API_TOKEN = "discogs_api_token"

# AI Fallback Model Options
AI_FALLBACK_MODEL_OPTIONS = ["turbo", "flux"]

# New Pixoo device settings constants
CONF_PIXOO_FULL_CONTROL = "pixoo_full_control"
CONF_PIXOO_CONTRAST = "pixoo_contrast"
CONF_PIXOO_SHARPNESS = "pixoo_sharpness"
CONF_PIXOO_COLORS_ENHANCED = "pixoo_colors_enhanced"
CONF_PIXOO_KERNEL_EFFECT = "pixoo_kernel_effect"
CONF_PIXOO_SPECIAL_MODE = "pixoo_special_mode"
CONF_PIXOO_INFO_FALLBACK = "pixoo_info_fallback"
CONF_PIXOO_SHOW_CLOCK = "pixoo_show_clock"
CONF_PIXOO_CLOCK_ALIGN = "pixoo_clock_align"
CONF_PIXOO_TEMPERATURE_ENABLED = "pixoo_temperature_enabled"
CONF_PIXOO_TV_ICON_ENABLED = "pixoo_tv_icon_enabled"
CONF_PIXOO_SPOTIFY_SLIDE = "pixoo_spotify_slide"
CONF_PIXOO_IMAGES_CACHE_SIZE = "pixoo_images_cache_size"
CONF_PIXOO_LIMIT_COLORS = "pixoo_limit_colors"
CONF_PIXOO_SHOW_LYRICS = "pixoo_show_lyrics"
CONF_PIXOO_LYRICS_FONT = "pixoo_lyrics_font"
CONF_PIXOO_SHOW_TEXT_ENABLED = "pixoo_show_text_enabled"
CONF_PIXOO_TEXT_CLEAN_TITLE = "pixoo_text_clean_title"
CONF_PIXOO_TEXT_BACKGROUND_ENABLED = "pixoo_text_background_enabled"
CONF_PIXOO_TEXT_SPECIAL_MODE_SPOTIFY_SLIDER = "pixoo_text_special_mode_spotify_slider"
CONF_PIXOO_TEXT_FORCE_FONT_COLOR = "pixoo_text_force_font_color"
CONF_PIXOO_CROP_BORDERS_ENABLED = "pixoo_crop_borders_enabled"
CONF_PIXOO_CROP_BORDERS_EXTRA = "pixoo_crop_borders_extra"

# New WLED settings constants
CONF_WLED_IP = "wled_ip"
CONF_WLED_BRIGHTNESS = "wled_brightness"
CONF_WLED_EFFECT_ID = "wled_effect_id"
CONF_WLED_EFFECT_SPEED = "wled_effect_speed"
CONF_WLED_EFFECT_INTENSITY = "wled_effect_intensity"
CONF_WLED_PALETTE_ID = "wled_palette_id"
CONF_WLED_SOUND_EFFECT_ID = "wled_sound_effect_id"
CONF_WLED_ONLY_AT_NIGHT = "wled_only_at_night"

# Options for select fields
CLOCK_ALIGN_OPTIONS = ["Left", "Right"]
LYRICS_FONT_OPTIONS = [2, 4, 32, 52, 58, 62, 48, 80, 158, 186, 190, 590]

# Input number specific
CONF_PIXOO_LYRICS_SYNC = "pixoo_lyrics_sync"

# Predefined font colors for text display on Pixoo
PREDEFINED_FONT_COLORS = {
    "Automatic": "none",  # Key changed, Special value to not force color / use auto-detected
    "White": "#FFFFFF",
    # "Black": "#000000", # Removed as per review instruction
    "Bright Yellow": "#FFFF00",
    "Gold": "#FFD700",
    "Light Cyan": "#E0FFFF",
    "Cyan / Aqua": "#00FFFF", # Combined as they are the same
    "Bright Magenta": "#FF00FF",
    "Pink": "#FFC0CB",
    "Lime Green": "#32CD32", # Changed from #00FF00 for better readability sometimes
    "Light Green": "#90EE90",
    "Orange": "#FFA500",
    "Red": "#FF0000",
    "Sky Blue": "#87CEEB",
    "Deep Sky Blue": "#00BFFF",
    "Spring Green": "#00FF7F",
    "Chartreuse": "#7FFF00",
    "Hot Pink": "#FF69B4",
    "Violet": "#EE82EE",
    "Turquoise": "#40E0D0",
    "Light Salmon": "#FFA07A", # Added another bright option
    "Custom": "custom"  # Special value to indicate custom hex input
}

CONF_PIXOO_TEXT_FORCE_FONT_COLOR_PRESET = "pixoo_text_force_font_color_preset"

# Display Mode Select
CONF_DISPLAY_MODE_SETTING = "display_mode_setting"
DISPLAY_MODE_OPTIONS = [
    "Default", "Clean", "AI Generation (Flux)", "AI Generation (Turbo)",
    "Burned", "Burned | Clock", "Burned | Clock (Background)",
    "Burned | Temperature", "Burned | Temperature (Background)",
    "Burned | Clock & Temperature (Background)", "Text", "Text (Background)",
    "Clock", "Clock (Background)", "Clock | Temperature",
    "Clock | Temperature (Background)", "Clock | Temperature | Text",
    "Clock | Temperature | Text (Background)", "Lyrics", "Lyrics (Background)",
    "Temperature", "Temperature (Background)", "Temperature | Text",
    "Temperature | Text (Background)", "Special Mode", "Special Mode | Text"
]
SPOTIFY_SLIDER_OPTIONS = [ # Renamed from SPOTIFY_SLIDER_MODES for clarity
    "Spotify Slider (beta)", 
    "Spotify Slider Special Mode with Text (beta)"
]

# Crop Mode Select
CONF_CROP_MODE_SETTING = "crop_mode_setting"
CROP_MODE_OPTIONS = ["Default", "No Crop", "Crop", "Extra Crop"]
