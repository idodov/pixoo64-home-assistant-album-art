import asyncio
import base64
import io
import json
import logging
import random
import time
from typing import TYPE_CHECKING, Any, Optional

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from PIL import Image, ImageDraw, ImageFont
from .helpers import get_font # Added

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from .config import Config
    from .image import ImageProcessor
    from .pixoo import PixooDevice
    from .media import MediaData
    from .spotify_service import SpotifyService # Import the actual SpotifyService

_LOGGER = logging.getLogger(__name__)

# Placeholder SpotifyService class removed

class FallbackService:
    """
    Handles finding fallback images from various online sources if no local/direct image is available.
    Also handles generating simple images like black screens or TV icons.
    """

    def __init__(self, config: "Config", hass: "HomeAssistant", image_processor: "ImageProcessor", pixoo_device: "PixooDevice"):
        self.config = config
        self.hass = hass
        self.image_processor = image_processor
        self.pixoo_device = pixoo_device
        # Instantiate the real SpotifyService, passing all required dependencies
        self.spotify_service = SpotifyService(config, hass, image_processor, pixoo_device)

    async def _make_request(self, url: str, method: str = "GET", headers: Optional[dict] = None, params: Optional[dict] = None, data: Optional[Any] = None, is_json: bool = False) -> Optional[Any]:
        """Makes an HTTP request using HA's client session."""
        session = async_get_clientsession(self.hass)
        try:
            _LOGGER.debug(f"Making {method} request to {url} with params: {params}, data: {data}, headers: {headers}")
            async with session.request(method, url, headers=headers, params=params, json=data if is_json else None, data=data if not is_json else None, timeout=10) as response:
                response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                if 'application/json' in response.headers.get('Content-Type', ''):
                    return await response.json()
                else:
                    return await response.text() # Or response.read() for binary data
        except aiohttp.ClientError as e:
            _LOGGER.error(f"HTTP request error for {url}: {e}")
            return None
        except asyncio.TimeoutError:
            _LOGGER.error(f"Timeout during HTTP request to {url}")
            return None
        except Exception as e:
            _LOGGER.error(f"Unexpected error during HTTP request to {url}: {e}")
            return None

    async def get_spotify_album_image_url(self, media_data: "MediaData") -> Optional[str]:
        """Gets album image URL from Spotify."""
        if not self.config.spotify_client_id or not self.config.spotify_client_secret:
            _LOGGER.debug("Spotify API credentials not configured.")
            return None
        if not media_data.artist or not media_data.title:
            _LOGGER.debug("Missing artist or title for Spotify search.")
            return None

        # Use the get_spotify_album_id_and_image method from the real SpotifyService
        album_id, album_image_url = await self.spotify_service.get_spotify_album_id_and_image(
            media_data.artist, media_data.title, media_data.album
        )
        if album_image_url: # If image URL is directly returned by combined search
            return album_image_url 
        # If only album_id was found, then try to get image using album_id
        # (This logic is now mostly inside get_spotify_album_id_and_image, this is a fallback if that changes)
        # if album_id: 
        #     return await self.spotify_service.get_spotify_album_image_url(album_id)
        return None # If neither found directly

    async def get_lastfm_album_image_url(self, media_data: "MediaData") -> Optional[str]:
        """Gets album image URL from Last.fm."""
        if not self.config.lastfm_api_key:
            _LOGGER.debug("Last.fm API key not configured.")
            return None
        if not media_data.artist or not media_data.album: # Last.fm usually needs album name
            _LOGGER.debug("Missing artist or album for Last.fm search.")
            return None

        url = "http://ws.audioscrobbler.com/2.0/"
        params = {
            "method": "album.getinfo",
            "api_key": self.config.lastfm_api_key,
            "artist": media_data.artist,
            "album": media_data.album,
            "format": "json"
        }
        response_data = await self._make_request(url, params=params)
        if response_data and isinstance(response_data, dict) and "album" in response_data and response_data["album"] and "image" in response_data["album"]:
            images = response_data["album"]["image"]
            # Find largest image (extralarge or mega)
            for size in ["mega", "extralarge", "large", "medium"]:
                for img_info in images:
                    if img_info["size"] == size and img_info["#text"]:
                        return img_info["#text"]
        _LOGGER.debug(f"Last.fm: No image found for {media_data.artist} - {media_data.album}")
        return None

    async def get_discogs_album_image_url(self, media_data: "MediaData") -> Optional[str]:
        """Gets album image URL from Discogs."""
        if not self.config.discogs_api_token:
            _LOGGER.debug("Discogs API token not configured.")
            return None
        if not media_data.artist or not media_data.album:
            _LOGGER.debug("Missing artist or album for Discogs search.")
            return None

        base_url = "https://api.discogs.com/database/search"
        headers = {"Authorization": f"Discogs token={self.config.discogs_api_token}"}
        params = {
            "type": "release", # Search for releases (albums)
            "artist": media_data.artist,
            "release_title": media_data.album, # Specific to album title
            "format": "album"
        }
        response_data = await self._make_request(base_url, headers=headers, params=params)
        if response_data and isinstance(response_data, dict) and "results" in response_data and response_data["results"]:
            # Prioritize results with cover_image and where title closely matches
            for result in response_data["results"]:
                if result.get("cover_image"):
                    # Further validation can be added here if needed (e.g., title matching)
                    return result["cover_image"]
        _LOGGER.debug(f"Discogs: No image found for {media_data.artist} - {media_data.album}")
        return None

    async def get_musicbrainz_album_image_url(self, media_data: "MediaData") -> Optional[str]:
        """Gets album image URL from MusicBrainz (via Cover Art Archive)."""
        if not self.config.musicbrainz_enabled:
            _LOGGER.debug("MusicBrainz integration is not enabled.")
            return None
        if not media_data.artist or not media_data.album:
            _LOGGER.debug("Missing artist or album for MusicBrainz search.")
            return None

        # 1. Search for release group ID by artist and album name
        search_url = "https://musicbrainz.org/ws/2/release-group"
        headers = {"Accept": "application/json", "User-Agent": "Pixoo64AlbumArtDisplay/0.1.0 ( https://github.com/idodov/pixoo64-home-assistant-album-art )"}
        # Query construction for MusicBrainz can be complex. Using a simplified one.
        query = f'artist:"{media_data.artist}" AND releasegroup:"{media_data.album}"'
        params = {"query": query, "fmt": "json", "limit": "1"}

        release_group_data = await self._make_request(search_url, headers=headers, params=params)
        if release_group_data and isinstance(release_group_data, dict) and "release-groups" in release_group_data and release_group_data["release-groups"]:
            rgid = release_group_data["release-groups"][0].get("id")
            if rgid:
                # 2. Fetch cover art from Cover Art Archive
                cover_art_url = f"https://coverartarchive.org/release-group/{rgid}"
                cover_data = await self._make_request(cover_art_url, headers={"Accept": "application/json"}) # No User-Agent needed for CAA
                if cover_data and isinstance(cover_data, dict) and "images" in cover_data and cover_data["images"]:
                    # Find front image, prefer large or original
                    for image in cover_data["images"]:
                        if image.get("front") and image.get("image"):
                            return image["image"] # This is usually the full-size image
        _LOGGER.debug(f"MusicBrainz/CAA: No image found for {media_data.artist} - {media_data.album}")
        return None

    async def get_tidal_album_image_url(self, media_data: "MediaData") -> Optional[str]:
        """Gets album image URL from TIDAL (Placeholder - TIDAL API is complex)."""
        if not self.config.tidal_client_id or not self.config.tidal_client_secret:
            _LOGGER.debug("TIDAL API credentials not configured.")
            return None
        _LOGGER.warning("TIDAL fallback is not fully implemented yet due to API complexity.")
        # Actual TIDAL integration would require OAuth and more complex calls.
        # For now, this is a placeholder.
        return None


    async def get_ai_pollinations_image_url(self, media_data: "MediaData") -> Optional[str]:
        """Generates an image URL using an AI image generation service (e.g., Pollinations)."""
        if not media_data.ai_prompt:
            _LOGGER.debug("No AI prompt available in media_data.")
            return None

        # Using Pollinations as an example, as in the AppDaemon script.
        # The prompt should be URL-encoded.
        # model_choice = "turbo" if self.config.ai_fallback_model == "turbo" else "flux" # Example based on config
        # Pollinations API can change, this is a general structure.
        # The URL structure from the AppDaemon script:
        # pollinations_url = f"https://image.pollinations.ai/prompt/{prompt}?model={model_choice}&width=512&height=512&nologo=true"
        # However, directly using this as an image URL for Pixoo might not work if Pixoo needs a direct image link.
        # Pollinations might return an HTML page or a redirect.
        # For now, let's assume it returns a direct image or we can fetch it.

        prompt = media_data.ai_prompt
        _LOGGER.info(f"Attempting AI image generation with prompt: {prompt}")

        # This is a placeholder for the actual Pollinations (or other AI service) call.
        # A real implementation would POST to an API endpoint and get an image URL or data.
        # The AppDaemon script seems to construct a GET URL that directly serves/redirects to an image.
        # Let's simulate that.
        # Note: Pollinations' direct URL scheme might change or have rate limits.
        # For a robust solution, using their official API if available is better.
        
        # Example: if Pollinations returns a page, you might need to scrape it or use a proper API.
        # If it returns a direct image URL (e.g. via redirect), then it's simpler.
        # The example from AppDaemon used a direct GET URL.
        # For this adaptation, we will assume the constructed URL is a direct link to an image.
        # No actual HTTP call here, as it's about constructing the URL for Pixoo to fetch,
        # or for ImageProcessor to fetch.
        
        # Based on the AppDaemon script's structure for Pollinations:
        # It seems it was constructing a URL that, when hit, would generate and return the image.
        # The `image_processor.get_image` will then fetch this URL.
        
        # This method should return a URL that `image_processor.get_image` can consume.
        # Example Pollinations URL structure (may vary):
        # https://pollinations.ai/p/{prompt_url_encoded}?model={model}&width={width}&height={height}
        # The AppDaemon used: `https://image.pollinations.ai/prompt/{prompt_url_encoded}?model=...`
        
        # For now, let's assume the config holds the base URL or we hardcode it.
        # This part is highly dependent on the chosen AI service and its API.
        # The key is that this function should return a *URL* to an image.
        
        # Let's use a simplified placeholder URL structure for Pollinations.
        # The actual generation is handled when this URL is fetched.
        from urllib.parse import quote
        encoded_prompt = quote(prompt)
        model = self.config.ai_fallback_model if self.config.ai_fallback_model in ["turbo", "flux"] else "turbo"
        # This URL must eventually resolve to an image.
        ai_image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model={model}&width=64&height=64&nologo=true"
        _LOGGER.info(f"Constructed AI image URL (Pollinations): {ai_image_url}")
        return ai_image_url


    def create_black_screen_image(self) -> Image.Image:
        """Creates a 64x64 black PIL Image."""
        return Image.new("RGB", (64, 64), "black")

    def create_tv_icon_image(self) -> Image.Image:
        """Creates a 64x64 PIL Image with a TV icon."""
        # This is a simplified version. A real icon would be loaded from a file or drawn more elaborately.
        img = Image.new("RGB", (64, 64), "black")
        draw = ImageDraw.Draw(img)
        # Simple TV shape
        draw.rectangle([10, 15, 54, 50], outline="white", width=2) # Screen
        draw.line([20, 50, 20, 55], fill="white", width=2) # Leg 1
        draw.line([44, 50, 44, 55], fill="white", width=2) # Leg 2
        font = get_font("DejaVuSans.ttf", 10) # Use helper
        draw.text((25, 25), "TV", font=font, fill="white")
        return img

    async def send_info(self, text: str, color: tuple = (100, 100, 100), font: int = 2, position: tuple = (0,56)):
        """Helper to send text to Pixoo display, similar to AppDaemon's send_info."""
        # This method should use self.pixoo_device.send_text or a similar command.
        # The AppDaemon script's send_info had more complex formatting.
        # For now, map to pixoo_device.send_text or a generic command.
        # Example: map to the send_text method in PixooDevice
        # payload = {
        #     "Command": "Draw/SendHttpText",
        #     "TextId": random.randint(1, 10000), # Random ID for text
        #     "x": position[0],
        #     "y": position[1],
        #     "dir": 0, # 0 for RTL, 1 for LTR (this might be text direction, not scroll)
        #     "font": font,
        #     "TextWidth": 64, # Assume full width
        #     "speed": 10, # Example speed
        #     "TextString": text,
        #     "color": "#{:02x}{:02x}{:02x}".format(color[0], color[1], color[2])
        # }
        # await self.pixoo_device.send_command(payload)
        _LOGGER.debug(f"FallbackService.send_info called with text: {text}. Using pixoo_device.send_text.")
        await self.pixoo_device.send_text(text, x=position[0], y=position[1], color=color, font=font, width=64, speed=10)


    async def send_info_img(self, image: Image.Image):
        """Helper to send a PIL Image to Pixoo, similar to AppDaemon's send_info_img."""
        # 1. Convert PIL Image to base64 GIF
        buffered = io.BytesIO()
        image.save(buffered, format="GIF") # Pixoo typically takes GIFs
        gif_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # 2. Send using pixoo_device.display_gif or similar command
        # payload = {
        #     "Command": "Device/PushDynamicImage", # Or the relevant command for static GIFs
        #     "PicNum": 1,
        #     "PicSpeed": 100, # Adjust as needed
        #     "PicData": gif_base64
        # }
        # await self.pixoo_device.send_command(payload)
        _LOGGER.debug("FallbackService.send_info_img called. Using pixoo_device.display_gif.")
        await self.pixoo_device.display_gif(gif_base64)


    async def get_final_url(self, media_data: "MediaData") -> Optional[str]:
        """
        Tries to get an image URL from various sources based on media type and configuration.
        This is the main logic method for this class.
        Returns a URL string that ImageProcessor can handle, or None.
        """
        _LOGGER.info(f"get_final_url called for: {media_data.title} by {media_data.artist}")
        final_image_url = None

        # 0. Direct URL from media_data if available (e.g., entity_picture)
        if media_data.cover_url and not self.config.force_ai:
            _LOGGER.info(f"Using direct cover_url: {media_data.cover_url}")
            final_image_url = media_data.cover_url
            # Check if this direct URL is actually accessible by ImageProcessor
            # No, ImageProcessor will handle fetching this.

        # Fallback sequence if no direct URL or if AI is forced for testing
        if not final_image_url or self.config.force_ai:
            _LOGGER.info("Attempting fallback image sources.")
            await self.send_info("Searching...") # Inform user on Pixoo

            # Fallback Order: Spotify -> Discogs -> Last.fm -> TIDAL -> MusicBrainz -> Spotify Artist/First Album -> AI
            
            # 1. Spotify (Primary Album Match)
            if media_data.current_mode == "Music" and not final_image_url:
                if self.config.spotify_client_id and self.config.spotify_client_secret:
                    _LOGGER.info("Trying Spotify (Primary Album) fallback...")
                    # get_spotify_album_image_url now primarily returns the best match from track search
                    final_image_url = await self.get_spotify_album_image_url(media_data)
                    if final_image_url: 
                        _LOGGER.info(f"Spotify (Primary Album) fallback found: {final_image_url}")
                        media_data.pic_source = "Spotify (Album)" # Example of setting pic_source if MediaData supports it

            # 2. Discogs
            if not final_image_url and media_data.current_mode == "Music" and self.config.discogs_api_token:
                _LOGGER.info("Trying Discogs fallback...")
                final_image_url = await self.get_discogs_album_image_url(media_data)
                if final_image_url: 
                    _LOGGER.info(f"Discogs fallback found: {final_image_url}")
                    media_data.pic_source = "Discogs"

            # 3. Last.fm
            if not final_image_url and media_data.current_mode == "Music" and self.config.lastfm_api_key:
                _LOGGER.info("Trying Last.fm fallback...")
                final_image_url = await self.get_lastfm_album_image_url(media_data)
                if final_image_url: 
                    _LOGGER.info(f"Last.fm fallback found: {final_image_url}")
                    media_data.pic_source = "Last.fm"
            
            # 4. TIDAL (Placeholder)
            if not final_image_url and media_data.current_mode == "Music" and self.config.tidal_client_id and self.config.tidal_client_secret:
                _LOGGER.info("Trying TIDAL fallback (placeholder)...")
                final_image_url = await self.get_tidal_album_image_url(media_data)
                if final_image_url: 
                    _LOGGER.info(f"TIDAL fallback found: {final_image_url}")
                    media_data.pic_source = "TIDAL"

            # 5. MusicBrainz/Cover Art Archive
            if not final_image_url and media_data.current_mode == "Music" and self.config.musicbrainz_enabled:
                _LOGGER.info("Trying MusicBrainz/CAA fallback...")
                final_image_url = await self.get_musicbrainz_album_image_url(media_data)
                if final_image_url: 
                    _LOGGER.info(f"MusicBrainz/CAA fallback found: {final_image_url}")
                    media_data.pic_source = "MusicBrainz/CAA"

            # 6. Spotify Artist Image (if available from initial Spotify search)
            if not final_image_url and media_data.current_mode == "Music" and self.spotify_service.artist_image_url:
                _LOGGER.info("Trying Spotify Artist Image fallback...")
                final_image_url = self.spotify_service.artist_image_url
                _LOGGER.info(f"Spotify Artist Image fallback found: {final_image_url}")
                media_data.pic_source = "Spotify (Artist)"

            # 7. Spotify First Album Match Image (if available from initial Spotify search)
            if not final_image_url and media_data.current_mode == "Music" and self.spotify_service.first_album_image_url:
                _LOGGER.info("Trying Spotify First Album Match fallback...")
                final_image_url = self.spotify_service.first_album_image_url
                _LOGGER.info(f"Spotify First Album Match fallback found: {final_image_url}")
                media_data.pic_source = "Spotify (First Album Match)"


            # 8. AI Image Generation (if no image found yet or forced_ai)
            if self.config.force_ai or (not final_image_url and media_data.ai_prompt):
                _LOGGER.info("Trying AI image generation fallback...")
                await self.send_info("AI Image...")
                final_image_url = await self.get_ai_pollinations_image_url(media_data) # This returns a URL
                if final_image_url:
                     _LOGGER.info(f"AI image URL generated: {final_image_url}")
                else:
                    _LOGGER.warning("AI image generation failed to produce a URL.")
                    await self.send_info("AI Fail :(")

        # If still no URL, handle specific fallbacks (TV icon, black screen)
        if not final_image_url:
            if media_data.current_mode == "TV" and self.config.pixoo_tv_icon_enabled:
                _LOGGER.info("No image found, using TV icon.")
                await self.send_info("TV Icon") # Inform user
                tv_icon_pil_image = self.create_tv_icon_image()
                # ImageProcessor expects a URL. We need to either save this locally and get a URL,
                # or have ImageProcessor accept PIL images, or send it directly here.
                # For now, let's send it directly via send_info_img (which uses pixoo_device)
                # This bypasses ImageProcessor's main get_image -> process -> base64 flow for this specific case.
                await self.send_info_img(tv_icon_pil_image)
                return "fallback_tv_icon_sent" # Special string indicating direct send
            elif self.config.pixoo_info_fallback: # If enabled, show info text on black screen
                _LOGGER.info("No image found, using info text on black screen fallback.")
                await self.send_info_img(self.create_black_screen_image()) # Send black screen first
                info_text = media_data.media_title_cleaned or media_data.title or "No Media Info"
                if media_data.artist and media_data.artist not in info_text: info_text = f"{media_data.artist} - {info_text}"
                await self.send_info(info_text)
                return "fallback_info_text_sent" # Special string
            else:
                _LOGGER.info("No image found and no specific fallbacks, sending black screen.")
                await self.send_info_img(self.create_black_screen_image())
                return "fallback_black_screen_sent" # Special string

        if final_image_url:
            _LOGGER.info(f"Final image URL to be processed: {final_image_url}")
            await self.send_info("Loading...") # Inform user on Pixoo
        
        return final_image_url

    async def shutdown(self):
        """Clean up resources if any were held by FallbackService itself."""
        _LOGGER.debug("FallbackService shutdown.")
        # If SpotifyService or others held resources (like own sessions), close them here.
        # For the placeholder SpotifyService, nothing to do.
        pass
