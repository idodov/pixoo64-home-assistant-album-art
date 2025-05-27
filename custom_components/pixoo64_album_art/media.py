import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, State
    from .config import Config
    from .image import ImageProcessor
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN # Import states

_LOGGER = logging.getLogger(__name__)

class MediaData:
    """Holds and processes media player and related entity data."""

    def __init__(self, hass: "HomeAssistant", config: "Config", image_processor: "ImageProcessor"):
        """Initialize MediaData."""
        self.hass = hass
        self.config = config
        self.image_processor = image_processor # Used for potential image processing tasks related to media

        # Initialize attributes that will be updated
        self.artist: Optional[str] = None
        self.album: Optional[str] = None
        self.title: Optional[str] = None
        self.cover_url: Optional[str] = None
        self.radio_logo_url: Optional[str] = None # For radio streams
        self.tv_logo_url: Optional[str] = None # For TV streams/channels
        self.is_playing: bool = False
        self.is_radio: bool = False
        self.is_tv: bool = False
        self.is_spotify: bool = False
        self.lyrics: list[str] = []
        self.duration: int = 0
        self.position: int = 0
        self.last_update: Optional[datetime] = None
        self.current_mode: Optional[str] = None # e.g., "Music", "TV", "Radio", "Clock"
        self.media_player_state: Optional[str] = None # e.g. "playing", "paused", "off"

        # Additional attributes from AppDaemon script
        self.app_name: Optional[str] = None
        self.media_content_type: Optional[str] = None
        self.media_title_cleaned: Optional[str] = None
        self.ai_prompt: Optional[str] = None
        self.stream_image_url: Optional[str] = None # For generic streams if applicable
        self.temperature: Optional[str] = None # For external temperature sensor
        self.pic_source: Optional[str] = None # Added

    def clean_title(self, title: str, remove_brackets: bool = True) -> str:
        """Cleans a media title by removing common bracketed expressions and extra spaces."""
        if not title:
            return ""
        if remove_brackets:
            title = re.sub(r'\s*\[.*?\]|\s*\(.*?\)', '', title).strip()
        title = ' '.join(title.split()) # Remove extra spaces
        return title

    def format_ai_image_prompt(self) -> str:
        """Formats a prompt for an AI image generator based on current media."""
        # Based on AppDaemon script's logic
        if self.is_tv and self.title:
            prompt = f"{self.title}"
            if self.app_name and self.app_name not in self.title: # e.g. app_name = "Netflix"
                prompt += f", {self.app_name}"
            prompt += ", movie poster style, cinematic lighting, high detail"
        elif self.is_radio and self.title:
            prompt = f"{self.title}, radio, music broadcast, vibrant colors"
        elif self.artist and self.title:
            prompt = f"{self.artist} - {self.title}, album cover art, high detail, iconic"
            if self.album and self.album not in self.title:
                prompt += f", {self.album}"
        elif self.title:
            prompt = f"{self.title}, abstract art, music visualization"
        else:
            prompt = "abstract colorful music visualization" # Default prompt
        return prompt

    async def _get_lyrics(self, artist: str, title: str) -> list[str]:
        """
        Placeholder for fetching lyrics.
        In the future, this will call a LyricsProvider.
        """
        _LOGGER.debug(f"Lyrics fetching for '{title}' by '{artist}' is not yet implemented.")
        # For now, return empty list as per subtask instructions
        return []

    async def update(self):
        """
        Fetches current media player state and updates MediaData attributes.
        This is the core method to interact with Home Assistant.
        """
        _LOGGER.debug(f"Updating MediaData for media_player: {self.config.media_player_entity_id}")
        if not self.config.media_player_entity_id:
            _LOGGER.error("media_player_entity_id is not configured.")
            return

        media_player_state_obj: Optional["State"] = self.hass.states.get(self.config.media_player_entity_id)

        if not media_player_state_obj:
            _LOGGER.warning(f"Media player entity {self.config.media_player_entity_id} not found.")
            self.is_playing = False
            self.media_player_state = "unavailable"
            return

        attributes = media_player_state_obj.attributes
        self.media_player_state = media_player_state_obj.state
        self.is_playing = self.media_player_state == "playing"

        self.artist = attributes.get("media_artist")
        self.album = attributes.get("media_album_name")
        self.title = attributes.get("media_title")
        self.media_content_type = attributes.get("media_content_type")
        self.app_name = attributes.get("app_name") # Common for Chromecasts, Android TV
        self.duration = attributes.get("media_duration", 0)
        self.position = attributes.get("media_position", 0)
        self.last_update = attributes.get("media_position_updated_at") or datetime.now()


        # Determine media type (TV, Radio, Music)
        self.is_tv = self.media_content_type in ["tvshow", "movie", "episode", "channel"] or \
                     (self.app_name and any(tv_app in self.app_name.lower() for tv_app in ["netflix", "plex", "hbo", "disney", "youtube", "tvheadend"])) # Add more TV app names
        self.is_radio = self.media_content_type in ["radio", "music"] and \
                        ("radio" in (self.title or "").lower() or "fm" in (self.title or "").lower() or "am" in (self.title or "").lower() or \
                         (self.app_name and "tunein" in self.app_name.lower())) # Add more radio indicators
        
        if self.is_tv and self.is_radio: # TV apps can play radio, prioritize TV if ambiguous
            if self.app_name and "tunein" not in self.app_name.lower(): # If it's a TV app not specifically TuneIn
                 self.is_radio = False
            elif not self.app_name : # If no app name, and title suggests radio, it might be radio on TV
                 if not ("radio" in (self.title or "").lower() or "fm" in (self.title or "").lower()):
                     self.is_radio = False


        self.is_spotify = "spotify" in (attributes.get("media_content_id", "") or "").lower() or \
                          "spotify" in (self.app_name or "").lower()


        # Get cover art URL
        self.cover_url = attributes.get("entity_picture")
        self.radio_logo_url = None # Reset
        self.tv_logo_url = None # Reset
        self.stream_image_url = None # Reset

        if self.is_radio:
            # Try to find a better radio logo if available (e.g. from a sensor, or predefined)
            # For now, use entity_picture if it seems like a logo, or a generic one.
            # Logic from AppDaemon: playing_radio, radio_logo
            # self.radio_logo_url = self.image_processor.get_radio_logo(self.title, self.artist) # This would be future
            if self.cover_url and "genre" not in self.cover_url: # Generic genre images are often not good logos
                 self.radio_logo_url = self.cover_url
            else: # Fallback or use a default radio icon image
                 self.radio_logo_url = None # Let ImageProcessor handle default later if needed
            self.current_mode = "Radio"
        elif self.is_tv:
            # Try to find a TV show/channel logo
            # self.tv_logo_url = self.image_processor.get_tv_logo(self.title) # This would be future
            self.tv_logo_url = self.cover_url # Often entity_picture is the show/movie art
            self.current_mode = "TV"
            # If it's a "channel" type, entity_picture might be the channel logo
            if self.media_content_type == "channel":
                self.tv_logo_url = self.cover_url
            else: # For movies/episodes, cover_url is usually the poster.
                  # We might want a different logo for the *app* (e.g. Netflix logo)
                  # This would require more complex logic, perhaps another sensor or config for app logos
                  pass
        else: # Music or other
            self.current_mode = "Music"
            # If cover_url is None for music, it might be a stream without art.
            # AppDaemon script had stream_image_url for this.
            if not self.cover_url and self.is_playing:
                self.stream_image_url = None # Placeholder: could generate one or use a default
        
        if not self.is_playing and self.media_player_state != "paused": # If off, idle, etc.
            self.current_mode = "Off" # Or "Idle", "Standby"
            if self.config.pixoo_show_clock: # Default to clock if player is off and clock is enabled
                self.current_mode = "Clock"


        # Clean title
        if self.title:
            self.media_title_cleaned = self.clean_title(self.title, self.config.pixoo_text_clean_title)
        else:
            self.media_title_cleaned = None

        # Format AI prompt
        if self.config.force_ai or (not self.cover_url and self.is_playing and not self.is_radio and not self.is_tv): # Condition for AI fallback
            self.ai_prompt = self.format_ai_image_prompt()
        else:
            self.ai_prompt = None

        # Lyrics fetching (currently commented out as per subtask)
        # if self.is_playing and self.artist and self.title and not self.is_tv and not self.is_radio:
        #     if self.config.pixoo_show_lyrics: # Check if lyrics display is enabled
        #         self.lyrics = await self._get_lyrics(self.artist, self.title)
        #     else:
        #         self.lyrics = []
        # else:
        #     self.lyrics = []

        # Fetch external temperature if configured
        self.temperature = None # Reset or initialize
        sensor_entity_id = self.config.temperature_sensor_entity

        if sensor_entity_id:
            temp_sensor_state = self.hass.states.get(sensor_entity_id)
            if temp_sensor_state and temp_sensor_state.state not in [STATE_UNAVAILABLE, STATE_UNKNOWN]:
                temp_value_str = temp_sensor_state.state
                unit = temp_sensor_state.attributes.get("unit_of_measurement", "")
                try:
                    # Attempt to convert to float then int for display, similar to original script
                    temp_numeric = float(temp_value_str)
                    self.temperature = f"{int(temp_numeric)}{unit}" # Or apply other formatting as desired
                    _LOGGER.debug(f"Fetched external temperature: {self.temperature} from {sensor_entity_id}")
                except ValueError:
                    _LOGGER.warning(f"Could not parse temperature value '{temp_value_str}' from {sensor_entity_id}")
                    # self.temperature remains None
            elif temp_sensor_state:
                _LOGGER.debug(f"Temperature sensor {sensor_entity_id} is {temp_sensor_state.state}")
            else:
                _LOGGER.warning(f"Temperature sensor {sensor_entity_id} not found.")


        _LOGGER.debug(f"MediaData updated: Title='{self.title}', Artist='{self.artist}', Album='{self.album}', Mode='{self.current_mode}', Playing='{self.is_playing}'")
        _LOGGER.debug(f"Cover URL: {self.cover_url}, Radio Logo: {self.radio_logo_url}, TV Logo: {self.tv_logo_url}, AI Prompt: {self.ai_prompt}, Temp: {self.temperature}")

    def as_dict(self) -> dict:
        """Returns a dictionary representation of the media data, useful for sensor attributes."""
        return {
            "artist": self.artist,
            "album": self.album,
            "title": self.title,
            "media_title_cleaned": self.media_title_cleaned,
            "cover_url": self.cover_url,
            "radio_logo_url": self.radio_logo_url,
            "tv_logo_url": self.tv_logo_url,
            "stream_image_url": self.stream_image_url,
            "is_playing": self.is_playing,
            "is_radio": self.is_radio,
            "is_tv": self.is_tv,
            "is_spotify": self.is_spotify,
            "lyrics_available": bool(self.lyrics), # Just indicate if lyrics were fetched (even if empty)
            "duration": self.duration,
            "position": self.position,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "current_mode": self.current_mode,
            "media_player_state": self.media_player_state,
            "app_name": self.app_name,
            "media_content_type": self.media_content_type,
            "ai_prompt": self.ai_prompt,
            "temperature": self.temperature, # Added temperature
            'pic_source': self.pic_source, # Added
        }

# Example usage (for testing, not part of the class):
# async def main():
#     # Mock HASS and Config objects
#     class MockHASS:
#         def __init__(self):
#             self.states = {} # Dict to store mock states
#         def get_state(self, entity_id):
#             return self.states.get(entity_id)
#
#     class MockConfig:
#         def __init__(self):
#             self.media_player_entity_id = "media_player.test_player"
#             self.pixoo_text_clean_title = True
#             self.force_ai = False
#             # ... other config attrs
#
#     class MockState:
#         def __init__(self, state, attributes):
#             self.state = state
#             self.attributes = attributes
#
#     hass = MockHASS()
#     config = MockConfig()
#     image_processor = None # Mock or actual if needed for deeper testing
#
#     # Populate a mock media player state
#     hass.states[config.media_player_entity_id] = MockState(
#         state="playing",
#         attributes={
#             "media_title": "Bohemian Rhapsody [Remastered]",
#             "media_artist": "Queen",
#             "media_album_name": "A Night At The Opera (2011 Remaster)",
#             "entity_picture": "/local/qotsa.jpg",
#             "media_content_type": "music",
#             "app_name": "Spotify",
#             "media_duration": 354,
#             "media_position": 60,
#             "media_position_updated_at": datetime.now()
#         }
#     )
#
#     media_data = MediaData(hass, config, image_processor)
#     await media_data.update()
#
#     print(f"Title: {media_data.title}")
#     print(f"Cleaned Title: {media_data.media_title_cleaned}")
#     print(f"Artist: {media_data.artist}")
#     print(f"Album: {media_data.album}")
#     print(f"Cover URL: {media_data.cover_url}")
#     print(f"Is Playing: {media_data.is_playing}")
#     print(f"Is Spotify: {media_data.is_spotify}")
#     print(f"Current Mode: {media_data.current_mode}")
#     print(f"AI Prompt: {media_data.ai_prompt}")

# if __name__ == "__main__":
#    asyncio.run(main())
