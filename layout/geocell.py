import colorsys

import folium
import streamlit as st
from branca.element import MacroElement, Template


class GeoApp:
    def __init__(self, geocell_data, driveless_data):
        """
        Initialize the GeoApp with geocell and driveless data.
        """
        self.geocell_data = geocell_data
        self.driveless_data = driveless_data
        self.unique_cellname = self.get_unique_cellname()
        self.map_center = self.calculate_map_center()
        self.tile_options = self.define_tile_options()
        self.map = None
        self.ci_colors = self.assign_ci_colors()
        self.cell_edge_coordinates = {}  # New attribute to store cell edge coordinates

    def get_unique_cellname(self):
        """
        Extract and sort unique Cell IDs.
        """
        return sorted(self.geocell_data["cellname"].unique())

    def calculate_map_center(self):
        """
        Calculate the geographic center of the map.
        """
        return [
            self.geocell_data["Latitude"].mean(),
            self.geocell_data["Longitude"].mean(),
        ]

    def define_tile_options():
        """
        Define map tile options.
        """
        return {
            "Openstreetmap": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            "Google Hybrid": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        }

    def initialize_map(self):
        """
        Initialize the map with a selected tile provider.
        """
        if "tile_provider" not in st.session_state:
            st.session_state.tile_provider = list(self.tile_options.keys())[1]
        tile_provider = st.selectbox(
            "Map",
            list(self.tile_options.keys()),
            index=list(self.tile_options.keys()).index(st.session_state.tile_provider),
            key="tile_provider_select",
        )
        if st.session_state.tile_provider != tile_provider:
            st.session_state.tile_provider = tile_provider
            st.rerun()
        self.map = folium.Map(
            location=self.map_center,
            zoom_start=15,
            tiles=self.tile_options[tile_provider],
            attr=tile_provider,
        )

    def assign_ci_colors(self):
        """
        Assign colors to unique Cell IDs using HSV color space.
        """
        ci_colors = {}
        num_colors = len(self.unique_cellname)
        for index, ci in enumerate(self.unique_cellname):
            hue = index / num_colors
            rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            color = f"#{int(rgb[0]*255):02x}{int(rgb[1]*255):02x}{int(rgb[2]*255):02x}"
            ci_colors[ci] = color
        return ci_colors

    def get_ci_color(self, ci):
        """
        Get color based on Cell ID.
        """
        return self.ci_colors.get(ci, "black")

    def get_rsrp_color(self, rsrp):
        """
        Determines the color representation based on the RSRP value.
        """
        ranges = [
            (-80, "blue"),
            (-95, "#14380A"),
            (-100, "#93FC7C"),
            (-110, "yellow"),
            (-115, "red"),
        ]
        for limit, color in ranges:
            if rsrp >= limit:
                return color
        return "red"

    def create_sector_beam(self, lat, lon, azimuth, beamwidth, radius):
        """
        Create a sector beam polygon and calculate its edge point.
        """
        from math import asin, atan2, cos, degrees, radians, sin

        lat_rad = radians(lat)
        lon_rad = radians(lon)
        azimuth_rad = radians(azimuth)
        beamwidth_rad = radians(beamwidth)
        num_points = 50
        angle_step = beamwidth_rad / (num_points - 1)
        start_angle = azimuth_rad - beamwidth_rad / 2
        points = []

        for i in range(num_points):
            angle = start_angle + i * angle_step
            lat_new = asin(
                sin(lat_rad) * cos(radius / 6371)
                + cos(lat_rad) * sin(radius / 6371) * cos(angle)
            )
            lon_new = lon_rad + atan2(
                sin(angle) * sin(radius / 6371) * cos(lat_rad),
                cos(radius / 6371) - sin(lat_rad) * sin(lat_new),
            )
            points.append([degrees(lat_new), degrees(lon_new)])

        # Calculate the edge point (middle of the arc)
        mid_angle = azimuth_rad
        edge_lat = asin(
            sin(lat_rad) * cos(radius / 6371)
            + cos(lat_rad) * sin(radius / 6371) * cos(mid_angle)
        )
        edge_lon = lon_rad + atan2(
            sin(mid_angle) * sin(radius / 6371) * cos(lat_rad),
            cos(radius / 6371) - sin(lat_rad) * sin(edge_lat),
        )
        edge_point = [degrees(edge_lat), degrees(edge_lon)]
        return points, edge_point

    def add_geocell_layer(self):
        """
        Add the geocell layer to the map.
        """
        geocell_layer = folium.FeatureGroup(name="Geocell Sites")

        polygons = []
        for _, row in self.geocell_data.iterrows():
            color = self.get_ci_color(row["cellname"])
            self.add_circle_marker(row, color, geocell_layer)
            self.add_site_label(row, geocell_layer)
            polygons.append((row, color))

        # Add polygons after markers to prevent them from being sealed by circles
        for row, color in polygons:
            self.add_sector_beam(row, color, geocell_layer)

        geocell_layer.add_to(self.map)

    def create_popup_content(self, row):
        """
        Create HTML content for popups.
        """
        return f"""
        <div style="font-family: Arial; font-size: 16px;">
            <b>Site:</b> {row['siteid']}<br>
            <b>Node:</b> {row['nodeid']}<br>
            <b>Cell:</b> {row['cellname']}
        </div>
        """

    def add_sector_beam(self, row, color, layer):
        """
        Add a sector beam to the map.
        """
        sector_polygon, edge_point = self.create_sector_beam(
            row["Latitude"],
            row["Longitude"],
            row["Dir"],
            row["Ant_BW"],
            row["Ant_Size"],  # Use Ant_Size as the radius
        )

        # Debug: Print edge point coordinates
        st.write(f"Edge Point for cell {row['cellname']}: {edge_point}")

        folium.Polygon(
            locations=sector_polygon,
            color="black",
            fill=True,
            fill_color=color,
            fill_opacity=1.0,
        ).add_to(layer)

        # Add edge point marker and store coordinates
        edge_marker = folium.CircleMarker(
            location=edge_point,
            radius=3,
            color="white",
            fill=True,
            fill_color="white",
            fill_opacity=1.0,
            popup=folium.Popup(f"Cell Edge: {row['cellname']}", max_width=250),
        )

        # Debug: Check if marker is being added
        if edge_marker:
            st.error(f"Edge marker for cell {row['cellname']} added successfully")
        else:
            st.error(f"Failed to add edge marker for cell {row['cellname']}")

        edge_marker.add_to(layer)

        self.cell_edge_coordinates[row["cellname"]] = edge_point

    def add_circle_marker(self, row, color, layer):
        """
        Add a circle marker for a cell site.
        """
        popup_content = self.create_popup_content(row)
        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=6,
            popup=folium.Popup(popup_content, max_width=250),
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=1.0,
        ).add_to(layer)

    def add_site_label(self, row, layer):
        """
        Add a label for a cell site.
        """
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=row["siteid"],
            icon=folium.DivIcon(
                html=f'<div style="font-size: 24pt; color: red">{row["siteid"]}</div>'
            ),
        ).add_to(layer)

    def add_driveless_layer(self, color_by_ci=True):
        """
        Add the driveless data layer to the map.
        """
        driveless_layer = folium.FeatureGroup(name="Driveless Data")

        for _, row in self.driveless_data.iterrows():
            if color_by_ci:
                color = self.get_ci_color(row["cellname"])
            else:
                color = self.get_rsrp_color(row["rsrp_mean"])
            folium.CircleMarker(
                location=[row["lat_grid"], row["long_grid"]],
                radius=4,
                popup=f"cellname: {row['cellname']} RSRP: {row['rsrp_mean']} dBm",
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=1,
            ).add_to(driveless_layer)

        driveless_layer.add_to(self.map)

    def add_spider_graph(self):
        """
        Add spider graph connections to the map.
        """
        for _, row in self.driveless_data.iterrows():
            if row["cellname"] in self.cell_edge_coordinates:
                edge_lat, edge_lon = self.cell_edge_coordinates[row["cellname"]]
                color = self.get_ci_color(row["cellname"])
                folium.PolyLine(
                    locations=[
                        [row["lat_grid"], row["long_grid"]],
                        [edge_lat, edge_lon],
                    ],
                    color=color,
                    weight=1,
                    opacity=0.5,
                ).add_to(self.map)

    def display_map(self):
        """
        Display the final map.
        """
        folium.LayerControl().add_to(self.map)
        self.add_legend()
        st.components.v1.html(self.map._repr_html_(), height=800)

    def display_legend(self):
        """
        Display a legend for cell colors.
        """
        st.subheader("Legend")
        for cellname, color in self.ci_colors.items():
            st.markdown(
                f'<span style="color:{color};">{cellname}: {color}</span>',
                unsafe_allow_html=True,
            )

    def add_legend(self):
        """
        Add a combined legend to the map.
        """
        combined_legend_template = """
        {% macro html(this, kwargs) %}
        <div id='maplegend' class='maplegend'
            style='position: absolute; z-index:9999; background-color: rgba(192, 192, 192, 1);
            border-radius: 6px; padding: 10px; font-size: 18px; right: 12px; top: 70px;'>
        <div class='legend-scale'>
          <ul class='legend-labels'>
            <li><strong>RSRP</strong></li>
            <li><span style='background: blue; opacity: 1;'></span>RSRP >= -85</li>
            <li><span style='background: green; opacity: 1;'></span>-95 <= RSRP < -85</li>
            <li><span style='background: yellow; opacity: 1;'></span>-105 <= RSRP < -95</li>
            <li><span style='background: orange; opacity: 1;'></span>-115 <= RSRP < -105</li>
            <li><span style='background: red; opacity: 1;'></span>RSRP < -115</li>
          </ul>
          <ul class='legend-labels'>
            <li><strong>CELL IDENTITY</strong></li>
        """
        for cellname, color in self.ci_colors.items():
            combined_legend_template += f"<li><span style='background: {color}; opacity: 1;'></span>CELL {cellname}</li>"

        combined_legend_template += """
          </ul>
        </div>
        </div>
        <style type='text/css'>
          .maplegend .legend-scale ul {margin: 0; padding: 0; color: #0f0f0f;}
          .maplegend .legend-scale ul li {list-style: none; line-height: 18px; margin-bottom: 1.5px;}
          .maplegend ul.legend-labels li span {float: left; height: 16px; width: 16px; margin-right: 4.5px;}
        </style>
        {% endmacro %}
        """
        combined_macro = MacroElement()
        combined_macro._template = Template(combined_legend_template)
        self.map.get_root().add_child(combined_macro)

    def run_geo_app(self):
        """
        Main method to run the GeoApp.
        """
        self.initialize_map()
        self.add_geocell_layer()

        categories = [
            "cellname",
            "RSRP",
            "cellname with Spidergraph",
            "RSRP with Spidergraph",
        ]

        for category in categories:
            st.subheader(category)

        col1, col2 = st.columns(2)

        with col1:
          if category == "cellname":
            self.add_driveless_layer(color_by_ci=True)

        with col2:
          if category == "RSRP":
            self.add_driveless_layer(color_by_ci=False)

        col1, col2 = st.columns(2)

        with col1:
          if category == "cellname with Spidergraph":
            self.add_driveless_layer(color_by_ci=True)
            self.add_spider_graph()
        with col2:
          if category == "RSRP with Spidergraph":
            self.add_driveless_layer(color_by_ci=False)
            self.add_spider_graph()

        self.display_map()


# End of GeoApp class

"""
Overall Class Structure and Functionality:

1. Initialization:
   - Sets up data structures and initial calculations.
   - Prepares color assignments and map settings.

2. Map Creation:
   - Initializes a Folium map with customizable tile options.
   - Allows user to select different map providers.

3. Data Visualization:
   - Adds geocell sites with sector beams and labels.
   - Visualizes driveless data points.
   - Implements a spider graph connecting driveless points to cell edges.

4. Color Coding:
   - Assigns unique colors to cell IDs.
   - Uses color gradients for RSRP values.

5. Interactivity:
   - Provides popups with detailed information on markers.
   - Allows toggling between different visualization modes.

6. Legend:
   - Adds a comprehensive legend explaining color codes for both cell IDs and RSRP values.

7. Streamlit Integration:
   - Uses Streamlit for the user interface and app layout.
   - Implements category selection buttons for different visualization modes.

8. Flexibility:
   - Adapts to different antenna sizes and configurations.
   - Calculates sector beams and edge points dynamically.

This class provides a comprehensive tool for visualizing and analyzing cellular network data, combining geographical information with network performance metrics in an interactive web application.
"""
