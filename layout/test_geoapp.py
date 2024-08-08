import colorsys

import folium
import streamlit as st
from branca.element import MacroElement, Template


class GeoApp:
    def __init__(self, geocell_data, driveless_data):
        """
        Initialize the GeoApp with geocell and driveless data.

        Remarks:
        - Sets up initial data structures and calculates necessary information.
        - Initializes map center, tile options, and color assignments.
        - Creates a new attribute 'cell_edge_coordinates' to store edge coordinates.
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

        Remarks:
        - Uses pandas operations to get unique cellnames from geocell_data.
        - Sorts the cellnames for consistent ordering.
        """
        return sorted(self.geocell_data["cellname"].unique())

    def calculate_map_center(self):
        """
        Calculate the geographic center of the map.

        Remarks:
        - Computes the mean latitude and longitude from geocell_data.
        - This center point is used as the initial focus of the map.
        """
        return [
            self.geocell_data["Latitude"].mean(),
            self.geocell_data["Longitude"].mean(),
        ]

    @staticmethod
    def define_tile_options():
        """
        Define map tile options.

        Remarks:
        - Provides a dictionary of tile options for the map.
        - Currently includes OpenStreetMap and Google Hybrid options.
        - Can be extended to include more tile providers if needed.
        """
        return {
            "Openstreetmap": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            "Google Hybrid": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        }

    def initialize_map(self):
        """
        Initialize the map with a selected tile provider.

        Remarks:
        - Uses Streamlit to create a selectbox for choosing the tile provider.
        - Initializes a Folium map with the chosen tile provider.
        - Sets the initial map center and zoom level.
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

        Remarks:
        - Creates a unique color for each cell ID using the HSV color space.
        - Converts HSV to RGB, then to hex color code.
        - Ensures visually distinct colors for different cells.
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

        Remarks:
        - Retrieves the pre-assigned color for a given cell ID.
        - Returns 'black' as a fallback if the cell ID is not found.
        """
        return self.ci_colors.get(ci, "black")

    def get_rsrp_color(self, rsrp):
        """
        Determines the color representation based on the RSRP value.

        Remarks:
        - Uses a series of thresholds to assign colors to RSRP values.
        - Colors range from blue (best signal) to red (worst signal).
        - Can be adjusted to match specific RSRP standards or preferences.
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

        Remarks:
        - Uses spherical trigonometry to calculate points on the Earth's surface.
        - Creates a sector-shaped polygon representing the antenna's coverage area.
        - Calculates the edge point at the middle of the arc, using the provided radius.
        - The radius (Ant_Size) determines the size of the sector beam.
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

        Remarks:
        - Creates a new FeatureGroup for geocell sites.
        - Iterates through geocell data to add markers and sector beams.
        - Adds circle markers for cell sites and labels them.
        - Creates sector beams for each cell site.
        - Ensures proper layering of elements (polygons added after markers).
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

        Remarks:
        - Generates formatted HTML for popup information.
        - Includes site ID, node ID, and cell name.
        - Can be extended to include more information if needed.
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

        Remarks:
        - Uses create_sector_beam to generate the sector polygon and edge point.
        - Adds the sector polygon to the map with appropriate styling.
        - Adds a white marker at the edge point of the sector.
        - Stores the edge point coordinates for later use in spider graphs.
        """
        sector_polygon, edge_point = self.create_sector_beam(
            row["Latitude"],
            row["Longitude"],
            row["Dir"],
            row["Ant_BW"],
            row["Ant_Size"],  # Use Ant_Size as the radius
        )
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
            popup=f"Cell Edge: {row['cellname']}",
        ).add_to(layer)

        self.cell_edge_coordinates[row["cellname"]] = edge_point

    def add_circle_marker(self, row, color, layer):
        """
        Add a circle marker for a cell site.

        Remarks:
        - Creates a circular marker at the cell site location.
        - Uses the assigned color for the cell.
        - Adds a popup with site information.
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

        Remarks:
        - Adds a text label (site ID) at the cell site location.
        - Uses a DivIcon for custom styling of the label.
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

        Remarks:
        - Creates a new FeatureGroup for driveless data.
        - Adds circular markers for each driveless data point.
        - Colors markers based on either cell ID or RSRP value.
        - Includes popup information for each point.
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

        Remarks:
        - Creates lines connecting driveless data points to their corresponding cell edge points.
        - Uses stored cell edge coordinates for accurate connections.
        - Colors lines based on the cell ID.
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

        Remarks:
        - Adds a layer control to toggle different map layers.
        - Adds a legend to the map.
        - Uses Streamlit to display the Folium map.
        """
        folium.LayerControl().add_to(self.map)
        self.add_legend()
        st.components.v1.html(self.map._repr_html_(), height=800)

    def display_legend(self):
        """
        Display a legend for cell colors.

        Remarks:
        - Creates a Streamlit subheader for the legend.
        - Lists each cell name with its corresponding color.
        - This method is not currently used in the main display.
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

        Remarks:
        - Creates a complex HTML/CSS-based legend for the map.
        - Includes both RSRP color ranges and cell identity colors.
        - Uses a MacroElement to add the legend to the map.
        - Legend is positioned in the top-right corner of the map.
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

        Remarks:
        - Sets up the Streamlit layout with four columns.
        - Initializes the map in the first column.
        - Creates category selection buttons in all four columns.
        - Adds geocell and driveless layers to the map based on selected category.
        - Adds spider graph if selected.
        - Displays the final map.

        This method orchestrates the entire application flow, combining all the individual components and functionalities of the GeoApp class.
        """
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            self.initialize_map()

        categories = [
            "cellname",
            "RSRP",
            "cellname with Spidergraph",
            "RSRP with Spidergraph",
        ]

        if "category" not in st.session_state:
            st.session_state.category = categories[0]

        for category, col in zip(categories, [col1, col2, col3, col4]):
            with col:
                if st.button(category):
                    st.session_state.category = category
                    st.rerun()

        self.add_geocell_layer()
        color_by_ci = "cellname" in st.session_state.category
        self.add_driveless_layer(color_by_ci=color_by_ci)

        if "Spidergraph" in st.session_state.category:
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
