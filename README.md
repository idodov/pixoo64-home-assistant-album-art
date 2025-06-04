# Pixoo64 Album Art Display

## Introduction

This Home Assistant custom component displays currently playing album art (or other media visuals) from a selected media player entity onto a Divoom Pixoo64 Wi-Fi pixel display. It offers several fallback mechanisms for artwork, lyrics display, and synchronization with Home Assistant lights and WLED devices based on album art colors.

## Features

*   Displays currently playing album art on your Divoom Pixoo64.
*   Compatible with various media player entities within Home Assistant.
*   Artwork Fallbacks: Fetches artwork from multiple sources if the media player doesn't provide it directly, including:
    *   Spotify API
    *   MusicBrainz (Cover Art Archive)
    *   Last.fm API
    *   Discogs API
    *   TIDAL API (currently placeholder, API keys can be configured)
    *   AI-based image generation (via Pollinations.ai) as a final fallback.
*   Lyrics Display: Shows synchronized lyrics on the Pixoo64 (from textyl.co).
*   Light Synchronization:
    *   Controls Home Assistant light entities, matching colors and brightness to the album art.
    *   Integrates with WLED devices, synchronizing colors, brightness, and effects.
*   Configurable Display:
    *   UI-based options for display modes (e.g., show clock, specific info).
    *   UI-based options for image cropping.
*   Easy Setup: Fully configurable through the Home Assistant UI (Integrations panel).

## Prerequisites

*   A running Home Assistant instance.
*   A Divoom Pixoo64 device, connected to your local network.
*   Network connectivity allowing Home Assistant to reach the Pixoo64 device (i.e., on the same network, no firewall blocking).
*   **Optional API Keys:** For enhanced artwork and metadata fetching, you may need API keys for:
    *   Spotify (Client ID and Client Secret)
    *   Last.fm (API Key)
    *   Discogs (API Token)
    *   TIDAL (Client ID and Client Secret - Note: TIDAL fallback is currently a placeholder)
    These can be added during setup or later via the integration's "Configure" option.

## Installation

### Recommended: Installation via HACS (Home Assistant Community Store)

1.  **Ensure HACS is Installed:** If you don't have HACS installed, follow the [official HACS installation guide](https://hacs.xyz/docs/setup/download).
2.  **Add Custom Repository:**
    *   In Home Assistant, navigate to **HACS** -> **Integrations**.
    *   Click the three dots (⋮) in the top right corner and select **Custom repositories**.
    *   In the "Repository" field, enter: `https://github.com/idodov/pixoo64-home-assistant-album-art`
    *   In the "Category" field, select **Integration**.
    *   Click **ADD**.
3.  **Install Integration:**
    *   The "Pixoo64 Album Art Display" integration should now appear in your HACS integrations list (you might need to search for it).
    *   Click on it and then click **INSTALL**. Select the latest version.
4.  **Restart Home Assistant:**
    *   After installation, restart your Home Assistant instance to allow it to detect the new component.

### Manual Installation (Alternative)

1.  **Download Files:**
    *   Download the `pixoo64_album_art` directory from the `custom_components` folder of this repository.
    *   Alternatively, download the latest release ZIP file and extract the `custom_components/pixoo64_album_art` directory.
2.  **Copy to Home Assistant:**
    *   Copy the entire `pixoo64_album_art` directory into your Home Assistant's `<config_directory>/custom_components/` directory. If the `custom_components` directory doesn't exist, create it.
    *   The final path should look like: `<config_directory>/custom_components/pixoo64_album_art/`.
3.  **Restart Home Assistant:**
    *   Restart your Home Assistant instance.

## Configuration

1.  Navigate to **Configuration** -> **Devices & Services** in your Home Assistant UI.
2.  Click the **+ ADD INTEGRATION** button in the bottom right.
3.  Search for "**Pixoo64 Album Art Display**".
4.  Click on the integration to start the setup process and follow the on-screen instructions.

You will be asked for initial configuration options, including:
*   **Pixoo64 IP Address:** (Required) The local IP address of your Pixoo64 device.
*   **Media Player Entity:** (Required) The Home Assistant entity ID of the media player you want to monitor (e.g., `media_player.spotify_username`).
*   **Optional API Keys:** Fields for Spotify, Last.fm, Discogs, and TIDAL API credentials.

Many more detailed options can be configured after the initial setup.

## Usage

Once configured, the integration will automatically monitor the selected media player. When the media player's state changes (e.g., starts playing, changes track), the Pixoo64 display will update accordingly.

The integration creates the following entities in Home Assistant, which you can use in automations or display in your Lovelace dashboard:

*   **`sensor.pixoo64_album_art_status_[entry_title]`**:
    *   Shows the current status (e.g., "Artist - Title", "Paused", "Idle").
    *   Provides detailed attributes about the currently playing media, fetched metadata, and image processing status.
*   **`input_select.pixoo64_display_mode_[entry_title]`**:
    *   Allows you to manually select different display modes for the Pixoo64 (e.g., "Music", "Clock", "Album Art Only"). The availability and behavior of these modes depend on the ongoing development and specific settings.
*   **`input_select.pixoo64_crop_mode_[entry_title]`**:
    *   Allows you to change how images are cropped before being displayed (e.g., "Default", "No Crop", "Crop", "Extra Crop").
*   **`input_number.pixoo64_lyrics_sync_offset_[entry_title]`**:
    *   Allows you to adjust the timing of displayed lyrics in **seconds** (e.g., from -10s to +10s, with a step of 1s) if they appear out of sync. A positive value makes lyrics appear later, a negative value sooner. `0s` is the default if automatically determined, or when no offset is needed.
*   **`switch.pixoo64_album_art_script_enabled_[entry_title]`**:
    *   Toggles the main functionality of the script. If turned off, album art and other display updates will stop. This switch entity is only created if enabled in the integration's configuration options.
*   **`switch.pixoo64_album_art_full_control_[entry_title]`**:
    *   Allows you to dynamically toggle the "full control" behavior. When "full control" is on, the integration actively manages the Pixoo64 display (e.g., clearing the screen when the media player stops). When off, it's less assertive. The initial state is set by the corresponding option in the integration's configuration.

*(Replace `[entry_title]` with the title you gave the integration during setup, e.g., "living_room" resulting in `sensor.pixoo64_album_art_status_living_room`)*

## Advanced Configuration / Options

After the initial setup, you can access more detailed configuration options by:
1.  Navigating to **Configuration** -> **Devices & Services**.
2.  Finding the "Pixoo64 Album Art Display" integration card.
3.  Clicking on **CONFIGURE**.

This will open an options flow where you can fine-tune settings related to:
*   Pixoo device parameters (brightness, contrast, color enhancement).
*   **Home Assistant Light Entities (`light_entity`)**: Select one or more Home Assistant light entities to synchronize with the album art colors. The brightness and color of these lights will be adjusted based on the currently displayed image.
*   **External Temperature Sensor Entity (`temperature_sensor_entity`)**: Optionally, select a temperature sensor entity from your Home Assistant setup. If configured and temperature display is enabled on the Pixoo64, this sensor's value (e.g., "23°C") will be displayed. If no entity is selected here but temperature display is enabled, the Pixoo64's internal temperature reading will be used.
*   Text display on the album art (font, color, background).
*   **WLED IP Address(es) (`wled_ip`)**: Enter the IP address of your WLED device. To control multiple WLED devices, enter their IP addresses separated by commas (e.g., `192.168.1.100, 192.168.1.101`). Other WLED settings include effects and brightness.
*   **Enable Script Toggle Switch**: Determines if the `switch.pixoo64_album_art_script_enabled` entity is created, allowing you to turn the integration's main script on or off from the Home Assistant UI. Defaults to enabled.
*   Fallback service behavior (enable/disable specific providers, AI model choice).
*   And many other operational parameters.

### Text Color Options

Customize the color of text (artist/title, clock, temperature) overlaid on the album art.

*   **Font Color Preset**: Choose a predefined color for the text. Select "Automatic" for the system to pick a contrasting color, or "Custom" to specify your own hex color below.
*   **Custom Font Color**: If you selected "Custom" in the preset menu, enter your desired hex color code here (e.g., `#FFFFFF` for white, `#FF0000` for red). This will override the preset if a valid hex color is entered.

## Troubleshooting

*   **Check Home Assistant Logs:** If you encounter issues, the first step is to check the Home Assistant logs (Configuration -> Settings -> Logs). Look for any error messages related to `custom_components.pixoo64_album_art`.
*   **Pixoo64 Connectivity:**
    *   Ensure the IP address configured for your Pixoo64 is correct and static (e.g., set a DHCP reservation in your router).
    *   Verify that your Home Assistant instance can reach the Pixoo64 device over your local network (e.g., try pinging the Pixoo64 IP from a device on the same network as HA).
*   **API Keys:** If artwork fallbacks or Spotify features are not working as expected, double-check that the relevant API keys are correctly entered in the integration's configuration.
*   **Media Player Entity:** Ensure the selected media player entity is providing metadata (title, artist, album art URL). Some media players might have limited information.

## Contributing

Contributions to this project are welcome! If you have ideas for improvements, find a bug, or want to add new features, please:
1.  Open an issue on the GitHub repository to discuss the change.
2.  Submit a pull request with your proposed changes.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
