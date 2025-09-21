# app.py

import streamlit as st
import pandas as pd
import re
from hk_grid_converter import HKGridConverter
import io


@st.cache_resource
def get_converter():
    """Instantiates and returns a cached HKGridConverter object."""
    return HKGridConverter()


def main():
    """The main function to run the Streamlit application."""
    st.set_page_config(page_title="HK Coordinate Converter", layout="wide")

    st.title("🇭🇰 Hong Kong Coordinate Converter")
    st.markdown("A versatile tool for converting between WGS84 and HK1980 Grid coordinates.")

    # Initialize session state to hold results
    if 'bulk_results_to_copy' not in st.session_state:
        st.session_state.bulk_results_to_copy = ""
    if 'download_data' not in st.session_state:
        st.session_state.download_data = None
    if 'download_filename' not in st.session_state:
        st.session_state.download_filename = "conversion_results.txt"

    converter = get_converter()

    # --- UI Toggles for Mode Selection ---
    col1, col2 = st.columns(2)
    with col1:
        direction = st.radio(
            "Select Conversion Direction",
            ("WGS84 (Lat/Lon) → HK1980 Grid", "HK1980 Grid → WGS84 (Lat/Lon)"),
            key="direction_toggle",
            on_change=lambda: st.session_state.update(bulk_results_to_copy="", download_data=None)
        )
    with col2:
        mode = st.radio(
            "Select Conversion Mode",
            ("Single Conversion", "Bulk Conversion"),
            key="mode_toggle",
            on_change=lambda: st.session_state.update(bulk_results_to_copy="", download_data=None)
        )

    st.divider()

    # --- UI Rendering based on selections ---
    if mode == "Single Conversion":
        handle_single_conversion(converter, direction)
    else:
        handle_bulk_conversion(converter, direction)

    # --- Examples Expander ---
    with st.expander("Show Input Format Examples"):
        st.markdown("""
        The tool accepts multiple formats for WGS84 coordinates:
        - **Decimal Degrees (DD):** `22.3193, 114.1694`
        - **Degrees Decimal Minutes (DM):** `22°18.5'N 114°12.75'E` or `N22 18.5, E114 12.75`
        - **Degrees Minutes Seconds (DMS):** `22°18'30"N 114°12'45"E` or `N22 18 30, E114 12 45`

        For HK1980 Grid, use formats like `KK195835` or `JK 876543`.
        """)


def handle_single_conversion(converter, direction):
    # (This function is unchanged)
    if direction == "WGS84 (Lat/Lon) → HK1980 Grid":
        st.subheader("WGS84 (Lat/Lon) to HK1980 Grid")
        coord_input = st.text_input("Enter WGS84 Coordinate (DD, DM, or DMS)", "22°18.5'N 114°12.75'E")

        if st.button("Convert", key="single_ll_to_grid", type="primary"):
            coords = converter.parse_any_coordinate_format(coord_input)
            if not coords:
                st.error("Invalid coordinate format. Please check the examples below.")
                return

            lat, lon = coords
            with st.spinner("Converting..."):
                grid_ref, error = converter.lat_lon_to_hk_grid(lat, lon)

            if error:
                st.error(f"**Error:** {error}")
            else:
                st.success(f"**Hong Kong Grid:** `{grid_ref}`")
                st.map(pd.DataFrame({'lat': [lat], 'lon': [lon]}), zoom=12)

    else:  # HK1980 Grid → WGS84
        st.subheader("HK1980 Grid to WGS84 (Lat/Lon)")
        grid_input = st.text_input("HK1980 Grid Reference", "KK195835")

        if st.button("Convert", key="single_grid_to_ll", type="primary"):
            with st.spinner("Converting..."):
                coords, error = converter.hk_grid_to_lat_lon(grid_input)

            if error:
                st.error(f"**Error:** {error}")
            else:
                lat, lon = coords
                st.success(f"**Latitude:** `{lat:.6f}`\n\n**Longitude:** `{lon:.6f}`")
                st.map(pd.DataFrame({'lat': [lat], 'lon': [lon]}), zoom=12)


def handle_bulk_conversion(converter, direction):
    """Handles the UI and logic for bulk conversions, with copy and download features."""

    # Clear previous results when the button is clicked
    def on_convert_click():
        st.session_state.bulk_results_to_copy = ""
        st.session_state.download_data = None

    if direction == "WGS84 (Lat/Lon) → HK1980 Grid":
        st.subheader("Bulk WGS84 (Lat/Lon) to HK1980 Grid")
        placeholder = "22.2759, 114.1455\n22°18'30\"N 114°12'45\"E\nN22 18.5, E114 12.75"
        input_data = st.text_area("Enter WGS84 coordinates (one per line)", placeholder, height=150)

        if st.button("Convert All", key="bulk_ll_to_grid", type="primary", on_click=on_convert_click):
            lines = [line.strip() for line in input_data.split('\n') if line.strip()]
            table_results = []
            copyable_results = []
            download_results = []

            with st.spinner(f"Converting {len(lines)} coordinates..."):
                for i, line in enumerate(lines, 1):
                    coords = converter.parse_any_coordinate_format(line)
                    if not coords:
                        table_results.append({"Input": line, "HK Grid": "Error: Invalid format", "Status": "❌"})
                        copyable_results.append("Error: Invalid format")
                        download_results.append(f"({i})\nWGS: {line}\nGrid: Error: Invalid format\n")
                        continue

                    lat, lon = coords
                    grid_ref, error = converter.lat_lon_to_hk_grid(lat, lon)
                    if error:
                        table_results.append({"Input": line, "HK Grid": f"Error: {error}", "Status": "❌"})
                        copyable_results.append(f"Error: {error}")
                        download_results.append(f"({i})\nWGS: {line}\nGrid: Error: {error}\n")
                    else:
                        table_results.append({"Input": line, "HK Grid": grid_ref, "Status": "✅"})
                        copyable_results.append(grid_ref)
                        download_results.append(f"({i})\nWGS: {line}\nGrid: {grid_ref}\n")

            if table_results:
                st.dataframe(pd.DataFrame(table_results), use_container_width=True)
                # Store the formatted strings
                st.session_state.bulk_results_to_copy = "\n".join(copyable_results)
                st.session_state.download_data = "".join(download_results)
                st.session_state.download_filename = "wgs84_to_hkgrid_results.txt"

    else:  # HK1980 Grid → WGS84
        st.subheader("Bulk HK1980 Grid to WGS84 (Lat/Lon)")
        placeholder = "KK195835\nJK 876 543\nHE123456"
        input_data = st.text_area("Enter HK Grid references (one per line)", placeholder, height=150)

        if st.button("Convert All", key="bulk_grid_to_ll", type="primary", on_click=on_convert_click):
            lines = [line.strip() for line in input_data.split('\n') if line.strip()]
            table_results = []
            copyable_results = []
            download_results = []

            with st.spinner(f"Converting {len(lines)} grid references..."):
                for i, line in enumerate(lines, 1):
                    coords, error = converter.hk_grid_to_lat_lon(line)
                    if error:
                        table_results.append(
                            {"Input Grid": line, "Latitude": f"Error: {error}", "Longitude": "", "Status": "❌"})
                        copyable_results.append(f"Error: {error}")
                        download_results.append(f"({i})\nGrid: {line}\nWGS: Error: {error}\n")
                    else:
                        lat, lon = coords
                        table_results.append(
                            {"Input Grid": line, "Latitude": f"{lat:.6f}", "Longitude": f"{lon:.6f}", "Status": "✅"})
                        copyable_results.append(f"{lat:.6f}, {lon:.6f}")
                        download_results.append(f"({i})\nGrid: {line}\nWGS: {lat:.6f}, {lon:.6f}\n")

            if table_results:
                st.dataframe(pd.DataFrame(table_results), use_container_width=True)
                # Store the formatted strings
                st.session_state.bulk_results_to_copy = "\n".join(copyable_results)
                st.session_state.download_data = "".join(download_results)
                st.session_state.download_filename = "hkgrid_to_wgs84_results.txt"

    # --- Display the copyable results section ---
    if st.session_state.bulk_results_to_copy:
        st.subheader("Results")

        # Create two columns for the copy and download buttons
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Copy Results")
            st.code(st.session_state.bulk_results_to_copy, language=None)
            st.caption("Click the copy icon in the top-right corner of the box above.")

        with col2:
            st.subheader("Download Results")
            if st.session_state.download_data:
                # Create a download button for the formatted text file
                st.download_button(
                    label="Download as Text File",
                    data=st.session_state.download_data,
                    file_name=st.session_state.download_filename,
                    mime="text/plain",
                )
                st.caption("Download a formatted text file with numbered entries.")


if __name__ == "__main__":
    main()
