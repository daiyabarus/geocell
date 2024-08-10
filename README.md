# GeoApp

## Overview

This tutorial will guide you through creating a geospatial visualization app called `GeoApp`. The app is designed to visualize geospatial data, including cellular coverage and signal strength, using Python libraries such as Folium, Pandas, and Streamlit.

## Libraries in Use

1. **colorsys**
   The `colorsys` module provides functions to convert colors between different color systems, such as RGB and HSV. In this app, it's used to generate color codes in the HSV space, which are then converted to hexadecimal format for consistent color mapping.

2. **math**
   The `math` module is used for mathematical functions like trigonometry, which are essential for calculating angles, coordinates, and distances when creating sector beams and other map features.

3. **folium**
   `folium` is a powerful Python library used for creating interactive maps. It allows easy integration of different map tiles, markers, and layers. In this app, Folium is used to render maps, add markers for cell sites, and draw polygons representing sector beams.

4. **pandas**
   `pandas` is a data manipulation library that provides data structures and functions needed to work with structured data, particularly tabular data. In `GeoApp`, it is used to load and process geospatial data from CSV files or DataFrames.

5. **streamlit**
   `streamlit` is a framework for creating web apps directly from Python scripts. It simplifies the process of adding interactivity and UI elements to data-driven applications. In this project, Streamlit is used to build the front-end interface, allowing users to interact with the map and select various visualization options.

6. **branca.element**
   `branca` is a Python library that works with Folium to create complex map elements like legends, popups, and more. The `MacroElement` and `Template` classes from `branca.element` are used in this app to create dynamic legends that change based on the data being visualized.

## Map Tile Options

The `GeoApp` includes a method called `define_tile_options` that defines the different map tile options available for use in the application. Map tiles are the images or layers that make up the visual representation of the map background. The app provides two tile options:

### 1. **OpenStreetMap**
   - **URL:** `https://tile.openstreetmap.org/{z}/{x}/{y}.png`
   - **Description:** OpenStreetMap (OSM) is a free, editable map of the world, created and maintained by a community of mappers. It's known for its high quality and up-to-date geographical data. The OSM tile option provides a standard street map view, which is suitable for a wide range of geospatial visualization tasks. It's open-source and doesn't require any API keys or usage restrictions.

### 2. **Google Hybrid**
   - **URL:** `https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}`
   - **Description:** The Google Hybrid tile combines both satellite imagery and road data, giving a comprehensive view that includes both natural features and man-made infrastructure. This tile is useful for visualizations where both geographical context and infrastructure details are important. The Google Hybrid tile provides a rich and detailed map view, but it typically requires API access and may have usage limits depending on the terms of service.

### How the Tiles are Defined

The `define_tile_options` method is a static method within the `GeoApp` class. It returns a dictionary where the keys are the names of the tile options (e.g., "OpenStreetmap" and "Google Hybrid"), and the values are the corresponding URL templates that Folium uses to fetch the map tiles.

Here's the method in the code:

```python
@staticmethod
def define_tile_options() -> dict[str, str]:
    """
    Define map tile options.
    """
    return {
        "Openstreetmap": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "Google Hybrid": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
    }
```

## Color Conversion: `hsv_to_hex` Method

In the `GeoApp`, the `hsv_to_hex` method is responsible for converting colors from the HSV (Hue, Saturation, Value) color space to the HEX color format, which is widely used in web development and visualization tools like Folium.

### What is HSV?

The HSV color model represents colors in terms of:
- **Hue (H):** The type of color, represented as a degree on the color wheel (0° to 360°). For example, 0° is red, 120° is green, and 240° is blue.
- **Saturation (S):** The intensity or purity of the color, ranging from 0 (completely desaturated, grayscale) to 1 (fully saturated).
- **Value (V):** The brightness of the color, ranging from 0 (completely dark) to 1 (maximum brightness).

### The Conversion Formula

The `hsv_to_hex` method converts HSV values to their corresponding RGB (Red, Green, Blue) values, and then formats these RGB values into a HEX string. Here's how it works:

1. **Convert HSV to RGB:**
   - The `colorsys.hsv_to_rgb` function is used for this conversion.
   - The function takes in three parameters: `hue`, `saturation`, and `value`, and returns a tuple of RGB values, each ranging from 0 to 1.

2. **Convert RGB to HEX:**
   - Each RGB value is multiplied by 255 to convert it to the standard 8-bit range (0 to 255).
   - The values are then formatted as a hexadecimal string using Python's string formatting capabilities.

### Implementation in the Code

Here's how the `hsv_to_hex` method is implemented:

```python
@staticmethod
def hsv_to_hex(hue: float) -> str:
    """
    Convert an HSV color to its hexadecimal string representation.
    """
    rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    return f"#{int(rgb[0] * 255):02x}{int(rgb[1] * 255):02x}{int(rgb[2] * 255):02x}"
```

How It Works
Input: The method takes in a hue value as a float, typically between 0 and 1. This hue value represents the position on the color wheel and is divided by the number of unique colors (i.e., unique cell names) to evenly distribute colors across the spectrum.

Processing:

The method calls colorsys.hsv_to_rgb(hue, 1.0, 1.0) to convert the HSV value to an RGB tuple.
The RGB values, each originally in the range [0, 1], are scaled to [0, 255] by multiplying by 255.
Output: The method then returns the corresponding HEX color code as a string. For example, a hue of 0.5 (green) would yield a HEX value of #00ff00.

Usage in GeoApp
This method is used in the assign_ci_colors method to generate distinct colors for each unique cell ID (CI) in the dataset. These colors are then used to visualize different cell sectors on the map, ensuring that each sector is easily distinguishable.

Example of Usage
If you call hsv_to_hex(0.5), it will return #00ff00, which corresponds to a fully saturated and bright green color in HEX format.

This explanation covers what the `hsv_to_hex` method does, the formula and process involved in converting HSV to HEX, and how this is implemented and used within the `GeoApp`.
