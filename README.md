# geocell
Geographic Visualization of a Cellular Networks with Point Coordinates Using Streamlit


Tutorial: Visualizing Geo-Spatial Data with Python
This tutorial demonstrates how to visualize geo-spatial data using Python. We will cover:

Libraries needed for the project.
How to create a sector beam and describe the formula.
How to find the cell edge and describe the formula.
How to create a Folium map with rectangle points.
How to create a spider graph from point to point.
How to assign colors using the HSV color space.
How to create a legend on the map with HTML code.
1. Libraries Used
The following libraries are used in this project:

colorsys: Provides utilities to convert colors between different color systems.
math: Provides mathematical functions like trigonometric functions.
folium: A Python library used to generate interactive maps.
pandas: A data manipulation and analysis library.
streamlit: A framework to create interactive web apps with Python.
branca: A library that provides utilities for web mapping.
python
Copy code
import colorsys
from math import asin, atan2, cos, degrees, radians, sin
import folium
import pandas as pd
import streamlit as st
from branca.element import MacroElement, Template
2. Creating a Sector Beam
Description:
A sector beam represents a specific directional area in which signals from a cell tower are transmitted. The beam's coverage is determined by parameters like azimuth, beamwidth, and radius.

Formula:
To calculate the points that form the sector beam, the following formulas are used:

Latitude Calculation:

lat_new
=
arcsin
⁡
(
sin
⁡
(
lat_rad
)
⋅
cos
⁡
(
radius
/
6371
)
+
cos
⁡
(
lat_rad
)
⋅
sin
⁡
(
radius
/
6371
)
⋅
cos
⁡
(
angle
)
)
lat_new=arcsin(sin(lat_rad)⋅cos(radius/6371)+cos(lat_rad)⋅sin(radius/6371)⋅cos(angle))
Longitude Calculation:

lon_new
=
lon_rad
+
arctan
⁡
2
(
sin
⁡
(
angle
)
⋅
sin
⁡
(
radius
/
6371
)
⋅
cos
⁡
(
lat_rad
)
,
cos
⁡
(
radius
/
6371
)
−
sin
⁡
(
lat_rad
)
⋅
sin
⁡
(
lat_new
)
)
lon_new=lon_rad+arctan2(sin(angle)⋅sin(radius/6371)⋅cos(lat_rad),cos(radius/6371)−sin(lat_rad)⋅sin(lat_new))
Implementation:
python
Copy code
def create_sector_polygon(lat, lon, azimuth, beamwidth, radius):
    lat_rad, lon_rad, azimuth_rad = radians(lat), radians(lon), radians(azimuth)
    beamwidth_rad = radians(beamwidth)
    angle_step = beamwidth_rad / 49  # 50 points
    start_angle = azimuth_rad - beamwidth_rad / 2

    points = [[lat, lon]]  # Start from the given lat, lon
    points.extend(
        [
            calculate_point(lat_rad, lon_rad, start_angle + i * angle_step, radius)
            for i in range(50)
        ]
    )
    points.append([lat, lon])  # Close the polygon back to the start point

    return points
3. Finding the Cell Edge
Description:
The edge of the cell's coverage is crucial for understanding the boundary where the signal strength begins to weaken.

Formula:
To find the center point at the edge of the beam:

Latitude Calculation:

lat_new
=
arcsin
⁡
(
sin
⁡
(
lat_rad
)
⋅
cos
⁡
(
radius
/
6371
)
+
cos
⁡
(
lat_rad
)
⋅
sin
⁡
(
radius
/
6371
)
⋅
cos
⁡
(
angle
)
)
lat_new=arcsin(sin(lat_rad)⋅cos(radius/6371)+cos(lat_rad)⋅sin(radius/6371)⋅cos(angle))
Longitude Calculation:

lon_new
=
lon_rad
+
arctan
⁡
2
(
sin
⁡
(
angle
)
⋅
sin
⁡
(
radius
/
6371
)
⋅
cos
⁡
(
lat_rad
)
,
cos
⁡
(
radius
/
6371
)
−
sin
⁡
(
lat_rad
)
⋅
sin
⁡
(
lat_new
)
)
lon_new=lon_rad+arctan2(sin(angle)⋅sin(radius/6371)⋅cos(lat_rad),cos(radius/6371)−sin(lat_rad)⋅sin(lat_new))
Implementation:
python
Copy code
def find_edge_beam_center(lat, lon, azimuth, radius):
    return calculate_point(radians(lat), radians(lon), radians(azimuth), radius)
4. Creating a Folium Map with Rectangle Points
Description:
A Folium map can be used to visualize the geospatial data by drawing rectangles, polygons, markers, and other shapes.

Implementation:
python
Copy code
def calculate_rectangle_bounds(lat, lon, size=0.000165):
    return [[lat - size, lon - size], [lat + size, lon + size]]
python
Copy code
def add_driveless_layer(self, color_by_ci=True):
    driveless_layer = folium.FeatureGroup(name="Driveless Data")

    for _, row in self.driveless_data.iterrows():
        color = (
            self.get_ci_color(row["cellname"])
            if color_by_ci
            else self.get_rsrp_color(row["rsrp_mean"])
        )
        bounds = calculate_rectangle_bounds(row["lat_grid"], row["long_grid"])

        folium.Rectangle(
            bounds=bounds,
            popup=f"CI: {row['cellname']} RSRP: {row['rsrp_mean']} dBm",
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=1,
        ).add_to(driveless_layer)

    driveless_layer.add_to(self.map)
5. Creating a Spider Graph from Point to Point
Description:
A spider graph connects the edge points of cells with other points of interest, such as driveless data points, showing the relationship between them.

Implementation:
python
Copy code
def add_spider_graph(self):
    for _, row in self.driveless_data.iterrows():
        if row["cellname"] in self.cell_edge_coordinates:
            edge_lat, edge_lon = self.cell_edge_coordinates[row["cellname"]]
            color = self.get_ci_color(row["cellname"])
            folium.PolyLine(
                locations=[[row["lat_grid"], row["long_grid"]], [edge_lat, edge_lon]],
                color=color,
                weight=1,
                opacity=0.5,
            ).add_to(self.map)
6. Assigning Colors Using HSV
Description:
The HSV (Hue, Saturation, Value) color space is used to assign colors to different cells based on their unique identifiers.

Implementation:
python
Copy code
def hsv_to_hex(hue):
    rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    return f"#{int(rgb[0] * 255):02x}{int(rgb[1] * 255):02x}{int(rgb[2] * 255):02x}"
python
Copy code
def assign_ci_colors(self):
    unique_cellnames = self.unique_cellname
    num_colors = len(unique_cellnames)
    return {ci: hsv_to_hex(index / num_colors) for index, ci in enumerate(unique_cellnames)}
7. Creating a Legend on the Map with HTML Code
Description:
A dynamic legend helps users understand the color coding used in the map, such as what each color represents in terms of signal strength (RSRP) or cell identifiers.

Implementation:
python
Copy code
def create_legend_template(self, color_by_ci):
    legend_template = """
    {% macro html(this, kwargs) %}
    <div id='maplegend' class='maplegend'
        style='position: absolute; z-index:9999; background-color: rgba(255, 255, 255, 0.8);
        border-radius: 6px; padding: 10px; font-size: 14px; right: 10px; top: 10px;'>
    <div class='legend-scale'>
      <ul class='legend-labels'>
    """
    if color_by_ci:
        legend_template += "<li><strong>EUtranCell</strong></li>"
        for cellname, color in self.ci_colors.items():
            legend_template += f"<li><span style='background: {color}; opacity: 1;'></span>{cellname}</li>"
    else:
        legend_template += """
        <li><strong>RSRP</strong></li>
        <li><span style='background: blue; opacity: 1;'></span>RSRP >= -80</li>
        <li><span style='background: #14380A; opacity: 1;'></span>-95 <= RSRP < -80</li>
        <li><span style='background: #93FC7C; opacity: 1;'></span>-100 <= RSRP < -95</li>
        <li><span style='background: yellow; opacity: 1;'></span>-110 <= RSRP < -100</li>
        <li><span style='background: red; opacity: 1;'></span>RSRP < -110</li>
        """

    legend_template += """
      </ul>
    </div>
    </div>
    <style type='text/css'>
      .maplegend .legend-scale ul {margin: 0; padding: 0; list-style: none;}
      .maplegend .legend-scale ul li {font-size: 80%; list-style: none; margin-left: 0; line-height: 18px; margin-bottom: 2px;}
      .maplegend ul.legend-labels li span {display: block; float: left; height: 16px; width: 30px; margin-right: 5px; margin-left: 0; border: 1px solid #999;}
    </style>
    {% endmacro %}
    """
    return legend_template
