import colorsys
from math import asin, atan2, cos, degrees, radians, sin

import folium
import pandas as pd
import streamlit as st
from branca.element import MacroElement, Template

from layout.styles import styling


class GeoApp:
    def __init__(
        self, geocell_data: str | pd.DataFrame, driveless_data: str | pd.DataFrame
    ):
        self.geocell_data = self._load_data(geocell_data)
        self.driveless_data = self._load_data(driveless_data)
        self.unique_cellname = self._get_unique_cellname()
        self.map_center = self._calculate_map_center()
        self.tile_options = self._define_tile_options()
        self.map = None
        self.ci_colors = self._assign_ci_colors()
        self.cell_edge_coordinates: dict[str, list[float]] = {}

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

    def get_ci_color(self, ci: str) -> str:
        return self.ci_colors.get(ci, "black")

    @staticmethod
    def get_rsrp_color(rsrp: float) -> str:
        ranges = [
            (-80, "blue"),
            (-95, "#14380A"),
            (-100, "#93FC7C"),
            (-110, "yellow"),
            (-115, "red"),
        ]
        return next((color for limit, color in ranges if rsrp >= limit), "red")

    def _create_sector_beam(
        self, lat: float, lon: float, azimuth: float, beamwidth: float, radius: float
    ) -> tuple[list[list[float]], list[float]]:
        lat_rad, lon_rad, azimuth_rad = radians(lat), radians(lon), radians(azimuth)
        beamwidth_rad = radians(beamwidth)
        angle_step = beamwidth_rad / 49
        start_angle = azimuth_rad - beamwidth_rad / 2

        points = [[lat, lon]]
        points.extend(
            [
                self._calculate_point(
                    lat_rad, lon_rad, start_angle + i * angle_step, radius
                )
                for i in range(50)
            ]
        )
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

    def _add_geocell_layer(self):
        geocell_layer = folium.FeatureGroup(name="Geocell Sites")
        for _, row in self.geocell_data.iterrows():
            color = self.get_ci_color(row["cellname"])
            self._add_sector_beam(row, color, geocell_layer)
            self._add_site_label(row, geocell_layer)
            self._add_circle_marker(row, color, geocell_layer)
        geocell_layer.add_to(self.map)

    def _add_sector_beam(self, row: pd.Series, color: str, layer: folium.FeatureGroup):
        sector_polygon, edge_point = self._create_sector_beam(
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
            fill_opacity=1,
        ).add_to(layer)
        self._add_edge_marker(
            edge_point[0], edge_point[1], row["Ant_Size"], color, layer
        )
        self.cell_edge_coordinates[row["cellname"]] = edge_point

    def _add_edge_marker(
        self,
        lat: float,
        lon: float,
        radius: float,
        color: str,
        layer: folium.FeatureGroup,
    ):
        folium.Circle(
            location=[lat, lon],
            radius=0.001,
            color="rgba(0, 0, 0, 0)",
            fill=True,
            fill_color="rgba(0, 0, 0, 0)",
            fill_opacity=0.2,
        ).add_to(layer)

    def _add_circle_marker(
        self, row: pd.Series, color: str, layer: folium.FeatureGroup
    ):
        popup_content = self._create_popup_content(row)
        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=6,
            popup=folium.Popup(popup_content, max_width=250),
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=1.0,
        ).add_to(layer)

    def _add_site_label(self, row: pd.Series, layer: folium.FeatureGroup):
        x, y = self.cell_edge_coordinates[row["cellname"]]
        folium.Marker(
            location=[x, y],
            popup=row["cellname"],
            icon=folium.DivIcon(
                html=f'<div style="font-size: 16pt; color: gray">{row["cellname"]}</div>'
            ),
        ).add_to(layer)

    def _add_driveless_layer(self, color_by_ci: bool = True):
        driveless_layer = folium.FeatureGroup(name="Driveless Data")
        for _, row in self.driveless_data.iterrows():
            color = (
                self.get_ci_color(row["cellname"])
                if color_by_ci
                else self.get_rsrp_color(row["rsrp"])
            )
            folium.CircleMarker(
                location=[row["lat_grid"], row["long_grid"]],
                radius=6,
                popup=f"Cellname: {row['cellname']} RSRP: {row['rsrp']} dBm",
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=1,
            ).add_to(driveless_layer)
        driveless_layer.add_to(self.map)

    def _add_spider_graph(self):
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
                    weight=0.5,
                    opacity=0.5,
                ).add_to(self.map)

    def _initialize_map(self, tile_provider: str):
        self.map = folium.Map(
            location=self.map_center,
            zoom_start=15,
            tiles=self.tile_options[tile_provider],
            attr=tile_provider,
        )

    def _add_dynamic_legend(self, color_by_ci: bool):
        legend_template = self._create_legend_template(color_by_ci)
        legend_macro = MacroElement()
        legend_macro._template = Template(legend_template)
        self.map.get_root().add_child(legend_macro)

    def calculate_rsrp_statistics(self) -> list[str]:
        """Calculate total and percentage of RSRP categories with correct color coding."""
        rsrp_conditions = [
            ("-80  >= 0", lambda rsrp: rsrp >= -80, "blue"),
            ("-95  >= -80", lambda rsrp: -95 <= rsrp < -80, "#14380A"),
            ("-100 >= -95", lambda rsrp: -100 <= rsrp < -95, "#93FC7C"),
            ("-110 >= -100", lambda rsrp: -110 <= rsrp < -100, "yellow"),
            ("-110 >= -140", lambda rsrp: rsrp < -110, "red"),
        ]

        total_records = len(self.driveless_data)
        results = []

        for label, condition, color in rsrp_conditions:
            count = self.driveless_data[
                self.driveless_data["rsrp"].apply(condition)
            ].shape[0]
            percentage = (count / total_records) * 100 if total_records > 0 else 0
            results.append(
                f"<li><span style='background:  {color}; opacity: 1;'></span>{label}&emsp;{count}&emsp;{percentage:.2f}%</li>"
            )

        return results

    def calculate_cellname_statistics(self) -> list[str]:
        """Calculate total and percentage of each unique cellname."""
        total_records = len(self.driveless_data)
        results = []

        for cellname, count in self.driveless_data["cellname"].value_counts().items():
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

    def _display_map(self, color_by_ci: bool):
        folium.LayerControl().add_to(self.map)
        self._add_dynamic_legend(color_by_ci)
        st.components.v1.html(self.map._repr_html_(), height=600)

    @staticmethod
    def _create_popup_content(row: pd.Series) -> str:
        return f"""
        <div style="font-family: Arial; font-size: 16px;">
            <b>Site:</b> {row['site']}<br>
            <b>Node:</b> {row['nodeid']}<br>
            <b>Cell:</b> {row['cellname']}
        </div>
        """

    def run_geo_app(self):
        if "tile_provider" not in st.session_state:
            st.session_state.tile_provider = list(self.tile_options.keys())[1]

        st.markdown(
            *styling("📝 Note:", tag="h6", text_align="left", font_size=26, color="red")
        )
        st.markdown(
            *styling(
                "The geographic data used in this analysis is simulated data created specifically for educational purposes. "
                "This data does not accurately reflect real conditions and is intended solely as an example to illustrate "
                "fundamental geoprocessing concepts. The use of this data is limited to educational settings and "
                "does not represent the conditions of any particular operator.<br>😎",
                tag="p",
                text_align="justify",
                font_size=18,
                color="black",
            )
        )

        col1, col2, _, _ = st.columns([1, 1, 2, 2])
        with col1:
            tile_provider = st.selectbox(
                "MAP",
                list(self.tile_options.keys()),
                index=list(self.tile_options.keys()).index(
                    st.session_state.tile_provider
                ),
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

        with col2:
            selected_category = st.selectbox("Category", categories)

        st.subheader(selected_category)
        self._initialize_map(tile_provider)
        self._add_geocell_layer()

        color_by_ci = "cellname" in selected_category
        self._add_driveless_layer(color_by_ci=color_by_ci)

        if "Spidergraph" in selected_category:
            self._add_spider_graph()

        self._display_map(color_by_ci)
