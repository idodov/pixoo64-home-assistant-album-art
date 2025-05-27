import asyncio
import base64
import io
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Optional, Tuple, Union, List
import hashlib

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import get_url 
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from .config import Config
from .helpers import (add_text_to_image_pil, ensure_rgb, get_bidi,
                      get_font, has_bidi, img_adptive, split_string, get_ha_font_path,
                      hex_to_rgb_list, rgb_to_hex) # Added rgb_to_hex

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from .media import MediaData 

_LOGGER = logging.getLogger(__name__)

class ImageProcessor:
    """Handles fetching and processing images for display on the Pixoo64."""

    def __init__(self, hass: "HomeAssistant", config: Config):
        self.hass = hass
        self.config = config
        self._executor = ThreadPoolExecutor(max_workers=3) 
        self._image_cache = {} 
        self._font_cache = {} 

    async def _fetch_image_data_from_url(self, url: str) -> Optional[bytes]:
        session = async_get_clientsession(self.hass)
        try:
            if url.startswith("/local/"):
                filepath = self.hass.config.path("www", url[len("/local/"):])
                _LOGGER.debug(f"Fetching local image from filesystem path: {filepath}")
                if os.path.exists(filepath):
                    return await self.hass.async_add_executor_job(self._read_local_file, filepath)
                else:
                    _LOGGER.error(f"Local file not found at resolved path: {filepath}")
                    return None
            elif url.startswith('/') and not url.startswith('//'): 
                absolute_url = f"{get_url(self.hass, prefer_internal=True).rstrip('/')}{url}"
                _LOGGER.debug(f"Fetching HA-internal image from absolute URL: {absolute_url}")
                async with session.get(absolute_url) as response:
                    response.raise_for_status()
                    return await response.read()
            elif url.startswith("http://") or url.startswith("https://"): 
                _LOGGER.debug(f"Fetching image from external URL: {url}")
                async with session.get(url) as response:
                    response.raise_for_status() 
                    return await response.read()
            else: 
                _LOGGER.debug(f"Attempting to load image from local file path (last resort): {url}")
                if os.path.exists(url):
                    return await self.hass.async_add_executor_job(self._read_local_file, url)
                else:
                    _LOGGER.error(f"URL/path not recognized or file not found: {url}")
                    return None
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Network error fetching image {url}: {e}")
            return None
        except FileNotFoundError:
            _LOGGER.error(f"File not found when trying to load image: {url}")
            return None
        except Exception as e:
            _LOGGER.error(f"Unexpected error fetching image {url}: {e}")
            return None

    def _read_local_file(self, filepath: str) -> Optional[bytes]:
        try:
            with open(filepath, "rb") as f:
                return f.read()
        except Exception as e:
            _LOGGER.error(f"Error reading local file {filepath}: {e}")
            return None

    def special_mode_render(self, img: Image.Image) -> Image.Image:
        """Renders the image in 'special mode' with gradient background."""
        output_size = (64, 64)
        
        # Determine album_size based on whether text (clock/temp) will be shown in special mode
        # This mirrors the AppDaemon logic where text implies smaller album art.
        # self.config.pixoo_show_text_enabled is for the ItemList text, not burned-in on image.
        # For special mode, text is usually shown via ItemList, not burned.
        # The original script's special_mode_text was for ItemList.
        # So, album_size depends on whether clock or temp are enabled, as they take space.
        if self.config.pixoo_show_clock or self.config.pixoo_temperature_enabled:
             album_size = (34, 34)
        else:
             album_size = (56, 56)

        img_resized = img.resize(album_size, Image.Resampling.LANCZOS)

        # Background color logic
        if album_size == (34, 34): # Text enabled, use black background for gradient
            bg_color = (0, 0, 0)
            # Get edge colors from the *original* image for gradient
            left_edge_color = img.getpixel((0, img.height // 2))[:3]
            right_edge_color = img.getpixel((img.width - 1, img.height // 2))[:3]
        else: # No text, derive background from edge colors
            left_edge_color = img.getpixel((0, img.height // 2))[:3]
            right_edge_color = img.getpixel((img.width - 1, img.height // 2))[:3]
            # Average the edge colors for a solid dark background
            # Or, use a more sophisticated approach if desired. For now, simple average.
            avg_edge_r = (left_edge_color[0] + right_edge_color[0]) // 2
            avg_edge_g = (left_edge_color[1] + right_edge_color[1]) // 2
            avg_edge_b = (left_edge_color[2] + right_edge_color[2]) // 2
            # Make it darker
            bg_color = (avg_edge_r // 3, avg_edge_g // 3, avg_edge_b // 3)
        
        background = Image.new('RGB', output_size, bg_color)
        draw = ImageDraw.Draw(background)

        # Paste position
        paste_x = (output_size[0] - album_size[0]) // 2
        paste_y = 8 # Top padding

        if album_size == (34, 34): # Draw gradients if text mode
            gradient_width = (output_size[0] - album_size[0]) // 2 - 2 # Width of each gradient area
            
            # Left gradient (edge color to background color)
            for x in range(gradient_width):
                ratio = x / gradient_width
                r = int(left_edge_color[0] * (1 - ratio) + bg_color[0] * ratio)
                g = int(left_edge_color[1] * (1 - ratio) + bg_color[1] * ratio)
                b = int(left_edge_color[2] * (1 - ratio) + bg_color[2] * ratio)
                draw.line([(x, paste_y), (x, paste_y + album_size[1] -1)], fill=(r,g,b))

            # Right gradient (background color to edge color)
            for x in range(gradient_width):
                ratio = x / gradient_width
                r = int(bg_color[0] * (1 - ratio) + right_edge_color[0] * ratio)
                g = int(bg_color[1] * (1 - ratio) + right_edge_color[1] * ratio)
                b = int(bg_color[2] * (1 - ratio) + right_edge_color[2] * ratio)
                draw.line([(paste_x + album_size[0] + x + 2, paste_y), (paste_x + album_size[0] + x + 2, paste_y + album_size[1] -1)], fill=(r,g,b))
        
        background.paste(img_resized, (paste_x, paste_y))
        _LOGGER.debug(f"Special mode image rendered: album_size={album_size}, bg_color={bg_color}")
        return background


    def _process_image_data(self, image_data: bytes, media_data: "MediaData", is_cover: bool) -> Optional[dict]:
        try:
            with Image.open(io.BytesIO(image_data)) as img_original:
                img = ensure_rgb(img_original)

                img_enhanced = img_adptive(
                    img.copy() if (self.config.pixoo_crop_borders_enabled and is_cover) or (self.config.pixoo_special_mode and is_cover) else img,
                    kernel_effect=self.config.pixoo_kernel_effect,
                    colors_enhanced=self.config.pixoo_colors_enhanced,
                    contrast=self.config.pixoo_contrast,
                    sharpness=self.config.pixoo_sharpness,
                    limit_colors_value=self.config.pixoo_limit_colors
                )

                # Apply special mode rendering if enabled (replaces img_enhanced)
                if self.config.pixoo_special_mode and is_cover:
                    _LOGGER.debug("Applying special mode rendering.")
                    img_enhanced = self.special_mode_render(img_enhanced) 
                    # special_mode_render returns a 64x64 image, so further cropping/resizing might not be needed
                    # or needs to be conditional. For now, assume it's the final composed image.
                    img_final_for_display = img_enhanced # It's already 64x64
                else:
                    # Standard processing: Crop and Resize
                    if self.config.pixoo_crop_borders_enabled and is_cover:
                        width, height = img_enhanced.size
                        base_border_percent = 0.05 
                        border = min(int(width * base_border_percent), int(height * base_border_percent))
                        if self.config.pixoo_crop_borders_extra:
                            border += 5 
                        border = min(border, (width // 2) -1, (height // 2) -1) 
                        if border < 0: border = 0
                        if border > 0 and (width - 2 * border > 0 and height - 2 * border > 0) :
                            _LOGGER.debug(f"Cropping image: original size=({width}x{height}), border={border}")
                            img_enhanced = img_enhanced.crop((border, border, width - border, height - border))
                        else:
                            _LOGGER.debug(f"Skipping crop for image size {width}x{height} with border {border}")
                    
                    img_final_for_display = img_enhanced.resize((64, 64), Image.Resampling.LANCZOS)
                
                img_for_colors = img_final_for_display.copy()
                avg_color = img_for_colors.resize((1, 1)).getpixel((0, 0))
                background_color_rgb = avg_color[:3]
                brightness = sum(background_color_rgb) / 3
                text_font_color_tuple = (0, 0, 0) if brightness > 128 else (255, 255, 255)

                try:
                    quantized_img = img_for_colors.quantize(colors=5, method=Image.Quantize.FASTOCTREE)
                    palette = quantized_img.getpalette()
                    distinct_colors_rgb = []
                    temp_palette_rgb = []
                    for i in range(0, len(palette), 3):
                        color = tuple(palette[i:i+3])
                        if color not in [(0,0,0), (255,255,255)] and color not in distinct_colors_rgb:
                             temp_palette_rgb.append(color)
                        if len(temp_palette_rgb) >= 3: break
                    if len(temp_palette_rgb) < 3 and len(distinct_colors_rgb) == 0 :
                         for i in range(0, len(palette), 3):
                            color = tuple(palette[i:i+3])
                            if color not in distinct_colors_rgb:
                                temp_palette_rgb.append(color)
                            if len(temp_palette_rgb) >=3: break
                    distinct_colors_rgb = temp_palette_rgb[:3]
                    color1_rgb = distinct_colors_rgb[0] if len(distinct_colors_rgb) > 0 else background_color_rgb
                    color2_rgb = distinct_colors_rgb[1] if len(distinct_colors_rgb) > 1 else color1_rgb
                    color3_rgb = distinct_colors_rgb[2] if len(distinct_colors_rgb) > 2 else color2_rgb
                except Exception as e:
                    _LOGGER.warning(f"Color quantization failed: {e}. Using average color for WLED colors.")
                    color1_rgb = color2_rgb = color3_rgb = background_color_rgb
                
                # Convert WLED colors to hex
                color1_hex = rgb_to_hex(color1_rgb)
                color2_hex = rgb_to_hex(color2_rgb)
                color3_hex = rgb_to_hex(color3_rgb)

                # "Burned" text logic - only if NOT in special mode and pixoo_burned is true
                if self.config.pixoo_burned and not (self.config.pixoo_special_mode and is_cover) and is_cover:
                    title = media_data.get("title", "")
                    artist = media_data.get("artist", "")
                    text_to_display = f"{title} - {artist}" if title and artist else title or artist
                    if self.config.pixoo_text_clean_title:
                        text_to_display = re.sub(r'\s*\[.*?\]|\s*\(.*?\)', '', text_to_display).strip()
                    if text_to_display:
                        if has_bidi(text_to_display):
                            text_to_display = get_bidi(text_to_display)
                        
                        final_text_color_for_drawing = text_font_color_tuple 
                        if self.config.pixoo_text_actual_force_font_color:
                            try:
                                final_text_color_for_drawing = tuple(int(self.config.pixoo_text_actual_force_font_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                            except ValueError:
                                _LOGGER.warning(f"Invalid format for pixoo_text_actual_force_font_color: '{self.config.pixoo_text_actual_force_font_color}'.")
                        
                        bg_color_val = (0,0,0) if self.config.pixoo_text_background_enabled else None
                        
                        img_final_for_display = add_text_to_image_pil(
                            image=img_final_for_display, text=text_to_display,
                            font_name=get_ha_font_path("arial.ttf"), font_size=8, 
                            font_color=final_text_color_for_drawing, position=(2, 56), 
                            max_width=60, bg_color=bg_color_val,
                            bg_opacity=0.6 if bg_color_val else 0, align="center"
                        )

                buffered = io.BytesIO()
                img_final_for_display.save(buffered, format="GIF", save_all=True, duration=100, loop=0, optimize=False)
                base64_gif = base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                return {
                    "base64_gif": base64_gif,
                    "font_color": text_font_color_tuple, # Auto-detected text color as tuple
                    "background_color_rgb": background_color_rgb, # as tuple
                    "color1": color1_hex, # as hex string
                    "color2": color2_hex, # as hex string
                    "color3": color3_hex, # as hex string
                    "brightness": int(brightness) 
                }
        except Exception as e:
            _LOGGER.error(f"Error processing image: {e}", exc_info=True)
            return None

    async def get_image(self, media_data: "MediaData", image_url: Optional[str], is_cover: bool = True) -> Optional[dict]:
        if not image_url:
            _LOGGER.debug("No image URL provided.")
            return None

        config_tuple = (
            self.config.pixoo_kernel_effect, self.config.pixoo_colors_enhanced,
            self.config.pixoo_contrast, self.config.pixoo_sharpness, self.config.pixoo_limit_colors,
            self.config.pixoo_crop_borders_enabled, self.config.pixoo_crop_borders_extra,
            # Burned text settings
            self.config.pixoo_burned, # Changed from pixoo_show_text_enabled
            self.config.pixoo_text_clean_title, 
            self.config.pixoo_text_actual_force_font_color, # Use resolved color for cache key
            self.config.pixoo_text_background_enabled,
            # Special mode
            self.config.pixoo_special_mode,
            # For special mode, album_size depends on clock/temp display, so include those config options
            self.config.pixoo_show_clock, 
            self.config.pixoo_temperature_enabled,
            is_cover 
        )
        text_parts = ""
        # Only include text in cache key if burned text is active
        if self.config.pixoo_burned and is_cover:
            title = media_data.get("title", "")
            artist = media_data.get("artist", "")
            text_parts = f"{title}-{artist}"

        key_material = f"{image_url}{config_tuple}{text_parts}"
        cache_key = hashlib.md5(key_material.encode()).hexdigest()

        if cache_key in self._image_cache:
            _LOGGER.debug(f"Returning cached image data for URL: {image_url} and key: {cache_key}")
            return self._image_cache[cache_key]

        image_data_bytes = await self._fetch_image_data_from_url(image_url)
        if not image_data_bytes:
            return None

        processed_image_dict = await self.hass.async_add_executor_job(
            self._process_image_data, image_data_bytes, media_data, is_cover
        )

        if processed_image_dict:
            if len(self._image_cache) >= self.config.pixoo_images_cache_size:
                self._image_cache.pop(next(iter(self._image_cache))) 
            self._image_cache[cache_key] = processed_image_dict
            _LOGGER.debug(f"Cached new image data for URL: {image_url} with key: {cache_key}")

        return processed_image_dict

    def clear_cache(self):
        self._image_cache.clear()
        _LOGGER.info("Image cache cleared.")

    async def shutdown(self):
        _LOGGER.debug("Shutting down ImageProcessor's ThreadPoolExecutor.")
        self._executor.shutdown(wait=True)

    async def create_text_image(
        self,
        text_lines: list[str],
        font_name: str = "arial.ttf", 
        font_size: int = 10,
        font_color: Union[str, Tuple[int, int, int]] = "black",
        bg_color: Union[str, Tuple[int, int, int]] = "white",
        image_width: int = 64,
        image_height: int = 64,
        align: str = "center"
    ) -> Optional[str]:
        try:
            base64_gif = await self.hass.async_add_executor_job(
                self._generate_text_image_sync,
                text_lines, font_name, font_size, font_color, bg_color, image_width, image_height, align
            )
            return base64_gif
        except Exception as e:
            _LOGGER.error(f"Error creating text image: {e}", exc_info=True)
            return None

    def _generate_text_image_sync(
        self,
        text_lines: list[str],
        font_name: str,
        font_size: int,
        font_color_input: Union[str, Tuple[int, int, int]],
        bg_color_input: Union[str, Tuple[int, int, int]],
        image_width: int,
        image_height: int,
        align: str
    ) -> Optional[str]:
        font = get_font(font_name, font_size) 

        if isinstance(font_color_input, str):
            try:
                font_color = tuple(int(font_color_input.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            except ValueError:
                _LOGGER.warning(f"Invalid font_color string: {font_color_input}. Defaulting to black.")
                font_color = (0,0,0)
        else:
            font_color = font_color_input

        if isinstance(bg_color_input, str):
            try:
                bg_color = tuple(int(bg_color_input.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            except ValueError:
                _LOGGER.warning(f"Invalid bg_color string: {bg_color_input}. Defaulting to white.")
                bg_color = (255,255,255)
        else:
            bg_color = bg_color_input

        img = Image.new("RGB", (image_width, image_height), color=bg_color)
        draw = ImageDraw.Draw(img)

        total_text_height = 0
        line_heights = []
        for line in text_lines:
            ascent, descent = font.getmetrics()
            text_h = ascent + descent
            line_heights.append(text_h)
            total_text_height += text_h
        
        if len(text_lines) > 1:
            total_text_height += (len(text_lines) -1) * (font_size // 4) 

        y_start = (image_height - total_text_height) // 2
        current_y = y_start
        for i, line in enumerate(text_lines):
            bbox = font.getbbox(line)
            text_width = bbox[2] - bbox[0]
            x_pos = (image_width - text_width) // 2 
            if align == "left":
                x_pos = 2 
            elif align == "right":
                x_pos = image_width - text_width - 2 
            
            draw.text((x_pos, current_y), line, font=font, fill=font_color)
            current_y += line_heights[i] + (font_size // 4 if i < len(text_lines) -1 else 0)

        buffered = io.BytesIO()
        img.save(buffered, format="GIF")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
