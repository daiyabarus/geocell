# Python-based Geospatial Analysis for LTE Network Visualization: An Alternative to QGIS

## Introduction

In the realm of geospatial analysis, particularly for LTE network visualization, Geographic Information System (GIS) tools like QGIS have been the go-to solution for creating gcell sites, spidergraphs, and plotting LTE signal quality. However, these tools can sometimes lack flexibility when it comes to customization and integration with other data processing workflows. This article presents a Python-based approach that offers a more flexible and programmable alternative to traditional GIS tools for visualizing and analyzing LTE network data.

We'll explore how to create a GeoApp class that handles tasks such as:
1. Loading and processing geospatial data
2. Creating interactive maps with cell sites and measurement points
3. Generating spidergraphs (polylines) to connect measurement points to cell sites
4. Implementing dynamic legends based on calculated statistics

This approach not only replaces the functionality typically achieved with QGIS but also provides greater flexibility for customization and integration with other data processing pipelines.

## Libraries and Dependencies

Before diving into the code, let's discuss the key libraries used in this project:

1. **pandas**: A powerful data manipulation library that we use for loading and processing our CSV data.
   ```python
   import pandas as pd
   ```

2. **folium**: A library that makes it easy to visualize data on an interactive leaflet map.
   ```python
   import folium
   from branca.element import MacroElement, Template
   ```

3. **geopy**: Used for geodesic distance calculations.
   ```python
   from geopy.distance import geodesic
   ```

4. **colorsys**: A module for color system conversions, used here for generating unique colors.
   ```python
   import colorsys
   ```

5. **streamlit**: A framework for creating web applications with Python, used here for the user interface.
   ```python
   import streamlit as st
   ```

6. **math**: Provides mathematical functions for calculations related to sector beams.
   ```python
   from math import asin, atan2, cos, degrees, radians, sin
   ```

These libraries collectively provide the functionality needed to replace QGIS for our specific use case of LTE network visualization.

## GeoApp Class: A Step-by-Step Breakdown

Let's break down the `GeoApp` class, explaining each method and its purpose in detail.

### Class Initialization

```python
@dataclass
class GeoApp:
    geocell_data: str | pd.DataFrame
    driveless_data: str | pd.DataFrame
    unique_cellname: list[str] = field(init=False)
    map_center: list[float] = field(init=False)
    tile_options: dict[str, str] = field(init=False)
    map: folium.Map = field(init=False, default=None)
    ci_colors: dict[str, str] = field(init=False)
    cell_edge_coordinates: dict[str, list[float]] = field(default_factory=dict)

    def __post_init__(self):
        self.geocell_data = self._load_data(self.geocell_data)
        self.driveless_data = self._load_data(self.driveless_data)
        self.unique_cellname = self._get_unique_cellname()
        self.map_center = self._calculate_map_center()
        self.tile_options = self._define_tile_options()
        self.ci_colors = self._assign_ci_colors()
```

The `GeoApp` class is defined using Python's `dataclass` decorator, which automatically generates several special methods like `__init__` and `__repr__`. The `__post_init__` method is called after the regular `__init__` to perform additional initialization steps.

### Data Loading and Processing

```python
@staticmethod
def _load_data(data: str | pd.DataFrame) -> pd.DataFrame:
    return pd.read_csv(data) if isinstance(data, str) else data

def _get_unique_cellname(self) -> list[str]:
    if "cellname" not in self.geocell_data.columns:
        raise ValueError("Column 'cellname' does not exist in geocell_data.")
    return sorted(self.geocell_data["cellname"].unique())

def _calculate_map_center(self) -> list[float]:
    return [
        self.geocell_data["Latitude"].mean(),
        self.geocell_data["Longitude"].mean(),
    ]
```

These methods handle data loading and initial processing. The `_load_data` method can accept either a file path or a pandas DataFrame, providing flexibility in data input. The `_get_unique_cellname` method extracts unique cell names, which is crucial for color assignment and legend creation. The `_calculate_map_center` method determines the center point of the map based on the average latitude and longitude of the cell sites.

### Map Initialization and Styling

```python
@staticmethod
def _define_tile_options() -> dict[str, str]:
    return {
        "Openstreetmap": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "Google Hybrid": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
    }


def _assign_ci_colors(self) -> dict[str, str]:
    return {
        ci: self._hsv_to_hex(index / len(self.unique_cellname))
        for index, ci in enumerate(self.unique_cellname)
    }


@staticmethod
def _hsv_to_hex(hue: float) -> str:
    rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    return f"#{int(rgb[0] * 255):02x}{int(rgb[1] * 255):02x}{int(rgb[2] * 255):02x}"
```

These methods set up the visual aspects of the map. The `_define_tile_options` method provides different map styles, while `_assign_ci_colors` generates unique colors for each cell using the HSV color space, converted to hex format for use in the map.

### Creating Sector Beams

```python
def _create_sector_beam(
    self, lat: float, lon: float, azimuth: float, beamwidth: float, radius: float
) -> tuple[list[list[float]], list[float]]:
    lat_rad, lon_rad, azimuth_rad = radians(lat), radians(lon), radians(azimuth)
    beamwidth_rad = radians(beamwidth)
    angle_step = beamwidth_rad / 49
    start_angle = azimuth_rad - beamwidth_rad / 2

    points = [[lat, lon]] + [
        self._calculate_point(
            lat_rad, lon_rad, start_angle + i * angle_step, radius
        )
        for i in range(50)
    ]
    points.append([lat, lon])

    edge_point = self._calculate_point(lat_rad, lon_rad, azimuth_rad, radius)
    return points, edge_point


@staticmethod
def _calculate_point(
    lat_rad: float, lon_rad: float, angle: float, radius: float
) -> list[float]:
    lat_new = asin(
        sin(lat_rad) * cos(radius / 6371)
        + cos(lat_rad) * sin(radius / 6371) * cos(angle)
    )
    lon_new = lon_rad + atan2(
        sin(angle) * sin(radius / 6371) * cos(lat_rad),
        cos(radius / 6371) - sin(lat_rad) * sin(lat_new),
    )
    return [degrees(lat_new), degrees(lon_new)]
```

These methods are responsible for creating the sector beams for each cell site. The `_create_sector_beam` method calculates a series of points that form the sector beam, while `_calculate_point` handles the complex trigonometry required to accurately place these points on the Earth's surface.

### Adding Map Layers

```python
def _add_geocell_layer(self):
    geocell_layer = folium.FeatureGroup(name="Geocell Sites")
    for row in self._iterate_rows(self.geocell_data):
        color = self.get_ci_color(row["cellname"])
        self._add_sector_beam(row, color, geocell_layer)
        self._add_site_label(row, geocell_layer)
        self._add_circle_marker(row, color, geocell_layer)
    geocell_layer.add_to(self.map)


def _add_driveless_layer(self, color_by_ci: bool = True):
    driveless_layer = folium.FeatureGroup(name="Driveless Data")
    for row in self._iterate_rows(self.driveless_data):
        color = (
            self.get_ci_color(row["cellname"])
            if color_by_ci
            else self.get_rsrp_color(row["rsrp"])
        )
        folium.CircleMarker(
            location=[row["lat_grid"], row["long_grid"]],
            radius=6,
            popup=f"Cellname: {row['cellname']}<br>RSRP: {row['rsrp']} dBm",
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=1,
        ).add_to(driveless_layer)
    driveless_layer.add_to(self.map)
```

These methods add the main layers to our map. The `_add_geocell_layer` method adds cell sites with their sector beams, while `_add_driveless_layer` adds measurement points. Both methods use color coding to represent either the cell identity or the RSRP value.

### Creating Spidergraphs

```python
def _add_spider_graph(self):
    for row in self._iterate_rows(self.driveless_data):
        point_location = (row["lat_grid"], row["long_grid"])
        distance = geodesic(self.map_center, point_location).kilometers
        if row["cellname"] in self.cell_edge_coordinates:
            edge_lat, edge_lon = self.cell_edge_coordinates[row["cellname"]]
            color = self.get_ci_color(row["cellname"])
            folium.PolyLine(
                locations=[
                    [row["lat_grid"], row["long_grid"]],
                    [edge_lat, edge_lon],
                ],
                color=color,
                weight=0.5,
                opacity=0.5,
                popup=f"Distance from Site:<br>{distance:.2f} km",
            ).add_to(self.map)
```

This method creates the spidergraph by drawing lines (polylines) from each measurement point to its corresponding cell site. It uses the `geopy.distance.geodesic` function to calculate the distance between points.

### Generating Dynamic Legends

```python
def calculate_rsrp_statistics(self) -> list[str]:
    rsrp_ranges = [
        ("-80  >= 0", lambda rsrp: rsrp >= -80, "blue"),
        ("-95  >= -80", lambda rsrp: -95 <= rsrp < -80, "#14380A"),
        ("-100 >= -95", lambda rsrp: -100 <= rsrp < -95, "#93FC7C"),
        ("-110 >= -100", lambda rsrp: -110 <= rsrp < -100, "yellow"),
        ("-110 >= -140", lambda rsrp: rsrp < -110, "red"),
    ]

    total_records = len(self.driveless_data)
    results = []

    for label, condition, color in rsrp_ranges:
        count = self.driveless_data[
            self.driveless_data["rsrp"].apply(condition)
        ].shape[0]
        percentage = (count / total_records) * 100 if total_records > 0 else 0
        results.append(
            f"<li><span style='background:  {color}; opacity: 1;'></span>{label}&emsp;{count}&emsp;{percentage:.2f}%</li>"
        )

    return results

def calculate_cellname_statistics(self) -> list[str]:
    total_records = len(self.driveless_data)
    results = []

    counts = self.driveless_data["cellname"].value_counts()

    for cellname, count in counts.items():
        percentage = (count / total_records) * 100 if total_records > 0 else 0
        color = self.get_ci_color(cellname)
        results.append(
            f"<li><span style='background: {color}; opacity: 1;'></span>{cellname}&emsp;{count}&emsp;{percentage:.2f}%</li>"
        )

    return results

def _create_legend_template(self, color_by_ci: bool) -> str:
    sitename = self.geocell_data["site"].iloc[0]
    legend_template = """
    {% macro html(this, kwargs) %}
    <div id='maplegend' class='maplegend'
        style='position: absolute; z-index:9999; background-color: rgba(192, 192, 192, 1);
        border-radius: 6px; padding: 10px; font-size: 12px; right: 12px; top: 70px;'>
    <div class='legend-scale'>
    <ul class='legend-labels'>
    """
    if color_by_ci:
        legend_template += f"<li><strong>{sitename}<br>by EUtranCell</strong></li>"
        legend_template += "".join(self.calculate_cellname_statistics())
    else:
        legend_template += f"<li><strong>{sitename}<br>by RSRP</strong></li>"
        legend_template += "".join(self.calculate_rsrp_statistics())

    legend_template += """
    </ul>
    </div>
    </div>
    <style type='text/css'>
    .maplegend .legend-scale ul {margin: 0; padding: 0; color: #0f0f0f;}
    .maplegend .legend-scale ul li {list-style: none; line-height: 18px; margin-bottom: 1.5px;}
    .maplegend ul.legend-labels li span {
        float: left;
        height: 14px;
        width: 14px;
        margin-right: 4.5px;
        border-radius: 50%;
    }
    </style>
    {% endmacro %}
    """
    return legend_template

def _add_dynamic_legend(self, color_by_ci: bool):
    legend_template = self._create_legend_template(color_by_ci)
    legend_macro = MacroElement()
    legend_macro._template = Template(legend_template)
    self.map.get_root().add_child(legend_macro)
```

These methods work together to create a dynamic legend for the map. The `calculate_rsrp_statistics` and `calculate_cellname_statistics` methods compute the statistics for RSRP ranges and cell names respectively. The `_create_legend_template` method generates an HTML template for the legend, which is then added to the map using `_add_dynamic_legend`.

## Advantages Over QGIS

This Python-based approach offers several advantages over using QGIS for LTE network visualization:

1. **Flexibility**: The code can be easily modified to accommodate different data structures or add new features. Unlike QGIS, where you're limited to the available tools and plugins, with Python you have complete control over the entire process.

2. **Automation**: The entire process from data loading to visualization can be automated, allowing for easy integration into data pipelines or scheduled reports. This is particularly useful for recurring analyses or when dealing with frequently updated data.

3. **Reproducibility**: The code provides a clear, step-by-step record of the entire analysis process. This makes it easier to reproduce results, share methodologies with colleagues, or adapt the analysis for similar projects.

4. **Customization**: Every aspect of the visualization can be customized to meet specific needs. From color schemes to the layout of the legend, you have fine-grained control over the output.

5. **Integration**: This Python-based solution can easily integrate with other data processing, machine learning, or statistical analysis libraries. This allows for more complex analyses that might be difficult or impossible to perform within QGIS alone.

6. **Version Control**: Unlike QGIS projects, this code can be easily version controlled using tools like Git, allowing for better collaboration and tracking of changes over time.

7. **Scalability**: The code can be easily scaled to handle larger datasets or multiple sites by leveraging Python's parallel processing capabilities or deploying to cloud environments.

8. **Interactive Web Integration**: By using libraries like Streamlit, the analysis can be turned into an interactive web application, allowing non-technical users to explore the data and generate visualizations.

9. **Continuous Updates**: As new Python libraries and tools become available, the code can be easily updated to incorporate these advancements, ensuring that the analysis remains current and efficient.

## Implementing the GeoApp

To use the GeoApp class, you would typically follow these steps:

1. Prepare your data files (geocell_data and driveless_data).
2. Import the necessary libraries and the GeoApp class.
3. Create an instance of the GeoApp class with your data.
4. Call the `run_geo_app()` method to generate the interactive map.

Here's a simple example of how to use the GeoApp:

```python
import os
import streamlit as st

script_dir = os.path.dirname(__file__)
sitelist_mcom = os.path.join(script_dir, "test_geocell.csv")
sitelist_driveless = os.path.join(script_dir, "test_driveless.csv")

app = GeoApp(sitelist_mcom, sitelist_driveless)
app.run_geo_app()


```

This code, when run with Streamlit (e.g., `streamlit run your_script.py`), will create an interactive web application that allows users to explore the LTE network data.

## Conclusion

This Python-based approach to LTE network visualization offers a powerful and flexible alternative to traditional GIS tools like QGIS. By leveraging libraries such as Pandas, Folium, and Streamlit, we've created a solution that not only replicates the functionality of QGIS for creating gcell sites, spidergraphs, and plotting LTE signal quality, but also enhances it with greater customization options and the ability to integrate with broader data analysis workflows.

Key benefits of this approach include:

1. **Programmability**: The entire process is codified, making it easy to modify, extend, and reuse for different datasets or similar projects.
2. **Interactivity**: The resulting visualization is interactive, allowing users to zoom, pan, and click on elements to get more information.
3. **Dynamic Updates**: The legend and statistics are generated dynamically based on the current data, ensuring that the visualization always reflects the most up-to-date information.
4. **Customizability**: Every aspect of the visualization can be tailored to specific needs, from color schemes to the layout of elements on the map.
5. **Integration**: This solution can easily be integrated into larger data processing pipelines or web applications.

While this approach requires more initial setup and programming knowledge compared to using QGIS, it offers significant advantages in terms of flexibility, reproducibility, and scalability. For teams working with LTE network data on a regular basis, investing in this type of custom solution can lead to more efficient workflows and more insightful analyses in the long run.

As with any tool, the choice between this Python-based approach and QGIS will depend on the specific needs of your project, your team's expertise, and your long-term goals for data analysis and visualization. However, for those looking to move beyond the limitations of traditional GIS tools and leverage the full power of programmatic data analysis, this approach provides a robust and extensible foundation.
