import asyncio
import json
import logging
import random
import re
from typing import TYPE_CHECKING, Any, Optional

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession

# Assuming get_font is not strictly needed by split_string if using character limits primarily
# from .helpers import get_bidi, has_bidi, split_string, get_font
from .helpers import get_bidi, has_bidi, split_string # Keep it minimal for now

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from .config import Config
    from .pixoo import PixooDevice
    from .media import MediaData
    from .image import ImageProcessor # Though likely not used directly by LyricsProvider

_LOGGER = logging.getLogger(__name__)

class LyricsProvider:
    """Fetches and prepares lyrics for display on the Pixoo64 device."""

    def __init__(self, config: "Config", hass: "HomeAssistant", image_processor: "ImageProcessor", pixoo_device: "PixooDevice"):
        """Initialize LyricsProvider."""
        self.config = config
        self.hass = hass
        self.image_processor = image_processor # Stored, though might not be used
        self.pixoo_device = pixoo_device
        self.lyrics_data: list[tuple[int, str]] = [] # Stores (time_ms, text) tuples
        self.last_lyrics_text: str = ""
        # self._last_sent_original_lyric_time_ms: Optional[int] = None # Replaced by timed clear logic
        self.clear_lyric_task: Optional[asyncio.Task] = None

    async def cancel_timed_clear(self):
        """Cancel any pending timed lyric clearing task."""
        if self.clear_lyric_task and not self.clear_lyric_task.done():
            self.clear_lyric_task.cancel()
            _LOGGER.debug("Cancelled previous timed lyric clear task.")
        self.clear_lyric_task = None

    async def get_lyrics(self, artist: str, title: str) -> list[tuple[int, str]]:
        """Fetches lyrics from textyl.co API and parses them."""
        await self.cancel_timed_clear() # Cancel any pending clear when new lyrics are fetched
        self.lyrics_data = []
        if not artist or not title:
            _LOGGER.debug("Artist or title missing, cannot fetch lyrics.")
            return []

        # Sanitize artist and title for URL
        artist_clean = re.sub(r'[^\w\s-]', '', artist).replace(' ', '-')
        title_clean = re.sub(r'[^\w\s-]', '', title).replace(' ', '-')
        
        url = f"https://api.textyl.co/api/lyrics/{artist_clean}/{title_clean}"
        _LOGGER.debug(f"Fetching lyrics from: {url}")

        session = async_get_clientsession(self.hass)
        try:
            async with session.get(url, timeout=15) as response: # Increased timeout slightly
                if response.status == 200:
                    content = await response.text()
                    if content.strip().startswith("<"): 
                        _LOGGER.warning(f"Lyrics API for '{title}' by '{artist}' returned HTML (likely no lyrics or error).")
                        return []
                    
                    try:
                        data = json.loads(content)
                    except json.JSONDecodeError:
                        _LOGGER.warning(f"Failed to decode JSON lyrics for '{title}' by '{artist}'. Response snippet: {content[:200]}")
                        return []

                    if isinstance(data, list):
                        parsed_lyrics = []
                        for item in data:
                            if isinstance(item, dict) and "seconds" in item and "lyrics" in item:
                                time_ms = int(float(item["seconds"]) * 1000) # Ensure float conversion for seconds
                                text = item["lyrics"].strip()
                                if text:
                                    parsed_lyrics.append((time_ms, text))
                            elif isinstance(item, str): # Should not happen with textyl.co if successful
                                _LOGGER.warning("Lyrics API returned flat string list (no timestamps), discarding.")
                                return [] # Explicitly return empty if format is wrong

                        if not parsed_lyrics:
                             _LOGGER.info(f"No lyrics lines found for '{title}' by '{artist}' in the response, or format was empty after parsing.")
                        else:
                            _LOGGER.info(f"Fetched and parsed {len(parsed_lyrics)} lines of lyrics for '{title}' by '{artist}'.")
                        self.lyrics_data = parsed_lyrics
                        return self.lyrics_data
                    else:
                        _LOGGER.warning(f"Unexpected lyrics format for '{title}' by '{artist}'. Expected list, got: {type(data)}. Content: {str(data)[:200]}")
                        return []
                else:
                    _LOGGER.warning(f"Failed to get lyrics for '{title}' by '{artist}'. Status: {response.status}, Response: {await response.text()}")
                    return []
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Network error fetching lyrics for '{title}' by '{artist}': {e}")
            return []
        except asyncio.TimeoutError:
            _LOGGER.error(f"Timeout fetching lyrics for '{title}' by '{artist}'.")
            return []
        except Exception as e:
            _LOGGER.error(f"Unexpected error fetching lyrics for '{title}' by '{artist}': {e}", exc_info=True)
            return []

    async def calculate_position(self, media_data: "MediaData", current_position_ms: int):
        """Calculates the current lyric based on media position and sends it to Pixoo."""
        await self.cancel_timed_clear() # Cancel any pending clear task

        if not self.lyrics_data or not self.config.pixoo_show_lyrics:
            if self.last_lyrics_text: # If lyrics were shown but now should not be
                _LOGGER.debug("No lyrics to display or lyrics disabled, clearing last lyric.")
                await self.pixoo_device.send_command({"Command": "Draw/ClearHttpText"})
                self.last_lyrics_text = ""
            return

        sync_offset_ms = self.config.pixoo_lyrics_sync 
        if sync_offset_ms == -1: sync_offset_ms = 0
            
        current_lyric_text = ""
        current_lyric_original_time_ms = -1
        current_lyric_idx = -1

        for idx, (original_lyric_time_ms, text_line) in enumerate(self.lyrics_data):
            adjusted_display_time_ms = original_lyric_time_ms + sync_offset_ms
            if current_position_ms >= adjusted_display_time_ms:
                current_lyric_text = text_line
                current_lyric_original_time_ms = original_lyric_time_ms
                current_lyric_idx = idx
            else:
                break 
        
        if current_lyric_text and current_lyric_text != self.last_lyrics_text:
            self.last_lyrics_text = current_lyric_text
            _LOGGER.debug(f"Displaying lyric: '{current_lyric_text}' (orig time: {current_lyric_original_time_ms}ms, offset: {sync_offset_ms}ms) at player pos: {current_position_ms}ms")
            
            payloads = self.create_lyrics_payloads(current_lyric_text) # This already sends ClearHttpText first
            # Send the new lyric payloads (create_lyrics_payloads prepends a clear command)
            for payload_item in payloads:
                try:
                    await self.pixoo_device.send_command(payload_item)
                    if len(payloads) > 1: 
                        await asyncio.sleep(0.05) 
                except Exception as e:
                    _LOGGER.error(f"Error sending lyrics command part to Pixoo: {e}")
                    break 
            
            # Schedule timed clear
            duration_ms = 0
            if current_lyric_idx != -1: # Lyric was found
                if current_lyric_idx + 1 < len(self.lyrics_data):
                    next_lyric_original_time_ms = self.lyrics_data[current_lyric_idx + 1][0]
                    # Duration is until the next lyric's *original* time, before that lyric's own offset adjustment
                    calculated_duration_ms = next_lyric_original_time_ms - current_lyric_original_time_ms
                    # Cap duration to avoid excessively long timers, e.g. 15s max
                    # Also ensure it's positive.
                    duration_ms = max(0, min(calculated_duration_ms, 15000)) 
                else: # Last lyric line
                    duration_ms = 10000 # Default 10 seconds for the last line

                if duration_ms > 0:
                    _LOGGER.debug(f"Scheduling lyric clear in {duration_ms / 1000.0}s")
                    async def _clear_lyrics_after_duration(delay_seconds: float):
                        try:
                            await asyncio.sleep(delay_seconds)
                            _LOGGER.debug(f"Auto-clearing lyrics from Pixoo after {delay_seconds}s.")
                            # Check if the lyric is still the one we scheduled to clear
                            if self.last_lyrics_text == current_lyric_text:
                                await self.pixoo_device.send_command({"Command": "Draw/ClearHttpText"})
                                self.last_lyrics_text = "" # Reset so it can be shown again if needed
                        except asyncio.CancelledError:
                            _LOGGER.debug("Lyric clear task cancelled.")
                        except Exception as e_clear:
                            _LOGGER.error(f"Error in timed lyric clear task: {e_clear}")
                    
                    self.clear_lyric_task = asyncio.create_task(_clear_lyrics_after_duration(duration_ms / 1000.0))
        
        elif not current_lyric_text and self.last_lyrics_text: # No current lyric, but something was on screen
            _LOGGER.debug("No current lyric, clearing displayed lyric immediately.")
            await self.pixoo_device.send_command({"Command": "Draw/ClearHttpText"})
            self.last_lyrics_text = ""


    def create_lyrics_payloads(self, text: str) -> list[dict]:
        """
        Creates JSON payload(s) for sending lyrics text to Pixoo.
        Prepends a command to clear previous lyrics.
        """
        payload_list = [{"Command": "Draw/ClearHttpText"}] # Clear previous text first
        font_choice = self.config.pixoo_lyrics_font
        
        if has_bidi(text): 
            text = get_bidi(text)

        # Character limits per font
        char_limits = {2: 12, 4: 10, 32: 12, 52: 10, 58: 8, 62: 7, 48: 12, 80: 10, 158: 8, 186: 7, 190: 10, 590: 8}
        max_chars = char_limits.get(font_choice, 10) 

        words = text.split(' ')
        line1, line2 = "", ""
        current_len_line1 = 0
        current_len_line2 = 0

        for word in words:
            word_len = len(word)
            if current_len_line1 + word_len + (1 if line1 else 0) <= max_chars:
                line1 += (" " if line1 else "") + word
                current_len_line1 += word_len + (1 if line1 else 0)
            elif current_len_line2 + word_len + (1 if line2 else 0) <= max_chars:
                line2 += (" " if line2 else "") + word
                current_len_line2 += word_len + (1 if line2 else 0)
            else: # Word doesn't fit in line2, append to line2 anyway (will be truncated by Pixoo or overflow)
                line2 += (" " if line2 else "") + word
                current_len_line2 += word_len + (1 if line2 else 0)
                # Potentially log truncation if word is very long, or handle by splitting word.
                # For now, matching simpler behavior.
                break # Stop adding words if they overflow significantly

        display_lines = [line1.strip()]
        if line2.strip():
            display_lines.append(line2.strip())
        
        text_id_counter = random.randint(1, 10000) 

        # Default y position for lyrics (usually bottom of screen)
        # If one line, center it vertically a bit more, e.g. y=58. If two lines, y=56 for first.
        base_y = 56 
        line_height_approx = 8 # Approximate height of one line of text

        if len(display_lines) == 1:
             base_y = 58 # Slightly adjust for single centered line

        for i, line_text in enumerate(display_lines):
            if not line_text: continue # Skip empty lines

            current_y = base_y + (i * line_height_approx)
            
            # Ensure 'y' does not exceed screen bounds (e.g. 63 for 64px screen)
            current_y = min(current_y, 63 - (line_height_approx // 2))


            payload = {
                "Command": "Draw/SendHttpText",
                "TextId": str(text_id_counter + i), # Ensure unique TextId for each line
                "x": 0,
                "y": current_y,
                "dir": 0, 
                "font": font_choice,
                "TextWidth": 64, 
                "speed": 10, # Pixoo may ignore speed for static text, but good to include
                "TextString": line_text,
                "color": self.config.pixoo_text_actual_force_font_color or "#FFFFFF", # Use resolved actual color
                "align": 1, # Horizontal center alignment
            }
            if i > 0 : # If this is the second line (append logic)
                # The AppDaemon script used "append": 1. If PixooDevice's send_command
                # doesn't natively support an "append" flag in the payload for SendHttpText,
                # sending a separate command with the same TextId might work as an "update"
                # or sending with a different TextId might be needed if they must be independent.
                # For now, using the same TextId implies an update/append operation if Pixoo supports it.
                # This part is highly dependent on specific Pixoo firmware behavior for "Draw/SendHttpText".
                # If append:1 is crucial, PixooDevice.send_command might need adjustment,
                # or a specialized version of send_text for lyrics in PixooDevice.
                # Given current PixooDevice, it just sends the payload.
                # Let's assume the same TextId for "update" behavior for the second line,
                # which is a common pattern if "append" isn't a direct flag.
                pass # Payload already set with new 'y' and same TextId (if Pixoo handles it as update)

            payloads.append(payload)
            # Max 2 lines for lyrics display area
            if i >= 1: 
                break
        
        if not payload_list and text: # If text was present but no lines generated
             _LOGGER.debug(f"Lyrics text '{text}' resulted in no displayable lines after ClearHttpText.")
        elif len(payload_list) == 1 and not text: # Only ClearHttpText, no actual lyrics
             _LOGGER.debug("No lyrics text, only clear command in payload.")
            
        return payload_list

    async def shutdown(self):
        """Clean up resources if any."""
        await self.cancel_timed_clear() # Cancel task on shutdown
        _LOGGER.debug("LyricsProvider shutdown.")
        self.lyrics_data = []
        self.last_lyrics_text = ""
