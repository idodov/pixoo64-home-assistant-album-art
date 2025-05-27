import re
import logging
from bidi.algorithm import get_display
from unidecode import unidecode
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

_LOGGER = logging.getLogger(__name__)

def ensure_rgb(image):
    """Ensure the image is in RGB format."""
    if image.mode == "RGBA":
        # Create a white background image
        bg = Image.new("RGB", image.size, (255, 255, 255))
        # Paste the RGBA image onto the white background
        bg.paste(image, (0, 0), image)
        return bg
    elif image.mode == "P": # Palette mode
        # Convert to RGBA first to preserve transparency if any, then to RGB
        image = image.convert("RGBA")
        bg = Image.new("RGB", image.size, (255, 255, 255))
        bg.paste(image, (0, 0), image)
        return bg
    elif image.mode != "RGB":
        return image.convert("RGB")
    return image

def hex_to_rgb_list(hex_string: Optional[str]) -> List[int]:
    """Converts a hex color string (e.g., "#RRGGBB") to a list of integers [R, G, B]."""
    if not hex_string or not hex_string.startswith("#"):
        return [0, 0, 0]  # Default to black for None or invalid start
    hex_color = hex_string.lstrip("#")
    if len(hex_color) == 6:
        try:
            return [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
        except ValueError:
            return [0,0,0] # Default for invalid hex characters
    elif len(hex_color) == 3:  # Short hex format #RGB
        try:
            return [int(c*2, 16) for c in hex_color]
        except ValueError:
            return [0,0,0] # Default for invalid hex characters
    return [0, 0, 0]  # Default for invalid length

def rgb_to_hex(rgb_tuple: Tuple[int, int, int]) -> str:
    """Converts an RGB tuple to a hex color string (e.g., "#RRGGBB")."""
    if not isinstance(rgb_tuple, tuple) or len(rgb_tuple) != 3:
        _LOGGER.warning(f"Invalid RGB tuple: {rgb_tuple}. Defaulting to black.")
        return "#000000"
    try:
        return "#{:02x}{:02x}{:02x}".format(
            max(0, min(rgb_tuple[0], 255)),
            max(0, min(rgb_tuple[1], 255)),
            max(0, min(rgb_tuple[2], 255))
        )
    except Exception as e:
        _LOGGER.error(f"Error converting RGB {rgb_tuple} to hex: {e}. Defaulting to black.")
        return "#000000"

def img_adptive(img: Image.Image, kernel_effect: bool = False, colors_enhanced: bool = False, contrast: bool = False, sharpness: bool = False, limit_colors_value=None) -> Image.Image:
    """Apply various image enhancements."""
    if kernel_effect:
        img = img.filter(ImageFilter.Kernel((3, 3), (-1, -1, -1, -1, 9, -1, -1, -1, -1), 1, 0))
    if colors_enhanced:
        img = ImageEnhance.Color(img).enhance(1.2) # Enhance colors by 20%
    if contrast:
        img = ImageEnhance.Contrast(img).enhance(1.2) # Enhance contrast by 20%
    if sharpness:
        img = ImageEnhance.Sharpness(img).enhance(1.2) # Enhance sharpness by 20%

    if limit_colors_value is not False and limit_colors_value is not None:
        if isinstance(limit_colors_value, int) and limit_colors_value > 0:
            _LOGGER.debug(f"Limiting colors to {limit_colors_value}")
            img = img.quantize(colors=limit_colors_value)
        else: # Default to 256 if not a valid number
            img = img.quantize(colors=256)
    return img

def split_string(text: str, max_length: int, font_size: int, font_path: str = "arial.ttf") -> list[str]:
    """Split a string into multiple lines based on max_length and font metrics."""
    lines = []
    words = text.split(' ')
    current_line = ""

    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        _LOGGER.warning(f"Font not found at {font_path}, using default PIL font for text splitting.")
        try:
            font = ImageFont.load_default()
        except Exception: # Fallback to a very basic estimation if all fails
            _LOGGER.error("Could not load any font for text splitting. Splitting will be very approximate.")
            # Basic estimation: average char width is roughly font_size / 2
            avg_char_width = font_size / 2
            if avg_char_width == 0: avg_char_width = 1 # Avoid division by zero
            chars_per_line = int(max_length / avg_char_width)
            if chars_per_line == 0: chars_per_line = 1
            
            current_line_char_count = 0
            for word in words:
                if current_line_char_count + len(word) + (1 if current_line else 0) <= chars_per_line:
                    current_line += (" " if current_line else "") + word
                    current_line_char_count += len(word) + (1 if current_line else 0)
                else:
                    lines.append(current_line)
                    current_line = word
                    current_line_char_count = len(word)
            if current_line:
                lines.append(current_line)
            return lines


    for word in words:
        # Check if the word itself is too long
        if font.getlength(word) > max_length:
            if current_line: # Add current line before splitting the long word
                lines.append(current_line)
                current_line = ""
            # Split the long word
            temp_word = ""
            for char in word:
                if font.getlength(temp_word + char) <= max_length:
                    temp_word += char
                else:
                    lines.append(temp_word)
                    temp_word = char
            if temp_word: # Add remaining part of the split word
                current_line = temp_word # Start new line with it
        elif font.getlength(current_line + (" " if current_line else "") + word) <= max_length:
            current_line += (" " if current_line else "") + word
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


def get_bidi(text: str, base_dir: str = 'L') -> str:
    """Apply bidi algorithm to text."""
    try:
        return get_display(text, base_dir=base_dir)
    except Exception as e:
        _LOGGER.warning(f"Bidi processing failed: {e}. Returning original text.")
        return text

def has_bidi(text: str) -> bool:
    """Check if text contains any RTL characters."""
    if not text:
        return False
    # Regex for RTL characters (Hebrew, Arabic, Persian, etc.)
    rtl_pattern = re.compile(r'[\u0590-\u05FF\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFF]')
    return bool(rtl_pattern.search(text))

def clean_filename(filename: str) -> str:
    """Clean a string to be suitable for use as a filename."""
    cleaned = unidecode(filename) # Transliterate non-ASCII characters
    cleaned = re.sub(r'[^\w\s-]', '', cleaned) # Remove remaining non-alphanumeric characters (except spaces and hyphens)
    cleaned = re.sub(r'[-\s]+', '-', cleaned).strip('-') # Replace spaces/hyphens with a single hyphen
    return cleaned

def format_memory_size(size_bytes: int) -> str:
    """Formats a size in bytes to a human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.2f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes/1024**2:.2f} MB"
    else:
        return f"{size_bytes/1024**3:.2f} GB"

# Placeholder for font path resolution - this will need to be adapted for HA
def get_font_path(font_name_or_path: str) -> str:
    """
    Resolves font name or path.
    In HA, fonts might need to be bundled or accessed via hass.config.path.
    For now, assume font_name_or_path is either a full path or a common font name.
    """
    common_fonts = {
        "arial": "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf", # Example path
        "default": "DejaVuSans.ttf" # Pillow's default if accessible
    }
    if font_name_or_path.lower() in common_fonts:
        return common_fonts[font_name_or_path.lower()]
    # If it's a path (e.g., ends with .ttf or .otf), use it directly
    if font_name_or_path.lower().endswith((".ttf", ".otf")):
        return font_name_or_path
    # Fallback or further logic needed here for HA environment
    _LOGGER.warning(f"Cannot resolve font: {font_name_or_path}. Using Pillow default.")
    return "arial.ttf" # Fallback to a name that split_string might try

def get_ha_font_path(font_name: str = "arial.ttf"):
    """
    Attempts to find a font. In a real HA component, you'd bundle fonts
    or ensure they are available in the execution environment.
    This is a placeholder.
    """
    # Example: Check common system font paths or a bundled path
    # common_paths = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf"]
    # for path in common_paths:
    #     if os.path.exists(path):
    #         return path
    # For now, just return the name, assuming Pillow might find it or it's a bundled name.
    if font_name.lower() == "default": # special case for Pillow's internal default
        return "ImageFont.load_default()" # Not a path, but an indicator
    return font_name # e.g. "arial.ttf"

def get_font(font_name_or_path: str, font_size: int) -> ImageFont.FreeTypeFont:
    """Loads a font using Pillow."""
    try:
        if font_name_or_path == "ImageFont.load_default()":
             return ImageFont.load_default()
        actual_path = get_ha_font_path(font_name_or_path) # Use the (placeholder) resolver
        return ImageFont.truetype(actual_path, font_size)
    except IOError:
        _LOGGER.warning(f"Font '{font_name_or_path}' (resolved to '{actual_path}') not found. Using Pillow default font.")
        return ImageFont.load_default()
    except Exception as e:
        _LOGGER.error(f"Error loading font {font_name_or_path}: {e}. Using Pillow default.")
        return ImageFont.load_default()

def add_text_to_image_pil(
    image: Image.Image,
    text: str,
    font_name: str = "arial.ttf",
    font_size: int = 10,
    font_color: str | tuple = "black", # hex string or tuple (R,G,B)
    position: tuple = (0, 0), # (x,y)
    max_width: int = None, # for text wrapping
    bg_color: str | tuple = None, # For background rectangle
    bg_opacity: float = 0.5, # 0.0 (transparent) to 1.0 (opaque)
    align: str = "left" # "left", "center", "right"
):
    """
    Adds text to a Pillow image with optional wrapping and background.
    Returns the modified image.
    """
    draw = ImageDraw.Draw(image, "RGBA" if bg_color and bg_opacity < 1.0 else "RGB")
    font = get_font(font_name, font_size)

    if isinstance(font_color, str):
        try:
            final_font_color = tuple(int(font_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        except ValueError:
            _LOGGER.warning(f"Invalid hex color string: {font_color}. Defaulting to black.")
            final_font_color = (0,0,0)
    else:
        final_font_color = font_color


    lines = [text]
    if max_width:
        lines = split_string(text, max_width, font_size, font_path=get_ha_font_path(font_name))

    line_height = font.getbbox("A")[3] - font.getbbox("A")[1] # Approximate line height
    y_text = position[1]

    for i, line in enumerate(lines):
        # Calculate text width for alignment
        bbox = font.getbbox(line)
        text_width = bbox[2] - bbox[0]
        
        x_text = position[0]
        if align == "center":
            x_text = position[0] + (max_width - text_width) / 2 if max_width else position[0] - text_width / 2
        elif align == "right":
            x_text = position[0] + (max_width - text_width) if max_width else position[0] - text_width
        
        current_pos = (x_text, y_text + i * line_height)

        if bg_color:
            if isinstance(bg_color, str):
                try:
                    final_bg_color = tuple(int(bg_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                except ValueError:
                    _LOGGER.warning(f"Invalid hex bg_color string: {bg_color}. Not drawing background.")
                    final_bg_color = None
            else:
                final_bg_color = bg_color

            if final_bg_color:
                bg_draw_color = final_bg_color + (int(255 * bg_opacity),) if len(final_bg_color) == 3 else final_bg_color
                
                # Get text bounding box for more precise background
                # We need to use textbbox for drawing, not getbbox for metrics
                text_bbox = draw.textbbox(current_pos, line, font=font)
                
                # Add some padding to the background box if desired
                padding = 2 
                bg_box = (text_bbox[0] - padding, text_bbox[1] - padding, 
                          text_bbox[2] + padding, text_bbox[3] + padding)

                # Create a temporary drawing surface for transparency if needed
                if bg_opacity < 1.0:
                    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
                    overlay_draw = ImageDraw.Draw(overlay)
                    overlay_draw.rectangle(bg_box, fill=bg_draw_color)
                    image = Image.alpha_composite(image.convert("RGBA"), overlay)
                    draw = ImageDraw.Draw(image) # Re-acquire draw object on the composited image
                else:
                    draw.rectangle(bg_box, fill=bg_draw_color)


        draw.text(current_pos, line, font=font, fill=final_font_color)

    return image
