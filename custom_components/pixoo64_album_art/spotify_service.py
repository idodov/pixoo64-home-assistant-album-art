import asyncio
import base64
import io
import json
import logging
import time
from typing import TYPE_CHECKING, Any, Optional, List, Tuple # Added List, Tuple

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from PIL import Image # For type hinting if ImageProcessor methods return PIL Images

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from .config import Config
    from .pixoo import PixooDevice
    from .image import ImageProcessor
    # from .media import MediaData # Not directly used in methods shown, but good for context

_LOGGER = logging.getLogger(__name__)

class SpotifyService:
    """Handles Spotify API interactions and Spotify-specific features like album art slides."""

    BASE_SPOTIFY_URL = "https://api.spotify.com/v1"
    TOKEN_URL = "https://accounts.spotify.com/api/token"

    def __init__(self, config: "Config", hass: "HomeAssistant", image_processor: "ImageProcessor", pixoo_device: "PixooDevice"):
        """Initialize SpotifyService."""
        self.config = config
        self.hass = hass
        self.image_processor = image_processor
        self.pixoo_device = pixoo_device
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        self.spotify_data: dict = {} # To store data from get_spotify_json
        self.first_album_image_url: Optional[str] = None # For fallback
        self.artist_image_url: Optional[str] = None    # For fallback

    async def _get_access_token(self) -> Optional[str]:
        """Gets an access token from Spotify."""
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        if not self.config.spotify_client_id or not self.config.spotify_client_secret:
            _LOGGER.error("Spotify client ID or secret not configured.")
            return None

        payload = {
            "grant_type": "client_credentials",
        }
        auth_header = base64.b64encode(
            f"{self.config.spotify_client_id}:{self.config.spotify_client_secret}".encode("ascii")
        ).decode("ascii")
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        session = async_get_clientsession(self.hass)
        try:
            async with session.post(self.TOKEN_URL, headers=headers, data=payload, timeout=10) as response:
                response.raise_for_status()
                token_data = await response.json()
                self._access_token = token_data.get("access_token")
                self._token_expires_at = time.time() + token_data.get("expires_in", 3600) - 60 # 60s buffer
                _LOGGER.info("Successfully obtained Spotify access token.")
                return self._access_token
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Error getting Spotify access token: {e}")
            return None
        except Exception as e:
            _LOGGER.error(f"Unexpected error getting Spotify access token: {e}", exc_info=True)
            return None


    async def get_spotify_json(self, url: str, params: Optional[dict] = None) -> Optional[dict]:
        """Makes a GET request to the Spotify API and returns JSON response."""
        token = await self._get_access_token()
        if not token:
            return None

        headers = {"Authorization": f"Bearer {token}"}
        session = async_get_clientsession(self.hass)
        try:
            _LOGGER.debug(f"Fetching Spotify JSON from {url} with params {params}")
            async with session.get(url, headers=headers, params=params, timeout=10) as response:
                response.raise_for_status()
                data = await response.json()
                self.spotify_data = data # Store response for get_album_list
                return data
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Spotify API request error for {url}: {e}")
            return None
        except Exception as e:
            _LOGGER.error(f"Unexpected error during Spotify API request for {url}: {e}", exc_info=True)
            return None

    async def get_spotify_album_id_and_image(self, artist: str, title: str, album_name: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """Searches Spotify for a track and returns album ID and image URL."""
        _LOGGER.debug(f"Searching Spotify for album ID and image: artist='{artist}', title='{title}', album='{album_name}'")
        query = f"artist:{artist} track:{title}"
        if album_name: # Adding album improves search accuracy
            query += f" album:{album_name}"
        
        search_url = f"{self.BASE_SPOTIFY_URL}/search"
        params = {"q": query, "type": "track", "limit": 1}
        
        data = await self.get_spotify_json(search_url, params=params)
        if data and data.get("tracks", {}).get("items"):
            track_item = data["tracks"]["items"][0]
            track_item = data["tracks"]["items"][0]
            album_info = track_item.get("album", {})
            album_id = album_info.get("id")
            album_image_url = None

            if album_info.get("images"):
                # Store the first album image encountered (usually the primary one from search)
                self.first_album_image_url = album_info["images"][0]["url"]
                album_image_url = self.first_album_image_url # This is the "best match" image
                _LOGGER.info(f"Found Spotify album ID: {album_id}, Image URL: {album_image_url}")
            else:
                _LOGGER.info(f"Found Spotify album ID: {album_id}, but no images for this album.")
            
            # Attempt to get artist image
            if track_item.get("artists"):
                artist_id = track_item["artists"][0].get("id")
                if artist_id:
                    self.artist_image_url = await self.get_spotify_artist_image_url(artist_id)
                    if self.artist_image_url:
                        _LOGGER.info(f"Found Spotify artist ID: {artist_id}, Artist Image URL: {self.artist_image_url}")
                    else:
                        _LOGGER.debug(f"Found Spotify artist ID: {artist_id}, but no artist image.")
            
            return album_id, album_image_url # Return best match album ID and its image
            
        _LOGGER.warning(f"No Spotify track found for query: {query}")
        self.first_album_image_url = None # Reset if no track found
        self.artist_image_url = None    # Reset if no track found
        return None, None

    async def get_spotify_album_image_url(self, album_id: str) -> Optional[str]:
        """Gets album image URL for a given Spotify album ID."""
        if not album_id: return None
        album_url = f"{self.BASE_SPOTIFY_URL}/albums/{album_id}"
        data = await self.get_spotify_json(album_url)
        if data and data.get("images"):
            return data["images"][0]["url"] # Return largest image
        return None

    async def get_spotify_artist_image_url(self, artist_id: str) -> Optional[str]:
        """Gets artist image URL for a given Spotify artist ID."""
        if not artist_id: return None
        artist_url = f"{self.BASE_SPOTIFY_URL}/artists/{artist_id}"
        data = await self.get_spotify_json(artist_url)
        if data and data.get("images"):
            return data["images"][0]["url"]
        return None

    async def get_spotify_artist_image_url_by_name(self, artist_name: str) -> Optional[str]:
        """Searches for an artist and returns their image URL."""
        search_url = f"{self.BASE_SPOTIFY_URL}/search"
        params = {"q": f"artist:{artist_name}", "type": "artist", "limit": 1}
        data = await self.get_spotify_json(search_url, params=params)
        if data and data.get("artists", {}).get("items"):
            artist_item = data["artists"]["items"][0]
            if artist_item.get("images"):
                return artist_item["images"][0]["url"]
        return None
    
    # Methods for Spotify Album Art Slide
    # These methods are more complex and interact with ImageProcessor and PixooDevice

    def get_album_list(self) -> List[Tuple[str, str]]:
        """Processes self.spotify_data (previously fetched) to extract album names and image URLs."""
        albums = []
        if not self.spotify_data or "items" not in self.spotify_data: # Assuming spotify_data is from a user's saved albums type endpoint
            # Try to parse if it's from a search result (e.g. tracks)
            if self.spotify_data and "tracks" in self.spotify_data and "items" in self.spotify_data["tracks"]:
                 for item in self.spotify_data["tracks"]["items"]:
                    album_info = item.get("album", {})
                    if album_info.get("name") and album_info.get("images"):
                        albums.append((album_info["name"], album_info["images"][0]["url"]))
                 return albums
            _LOGGER.warning("Spotify data not found or in unexpected format for get_album_list.")
            return albums

        # Example for processing user's saved albums (adjust based on actual endpoint used)
        # This assumes self.spotify_data is from an endpoint like "/me/albums"
        for item in self.spotify_data.get("items", []):
            album_info = item.get("album", item) # If items are directly albums or nested under 'album'
            if album_info and album_info.get("name") and album_info.get("images"):
                albums.append((album_info["name"], album_info["images"][0]["url"]))
        _LOGGER.info(f"Extracted {len(albums)} albums for slide show.")
        return albums


    async def get_slide_img(self, image_url: str) -> Optional[str]:
        """Fetches an image, processes it for the slide, and returns base64 GIF."""
        if not image_url: return None
        
        # Use the stored ImageProcessor instance
        # The original AppDaemon script did:
        # img_data = await self.image_processor._fetch_image_data_from_url(image_url)
        # if img_data:
        #     img = Image.open(io.BytesIO(img_data))
        #     img = self.image_processor.ensure_rgb(img)
        #     # Specific processing for slide images (e.g. no text, different enhancements)
        #     img = self.image_processor.img_adptive(img, kernel_effect=True) # Example: apply kernel effect
        #     img = img.resize((64, 64), Image.Resampling.LANCZOS)
        #     buffered = io.BytesIO()
        #     img.save(buffered, format="GIF")
        #     return base64.b64encode(buffered.getvalue()).decode('utf-8')
        # return None
        
        # For HA, we should use the ImageProcessor's get_image method,
        # but we need to control the processing steps (e.g. no text, specific enhancements for slide).
        # This might require adding a "processing_profile" to ImageProcessor.get_image,
        # or a dedicated method in ImageProcessor for slide images.

        # Temporary simplified approach: fetch and minimal process here, then convert to base64.
        # This duplicates some ImageProcessor logic but gives control.
        # A better long-term solution is to enhance ImageProcessor.
        
        _LOGGER.debug(f"get_slide_img: Fetching URL {image_url}")
        img_data_bytes = await self.image_processor._fetch_image_data_from_url(image_url)
        if not img_data_bytes:
            _LOGGER.error(f"get_slide_img: Failed to fetch image data from {image_url}")
            return None

        try:
            # Run PIL operations in executor as they are CPU-bound
            def _process_slide_image_sync(data_bytes):
                with Image.open(io.BytesIO(data_bytes)) as img:
                    img = self.image_processor.ensure_rgb(img)
                    # Apply specific enhancements for slide if needed, e.g., from config
                    img = self.image_processor.img_adptive(
                        img,
                        kernel_effect=self.config.pixoo_kernel_effect, # Use general config for now
                        colors_enhanced=self.config.pixoo_colors_enhanced,
                        contrast=self.config.pixoo_contrast,
                        sharpness=self.config.pixoo_sharpness,
                        limit_colors_value=self.config.pixoo_limit_colors
                    )
                    img = img.resize((64, 64), Image.Resampling.LANCZOS)
                    buffered = io.BytesIO()
                    img.save(buffered, format="GIF") # Save as GIF
                    return base64.b64encode(buffered.getvalue()).decode('utf-8')

            base64_gif = await self.hass.async_add_executor_job(_process_slide_image_sync, img_data_bytes)
            return base64_gif
        except Exception as e:
            _LOGGER.error(f"Error processing slide image {image_url}: {e}", exc_info=True)
            return None


    async def send_pixoo_animation_frame(self, gif_base64_data: str, pic_id: int, total_frames: int, speed_ms: int):
        """Sends a single frame of an animation to Pixoo."""
        # This method structure assumes a command like "Device/PushDynamicImage" or similar.
        # The AppDaemon script's `send_pixoo_animation_frame` used a specific payload structure.
        payload = {
            "Command": "Device/PushDynamicImage", # Or "Draw/SendHttpGif" or similar
            "PicNum": 1, # Number of pictures in this message (usually 1 for this type of animation)
            "PicWidth": 64,
            "PicOffset": pic_id, # Frame index (0 to TotalFrames-1)
            "PicID": 0, # Animation ID, consistent for all frames of one animation
            "PicSpeed": speed_ms, # Speed for this frame or entire animation
            "PicData": gif_base64_data
        }
        # The AppDaemon script also had "TotalNum": total_frames. This might be Divoom specific.
        # If "Device/PushDynamicImage" is used, it might need TotalNum.
        # payload["TotalNum"] = total_frames # Add if required by Pixoo firmware/command

        _LOGGER.debug(f"Sending animation frame {pic_id + 1}/{total_frames} to Pixoo.")
        await self.pixoo_device.send_command(payload) # Use stored PixooDevice instance

    async def spotify_albums_slide(self):
        """Fetches user's Spotify albums and displays them as a slideshow on Pixoo."""
        if not self.config.pixoo_spotify_slide:
            _LOGGER.info("Spotify album slide is not enabled in config.")
            return

        _LOGGER.info("Starting Spotify album slide show...")
        # 1. Fetch user's saved albums (or playlists, etc.)
        # Example: Fetch user's saved albums. Requires "user-library-read" scope.
        # This scope needs user authorization, not possible with client_credentials.
        # So, this feature as implemented in AppDaemon (likely using user token)
        # cannot be directly replicated with client_credentials.
        # For client_credentials, we might fetch "new releases" or "featured playlists".
        
        # Let's assume we fetch new releases for now, as it doesn't require user scope.
        new_releases_url = f"{self.BASE_SPOTIFY_URL}/browse/new-releases"
        # This populates self.spotify_data
        await self.get_spotify_json(new_releases_url, params={"limit": 10}) # Get 10 new releases

        albums = self.get_album_list() # This now needs to parse new-releases structure
        # Adapting get_album_list for new-releases structure (if different)
        if not albums and self.spotify_data.get("albums", {}).get("items"): # Check for new-releases structure
            parsed_albums = []
            for item in self.spotify_data["albums"]["items"]:
                if item.get("name") and item.get("images"):
                    parsed_albums.append((item["name"], item["images"][0]["url"]))
            albums = parsed_albums
            _LOGGER.info(f"Fetched {len(albums)} new releases for slide show.")


        if not albums:
            _LOGGER.warning("No albums found for Spotify slide show.")
            return

        # Animation parameters
        animation_id = random.randint(1, 1000) # Unique ID for this animation sequence
        frame_duration_ms = 3000 # 3 seconds per album cover

        for i, (name, url) in enumerate(albums):
            _LOGGER.info(f"Slide show: Displaying '{name}' ({i+1}/{len(albums)})")
            
            # Inform user on Pixoo display (optional)
            # await self.pixoo_device.send_text(f"{name[:15]}...", x=0, y=0, font=2, color=(200,200,200))
            
            base64_gif = await self.get_slide_img(url)
            if base64_gif:
                # The "Device/PlayTFGif" command in PixooDevice.display_gif might be simpler
                # if we want to show one GIF at a time without explicit animation sequence commands.
                # The AppDaemon script's spotify_albums_slide implies a sequence.
                # If using PushDynamicImage for sequence:
                # await self.send_pixoo_animation_frame(base64_gif, pic_id=i, total_frames=len(albums), speed_ms=frame_duration_ms)
                
                # Simpler: just display each GIF using the existing display_gif method.
                # This won't be a smooth "animation" in the Divoom sense but a sequence of images.
                await self.pixoo_device.display_gif(base64_gif, speed=frame_duration_ms)

                await asyncio.sleep(frame_duration_ms / 1000.0) # Wait for the duration of the slide
            else:
                _LOGGER.warning(f"Could not get/process image for '{name}' from {url}")

        _LOGGER.info("Spotify album slide show finished.")

    async def spotify_album_art_animation(self, image_url: str):
        """Creates a simple animation (e.g., zoom) from a single album art image."""
        # This is a more advanced feature.
        # 1. Fetch the image.
        # 2. Create multiple frames (e.g., slightly zoomed, panned).
        # 3. Send each frame.
        _LOGGER.warning("spotify_album_art_animation is not fully implemented yet.")
        # Example:
        # base64_gif = await self.get_slide_img(image_url) # Get initial image
        # if base64_gif:
        #     # Create variations (frames) of this image using PIL if needed, or use a multi-frame GIF.
        #     # For simplicity, let's assume we just display the static image for now.
        #     await self.pixoo_device.display_gif(base64_gif)
        pass

    async def shutdown(self):
        """Clean up resources if any."""
        _LOGGER.debug("SpotifyService shutdown.")
        # No explicit resources to clean for this implementation (token is in memory, session managed by HA).
        pass
