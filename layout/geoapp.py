import colorsys

import folium
import streamlit as st
from branca.element import MacroElement, Template


class GeoApp:
    def __init__(self, geocell_data, driveless_data):
        self.geocell_data = geocell_data
        self.driveless_data = driveless_data
        self.unique_cellname = self.get_unique_cellname()
        self.map_center = self.calculate_map_center()
        self.tile_options = self.define_tile_options()
        self.map = None
        self.ci_colors = self.assign_ci_colors()

    def get_unique_cellname(self):
        """Extract and sort unique Cell IDs."""
        return sorted(self.geocell_data["cellname"].unique())

    def calculate_map_center(self):
        """Calculate the geographic center of the map."""
        return [
            self.geocell_data["Latitude"].mean(),
            self.geocell_data["Longitude"].mean(),
        ]

    @staticmethod
    def define_tile_options():
        """Define map tile options."""
        return {
            "Openstreetmap": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            "Google Hybrid": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        }

    def initialize_map(self):
        """Initialize the map with a selected tile provider."""
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
        """Assign colors to unique Cell IDs using HSV color space."""
        ci_colors = {}
        num_colors = len(self.unique_cis)
        for index, ci in enumerate(self.unique_cis):
            hue = index / num_colors
            rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            color = f"#{int(rgb[0]*255):02x}{int(rgb[1]*255):02x}{int(rgb[2]*255):02x}"
            ci_colors[ci] = color
        return ci_colors

    def get_ci_color(self, ci):
        """Get color based on Cell ID."""
        return self.ci_colors.get(ci, "black")

    def get_rsrp_color(self, rsrp):
        """Determines the color representation based on the RSRP value."""
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

        points.append([lat, lon])  # Return to the starting point for a complete polygon
        return points

    def add_geocell_layer(self):
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
        return f"""
        <div style="font-family: Arial; font-size: 16px;">
            <b>Site:</b> {row['siteid']}<br>
            <b>Node:</b> {row['nodeid']}<br>
            <b>Cell:</b> {row['cellname']}
        </div>
        """

    def add_sector_polygon(self, row, color, layer):
        sector_polygon = self.create_sector_polygon(
            row["Latitude"],
            row["Longitude"],
            row["Dir"],
            row["Ant_BW"],
            row["Ant_Size"],
        )
        folium.Polygon(
            locations=sector_polygon,
            color="black",
            fill=True,
            fill_color=color,
            fill_opacity=1.0,
        ).add_to(layer)

    def add_circle_marker(self, row, color, layer):
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
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=row["siteid"],
            icon=folium.DivIcon(
                html=f'<div style="font-size: 24pt; color: red">{row["siteid"]}</div>'
            ),
        ).add_to(layer)

    def add_driveless_layer(self, color_by_ci=True):
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
        for _, row in self.driveless_data.iterrows():
            geocell_match = self.geocell_data[
                (self.geocell_data["cellname"] == row["cellname"])
            ]
            if not geocell_match.empty:
                geocell_lat = geocell_match["Latitude"].values[0]
                geocell_lon = geocell_match["Longitude"].values[0]
                color = self.get_ci_color(row["cellname"])
                folium.PolyLine(
                    locations=[
                        [row["lat_grid"], row["long_grid"]],
                        [geocell_lat, geocell_lon],
                    ],
                    color=color,
                    weight=1,
                    opacity=0.5,
                ).add_to(self.map)

    def display_map(self):
        folium.LayerControl().add_to(self.map)
        self.add_legend()
        st.components.v1.html(self.map._repr_html_(), height=800)

    def display_legend(self):
        st.subheader("Legend")
        for cellname, color in self.ci_colors.items():
            st.markdown(
                f'<span style="color:{color};">{cellname}: {color}</span>',
                unsafe_allow_html=True,
            )

    def add_legend(self):
        # Combined Legend
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
        col1, col2, _, _ = st.columns([1, 1, 2, 2])

        with col1:
            self.initialize_map()

        with col2:
            if "category" not in st.session_state:
                st.session_state.category = "cellname"
            category = st.selectbox(
                "Category",
                [
                    "cellname",
                    "RSRP",
                    "cellname with Spidergraph",
                    "RSRP with Spidergraph",
                ],
                index=[
                    "cellname",
                    "RSRP",
                    "Cell with Spidergraph",
                    "RSRP with Spidergraph",
                ].index(st.session_state.category),
                key="category_select",
            )
            if st.session_state.category != category:
                st.session_state.category = category
                st.rerun()

        self.add_geocell_layer()
        color_by_ci = "cellname" in category
        self.add_driveless_layer(color_by_ci=color_by_ci)

        if "Spidergraph" in category:
            self.add_spider_graph()

        self.display_map()
