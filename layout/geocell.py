import colorsys
from math import asin, atan2, cos, degrees, radians, sin

import folium
import pandas as pd
import streamlit as st
from branca.element import MacroElement, Template


class GeoApp:
    def __init__(
        self, geocell_data: str | pd.DataFrame, driveless_data: str | pd.DataFrame
    ):
        """
        Initialize the GeoApp with geocell and driveless data.
        """
        self.geocell_data = self.load_data(geocell_data)
        self.driveless_data = self.load_data(driveless_data)
        self.unique_cellname = self.get_unique_cellname()
        self.map_center = self.calculate_map_center()
        self.tile_options = self.define_tile_options()
        self.map = None
        self.ci_colors = self.assign_ci_colors()
        self.cell_edge_coordinates = {}

    # Data loading and preprocessing methods
    @staticmethod
    def load_data(data: str | pd.DataFrame) -> pd.DataFrame:
        """
        Load data from a CSV file or a DataFrame.
        """
        if isinstance(data, str):
            return pd.read_csv(data)
        elif isinstance(data, pd.DataFrame):
            return data

    def get_unique_cellname(self) -> list[str]:
        """
        Extract and sort unique Cell IDs.
        """
        if "cellname" not in self.geocell_data.columns:
            raise ValueError("Column 'cellname' does not exist in geocell_data.")
        return sorted(self.geocell_data["cellname"].unique())

    def calculate_map_center(self) -> list[float]:
        """
        Calculate the geographic center of the map.
        """
        return [
            self.geocell_data["Latitude"].mean(),
            self.geocell_data["Longitude"].mean(),
        ]

    @staticmethod
    def define_tile_options() -> dict[str, str]:
        """
        Define map tile options.
        """
        return {
            "Openstreetmap": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            "Google Hybrid": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        }

    # Color assignment methods
    def assign_ci_colors(self) -> dict[str, str]:
        """
        Assign colors to unique Cell IDs using HSV color space.
        """
        unique_cellnames = self.unique_cellname
        num_colors = len(unique_cellnames)
        return {
            ci: self.hsv_to_hex(index / num_colors)
            for index, ci in enumerate(unique_cellnames)
        }

    @staticmethod
    def hsv_to_hex(hue: float) -> str:
        """
        Convert an HSV color to its hexadecimal string representation.
        """
        rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        return f"#{int(rgb[0] * 255):02x}{int(rgb[1] * 255):02x}{int(rgb[2] * 255):02x}"

    def get_ci_color(self, ci: str) -> str:
        """
        Get color based on Cell ID.
        """
        return self.ci_colors.get(ci, "black")

    @staticmethod
    def get_rsrp_color(rsrp: float) -> str:
        """
        Determine the color representation based on the RSRP value.
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

    # Sector beam calculation methods
    def create_sector_polygon(
        self, lat: float, lon: float, azimuth: float, beamwidth: float, radius: float
    ) -> list[list[float]]:
        """
        Create a sector beam polygon starting from the given latitude and longitude, with the given azimuth, beamwidth, and radius.
        """
        lat_rad, lon_rad, azimuth_rad = radians(lat), radians(lon), radians(azimuth)
        beamwidth_rad = radians(beamwidth)
        angle_step = beamwidth_rad / 49  # 50 points
        start_angle = azimuth_rad - beamwidth_rad / 2

        points = [[lat, lon]]  # Start from the given lat, lon
        points.extend(
            [
                self.calculate_point(
                    lat_rad, lon_rad, start_angle + i * angle_step, radius
                )
                for i in range(50)
            ]
        )
        points.append([lat, lon])  # Close the polygon back to the start point

        return points

    @staticmethod
    def calculate_point(
        lat_rad: float, lon_rad: float, angle: float, radius: float
    ) -> list[float]:
        """
        Calculate a point on the earth's surface based on an angle and radius.
        """
        lat_new = asin(
            sin(lat_rad) * cos(radius / 6371)
            + cos(lat_rad) * sin(radius / 6371) * cos(angle)
        )
        lon_new = lon_rad + atan2(
            sin(angle) * sin(radius / 6371) * cos(lat_rad),
            cos(radius / 6371) - sin(lat_rad) * sin(lat_new),
        )
        return [degrees(lat_new), degrees(lon_new)]

    def create_circle_at_edge(
        self,
        lat: float,
        lon: float,
        radius: float,
        color: str,
        layer: folium.FeatureGroup,
    ):
        """
        Create a circle with transparency at the given latitude and longitude, with the specified radius.
        """
        folium.Circle(
            location=[lat, lon],
            radius=0.001,  # Radius in meters
            color="rgba(0, 0, 0, 0)",
            fill=True,
            fill_color="rgba(0, 0, 0, 0)",
            fill_opacity=0.2,  # Transparent fill
        ).add_to(layer)

    def find_edge_beam_center(
        self, lat: float, lon: float, azimuth: float, radius: float
    ) -> list[float]:
        """
        Calculate the center point of the edge beam.
        """
        return self.calculate_point(
            radians(lat), radians(lon), radians(azimuth), radius
        )

    def create_sector_beam(
        self, lat: float, lon: float, azimuth: float, beamwidth: float, radius: float
    ) -> tuple[list[list[float]], list[float]]:
        """
        Create a sector beam polygon and calculate its edge point.
        """
        points = self.create_sector_polygon(lat, lon, azimuth, beamwidth, radius)
        edge_point = self.find_edge_beam_center(lat, lon, azimuth, radius)
        return points, edge_point

    # Map layer addition methods
    def add_geocell_layer(self):
        """
        Add the geocell layer to the map.
        """
        geocell_layer = folium.FeatureGroup(name="Geocell Sites")

        polygons = [
            (row, self.get_ci_color(row["cellname"]))
            for _, row in self.geocell_data.iterrows()
        ]

        for row, color in polygons:
            self.add_circle_marker(row, color, geocell_layer)
            self.add_site_label(row, geocell_layer)
            self.add_sector_beam(row, color, geocell_layer)

        geocell_layer.add_to(self.map)

    def add_sector_beam(self, row: pd.Series, color: str, layer: folium.FeatureGroup):
        """
        Add a sector beam to the map.
        """
        sector_polygon, edge_point = self.create_sector_beam(
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
            fill_opacity=0.6,
        ).add_to(layer)

        self.create_circle_at_edge(
            edge_point[0], edge_point[1], row["Ant_Size"], color, layer
        )

        self.cell_edge_coordinates[row["cellname"]] = edge_point

    def add_circle_marker(self, row: pd.Series, color: str, layer: folium.FeatureGroup):
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

    def add_site_label(self, row: pd.Series, layer: folium.FeatureGroup):
        """
        Add a label for a cell site.
        """
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=row["site"],
            icon=folium.DivIcon(
                html=f'<div style="font-size: 24pt; color: red">{row["site"]}</div>'
            ),
        ).add_to(layer)

    def add_driveless_layer(self, color_by_ci: bool = True):
        """
        Add the driveless data layer to the map.
        """
        driveless_layer = folium.FeatureGroup(name="Driveless Data")

        for _, row in self.driveless_data.iterrows():
            color = (
                self.get_ci_color(row["cellname"])
                if color_by_ci
                else self.get_rsrp_color(row["rsrp_mean"])
            )
            bounds = self.calculate_rectangle_bounds(row["lat_grid"], row["long_grid"])

            folium.Rectangle(
                bounds=bounds,
                popup=f"CI: {row['cellname']} RSRP: {row['rsrp_mean']} dBm",
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=1,
            ).add_to(driveless_layer)

        driveless_layer.add_to(self.map)

    @staticmethod
    def calculate_rectangle_bounds(
        lat: float, lon: float, size: float = 0.000165
    ) -> list[list[float]]:
        """
        Calculate the bounds of a rectangle given a center point and size.
        """
        return [[lat - size, lon - size], [lat + size, lon + size]]

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

    # Map display and legend methods
    def initialize_map(self, tile_provider: str):
        """
        Initialize the map with the selected tile provider.
        """
        self.map = folium.Map(
            location=self.map_center,
            zoom_start=15,
            tiles=self.tile_options[tile_provider],
            attr=tile_provider,
        )

    def add_dynamic_legend(self, color_by_ci: bool):
        """
        Add a dynamic legend to the map based on whether it's showing RSRP or cellname data.
        """
        legend_template = self.create_legend_template(color_by_ci)
        legend_macro = MacroElement()
        legend_macro._template = Template(legend_template)
        self.map.get_root().add_child(legend_macro)

    def create_legend_template(self, color_by_ci: bool) -> str:
        """
        Create the legend template based on the color coding used.
        """
        legend_template = """
        {% macro html(this, kwargs) %}
        <div id='maplegend' class='maplegend'
            style='position: absolute; z-index:9999; background-color: rgba(192, 192, 192, 1);
            border-radius: 6px; padding: 10px; font-size: 18px; right: 12px; top: 70px;'>
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

    def display_map(self, color_by_ci: bool):
        """
        Display the final map with a dynamic legend.
        """
        folium.LayerControl().add_to(self.map)
        self.add_dynamic_legend(color_by_ci)
        st.components.v1.html(self.map._repr_html_(), height=600)

    def create_popup_content(self, row: pd.Series) -> str:
        """
        Create HTML content for popups.
        """
        return f"""
        <div style="font-family: Arial; font-size: 16px;">
            <b>Site:</b> {row['site']}<br>
            <b>Node:</b> {row['nodeid']}<br>
            <b>Cell:</b> {row['cellname']}
        </div>
        """

    def run_geo_app(self):
        """
        Main method to run the GeoApp.
        """
        # Single tile provider selection for all maps
        if "tile_provider" not in st.session_state:
            st.session_state.tile_provider = list(self.tile_options.keys())[1]

        tile_provider = st.selectbox(
            "Select Map Tile Provider",
            list(self.tile_options.keys()),
            index=list(self.tile_options.keys()).index(st.session_state.tile_provider),
            key="tile_provider_select",
        )

        if st.session_state.tile_provider != tile_provider:
            st.session_state.tile_provider = tile_provider
            st.rerun()

        categories = [
            "cellname",
            "RSRP",
            "cellname with Spidergraph",
            "RSRP with Spidergraph",
        ]

        col1, col2 = st.columns(2)

        for i, category in enumerate(categories):
            column = col1 if i % 2 == 0 else col2

            with column:
                st.subheader(category)

                self.initialize_map(tile_provider)
                self.add_geocell_layer()

                color_by_ci = "cellname" in category
                self.add_driveless_layer(color_by_ci=color_by_ci)

                if "Spidergraph" in category:
                    self.add_spider_graph()

                self.display_map(color_by_ci)
