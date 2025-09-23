# app.py

import streamlit as st
import pandas as pd
import re
from hk_grid_converter import HKGridConverter
import io


# Define Hong Kong coordinate bounds
HK_LAT_MIN = 22.15
HK_LAT_MAX = 22.60
HK_LON_MIN = 113.80
HK_LON_MAX = 114.45

# Center of Hong Kong (Victoria Harbour area)
HK_CENTER_LAT = 22.302711
HK_CENTER_LON = 114.177216



@st.cache_resource
def get_converter():
    """Instantiates and returns a cached HKGridConverter object."""
    return HKGridConverter()


def main():
    """The main function to run the Streamlit application."""
    st.set_page_config(page_title="HK Coordinate Converter", layout="wide")

    # Initialize session state for navigation if not already set
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "converter"

    # Initialize session state to hold results
    if 'bulk_results_to_copy' not in st.session_state:
        st.session_state.bulk_results_to_copy = ""
    if 'download_data' not in st.session_state:
        st.session_state.download_data = None
    if 'download_filename' not in st.session_state:
        st.session_state.download_filename = "conversion_results.txt"

    # Get the converter instance
    converter = get_converter()

    # Create the sidebar for navigation
    with st.sidebar:
        st.title("🇭🇰 HK Coordinate Tools")
        st.divider()

        # Navigation buttons
        if st.button("🔄 Coordinate Converter",
                     use_container_width=True,
                     type="primary" if st.session_state.current_page == "converter" else "secondary"):
            st.session_state.current_page = "converter"
            st.rerun()

        if st.button("🔍 Search Coordinates",
                     use_container_width=True,
                     type="primary" if st.session_state.current_page == "search" else "secondary"):
            st.session_state.current_page = "search"
            st.rerun()

        st.divider()
        st.caption("© 2025 HK Coordinate Tools")

    # Display the appropriate page based on navigation
    if st.session_state.current_page == "converter":
        show_converter_page(converter)
    else:
        show_search_page(converter)


def show_converter_page(converter):
    """Display the coordinate converter page."""
    st.title("🔄 Coordinate Converter")
    st.markdown("A versatile tool for converting between WGS84 and HK1980 Grid coordinates.")

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
        ### WGS84 Coordinate Formats:

        **Type 1: With degree and minute symbols**
        - `22°05'05" N, 114°05'05" E` or `N 22°05'05", E 114°05'05"`
        - `22°05.05' N, 114°05.03' E` or `N 22°05.05', E 114°05.03'`
        - `22.3193° N, 114.1694° E` or `N 22.3193°, E 114.1694°`

        **Type 2: Without symbols**
        - `22 05 05 N, 114 05 05 E` or `N 22 05 05, E 114 05 05`
        - `22 05.05 N, 114 05.03 E` or `N 22 05.05, E 114 05.03`
        - `22.3193 N, 114.1694 E` or `N 22.3193, E 114.1694`

        **Type 3: Decimal with sign**
        - `22.3193, 114.1694` (positive = N/E, negative = S/W)
        - `-22.3193, -114.1694` (negative latitude = South, negative longitude = West)

        ### HK1980 Grid Formats:
        - `KK369077`
        - `KK 369077`
        - `KK 369 077`
        """)


def handle_single_conversion(converter, direction):
    """Handles the UI and logic for single conversions."""
    if direction == "WGS84 (Lat/Lon) → HK1980 Grid":
        st.subheader("WGS84 (Lat/Lon) to HK1980 Grid")
        coord_input = st.text_input("Enter WGS84 Coordinate (DD, DM, or DMS)", f"{HK_CENTER_LAT}, {HK_CENTER_LON}")

        if st.button("Convert", key="single_ll_to_grid", type="primary"):
            # Use the enhanced parser instead of the default one
            coords = enhanced_coordinate_parser(coord_input, converter)
            if not coords:
                st.error("Invalid coordinate format. Please check the examples below.")
                return

            lat, lon = coords
            with st.spinner("Converting..."):
                try:
                    grid_ref, error = converter.lat_lon_to_hk_grid(lat, lon)

                    if error:
                        if "API error" in error:
                            st.error("Coordinates are outside the valid range for Hong Kong Grid conversion.")
                        else:
                            st.error(f"**Error:** {error}")
                    else:
                        st.success(f"**Hong Kong Grid:** `{grid_ref}`")

                        # Display map
                        st.subheader("Map View")
                        st.map(pd.DataFrame({'lat': [lat], 'lon': [lon]}), zoom=14)
                except Exception as e:
                    st.error("Coordinates are outside the valid range for Hong Kong Grid conversion.")
                    st.info(f"Debug info - Latitude: {lat}, Longitude: {lon}")

    else:  # HK1980 Grid → WGS84
        st.subheader("HK1980 Grid to WGS84 (Lat/Lon)")
        grid_input = st.text_input("HK1980 Grid Reference", "KK114553")  # Central Hong Kong grid reference

        if st.button("Convert", key="single_grid_to_ll", type="primary"):
            with st.spinner("Converting..."):
                # Use the enhanced grid parser
                grid_ref = parse_hk_grid(grid_input)
                if not grid_ref:
                    st.error("Invalid grid reference format. Please check the examples below.")
                    return

                try:
                    coords, error = converter.hk_grid_to_lat_lon(grid_ref)

                    if error:
                        st.error(f"**Error:** {error}")
                    else:
                        lat, lon = coords
                        st.success(f"**Latitude:** `{lat:.6f}`\n\n**Longitude:** `{lon:.6f}`")

                        # Display map
                        st.subheader("Map View")
                        st.map(pd.DataFrame({'lat': [lat], 'lon': [lon]}), zoom=14)
                except Exception as e:
                    st.error("Invalid grid reference or outside the valid range.")


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
            map_data = []

            with st.spinner(f"Converting {len(lines)} coordinates..."):
                for i, line in enumerate(lines, 1):
                    # Use the enhanced parser
                    coords = enhanced_coordinate_parser(line, converter)
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
                        map_data.append({"lat": lat, "lon": lon})

            if table_results:
                st.dataframe(pd.DataFrame(table_results), use_container_width=True)
                # Store the formatted strings
                st.session_state.bulk_results_to_copy = "\n".join(copyable_results)
                st.session_state.download_data = "".join(download_results)
                st.session_state.download_filename = "wgs84_to_hkgrid_results.txt"

                # Show map if we have valid coordinates
                if map_data:
                    st.subheader("Map View")
                    st.map(pd.DataFrame(map_data), zoom=11)

    else:  # HK1980 Grid → WGS84
        st.subheader("Bulk HK1980 Grid to WGS84 (Lat/Lon)")
        placeholder = "KK195835\nJK 876 543\nHE123456"
        input_data = st.text_area("Enter HK Grid references (one per line)", placeholder, height=150)

        if st.button("Convert All", key="bulk_grid_to_ll", type="primary", on_click=on_convert_click):
            lines = [line.strip() for line in input_data.split('\n') if line.strip()]
            table_results = []
            copyable_results = []
            download_results = []
            map_data = []

            with st.spinner(f"Converting {len(lines)} grid references..."):
                for i, line in enumerate(lines, 1):
                    # Use the enhanced grid parser first
                    grid_ref = parse_hk_grid(line)
                    if not grid_ref:
                        table_results.append(
                            {"Input Grid": line, "Latitude": "Error: Invalid format", "Longitude": "", "Status": "❌"})
                        copyable_results.append("Error: Invalid format")
                        download_results.append(f"({i})\nGrid: {line}\nWGS: Error: Invalid format\n")
                        continue

                    coords, error = converter.hk_grid_to_lat_lon(grid_ref)
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
                        map_data.append({"lat": lat, "lon": lon})

            if table_results:
                st.dataframe(pd.DataFrame(table_results), use_container_width=True)
                # Store the formatted strings
                st.session_state.bulk_results_to_copy = "\n".join(copyable_results)
                st.session_state.download_data = "".join(download_results)
                st.session_state.download_filename = "hkgrid_to_wgs84_results.txt"

                # Show map if we have valid coordinates
                if map_data:
                    st.subheader("Map View")
                    st.map(pd.DataFrame(map_data), zoom=11)

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


def show_search_page(converter):
    """Display the coordinate search page."""
    st.title("🔍 Search Coordinates")
    st.markdown("Locate and visualize coordinates on a map.")

    # Unified coordinate input that accepts both WGS84 and HK1980 Grid
    coord_input = st.text_input(
        "Enter coordinates (WGS84 or HK1980 Grid)",
        f"{HK_CENTER_LAT}, {HK_CENTER_LON}",
        help="Examples: 'N 22 18.17, E 114 10.63', '22.3028, 114.1772', or 'KK114553'"
    )

    # Debug mode toggle
    debug_mode = st.checkbox("Debug parsing", value=False)

    if st.button("Locate", type="primary"):
        if not coord_input.strip():
            st.error("Please enter coordinates.")
            return

        with st.spinner("Locating coordinates..."):
            # First try to parse as WGS84
            if debug_mode:
                wgs84_coords = debug_coordinate_parsing(coord_input, converter)
            else:
                wgs84_coords = enhanced_coordinate_parser(coord_input, converter)

            if wgs84_coords:
                # It's a WGS84 coordinate
                lat, lon = wgs84_coords
                try:
                    grid_ref, error = converter.lat_lon_to_hk_grid(lat, lon)

                    if error:
                        if "API error" in error:
                            st.error("Coordinates are outside the valid range for Hong Kong Grid conversion.")
                        else:
                            st.error(f"Error converting to HK Grid: {error}")
                    else:
                        display_coordinate_result(lat, lon, grid_ref)
                except Exception:
                    st.error("Coordinates are outside the valid range for Hong Kong Grid conversion.")
            else:
                # Try to parse as HK1980 Grid
                grid_ref = parse_hk_grid(coord_input)
                if grid_ref:
                    try:
                        coords, error = converter.hk_grid_to_lat_lon(grid_ref)

                        if error:
                            st.error(f"Error converting grid reference: {error}")
                        else:
                            lat, lon = coords
                            display_coordinate_result(lat, lon, grid_ref)
                    except Exception:
                        st.error("Invalid grid reference or outside the valid range.")
                else:
                    st.error("Invalid coordinate format. Please check the examples below.")

def enhanced_coordinate_parser(coord_str, converter):
    """
    Enhanced parser that handles all specified WGS84 coordinate formats.
    Returns (latitude, longitude) tuple if successful, None if parsing fails.
    """
    if not coord_str:
        return None

    # Clean up the input string
    text = coord_str.strip().upper()

    # Helper to convert DMS/DM components to decimal
    def to_decimal(deg, mnt=0, sec=0, hem=None):
        try:
            deg = float(deg)
            mnt = float(mnt) if mnt else 0
            sec = float(sec) if sec else 0
            dec = deg + mnt / 60.0 + sec / 3600.0
            if hem in ['S', 'W']:
                dec = -dec
            return dec
        except (ValueError, TypeError):
            return None

    # Try to parse using a more flexible approach
    try:
        # Split into lat/lon parts
        parts = re.split(r'[,;]', text)
        if len(parts) != 2:
            # Try to find another separator
            if 'N' in text and ('E' in text or 'W' in text):
                # Try to split at the E/W
                match = re.search(r'([NS].*?)\s*([EW].*)', text)
                if match:
                    parts = [match.group(1), match.group(2)]

        if len(parts) == 2:
            lat_part = parts[0].strip()
            lon_part = parts[1].strip()

            # Extract hemisphere, degrees, minutes, seconds from each part
            lat_hem = None
            lon_hem = None
            lat_deg = None
            lat_min = None
            lat_sec = None
            lon_deg = None
            lon_min = None
            lon_sec = None

            # Check for hemisphere indicators
            if 'N' in lat_part:
                lat_hem = 'N'
            elif 'S' in lat_part:
                lat_hem = 'S'

            if 'E' in lon_part:
                lon_hem = 'E'
            elif 'W' in lon_part:
                lon_hem = 'W'

            # Remove hemisphere indicators for easier parsing
            lat_part = lat_part.replace('N', '').replace('S', '').strip()
            lon_part = lon_part.replace('E', '').replace('W', '').strip()

            # Check for degree/minute/second symbols and remove them
            lat_part = lat_part.replace('°', ' ').replace("'", ' ').replace('"', ' ')
            lon_part = lon_part.replace('°', ' ').replace("'", ' ').replace('"', ' ')

            # Split into components
            lat_components = lat_part.split()
            lon_components = lon_part.split()

            # Parse components based on how many we have
            if len(lat_components) >= 1:
                lat_deg = lat_components[0]
            if len(lat_components) >= 2:
                lat_min = lat_components[1]
            if len(lat_components) >= 3:
                lat_sec = lat_components[2]

            if len(lon_components) >= 1:
                lon_deg = lon_components[0]
            if len(lon_components) >= 2:
                lon_min = lon_components[1]
            if len(lon_components) >= 3:
                lon_sec = lon_components[2]

            # Convert to decimal degrees
            lat = to_decimal(lat_deg, lat_min, lat_sec, lat_hem)
            lon = to_decimal(lon_deg, lon_min, lon_sec, lon_hem)

            # Validate coordinates
            if lat is not None and lon is not None:
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    # Check if within Hong Kong bounds
                    if HK_LAT_MIN <= lat <= HK_LAT_MAX and HK_LON_MIN <= lon <= HK_LON_MAX:
                        return lat, lon
                    else:
                        st.warning("Coordinates are outside of Hong Kong bounds.")
                        return lat, lon  # Still return the coordinates, just with a warning
                else:
                    st.error("Coordinates are outside valid range (-90 to 90 for latitude, -180 to 180 for longitude).")
                    return None
    except Exception:
        pass

    # Format: Decimal degrees (22.3193, 114.1694)
    pattern_dd = re.compile(r"(-?\d+\.\d+)\s*[,;]\s*(-?\d+\.\d+)")
    match = pattern_dd.search(text)
    if match:
        try:
            lat = float(match.group(1))
            lon = float(match.group(2))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                # Check if within Hong Kong bounds
                if HK_LAT_MIN <= lat <= HK_LAT_MAX and HK_LON_MIN <= lon <= HK_LON_MAX:
                    return lat, lon
                else:
                    st.warning("Coordinates are outside of Hong Kong bounds.")
                    return lat, lon  # Still return the coordinates, just with a warning
            else:
                st.error("Coordinates are outside valid range (-90 to 90 for latitude, -180 to 180 for longitude).")
                return None
        except (ValueError, TypeError):
            pass

    # Try the original parser as a fallback
    try:
        coords = converter.parse_any_coordinate_format(coord_str)
        if coords:
            lat, lon = coords
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                # Check if within Hong Kong bounds
                if HK_LAT_MIN <= lat <= HK_LAT_MAX and HK_LON_MIN <= lon <= HK_LON_MAX:
                    return lat, lon
                else:
                    st.warning("Coordinates are outside of Hong Kong bounds.")
                    return lat, lon  # Still return the coordinates, just with a warning
            else:
                st.error("Coordinates are outside valid range (-90 to 90 for latitude, -180 to 180 for longitude).")
                return None
    except Exception:
        pass

    return None


def debug_coordinate_parsing(coord_str, converter):
    """
    Debug function to show the parsing process for a coordinate string.
    """
    text = coord_str.strip().upper()

    st.write(f"Input: '{coord_str}'")
    st.write(f"Cleaned: '{text}'")

    # Split into lat/lon parts
    parts = re.split(r'[,;]', text)
    if len(parts) != 2:
        # Try to find another separator
        if 'N' in text and ('E' in text or 'W' in text):
            # Try to split at the E/W
            match = re.search(r'([NS].*?)\s*([EW].*)', text)
            if match:
                parts = [match.group(1), match.group(2)]
                st.write(f"Split using E/W separator: {parts}")
            else:
                st.write("Could not split using E/W separator")
        else:
            st.write(f"Could not split into two parts: {parts}")
    else:
        st.write(f"Split into parts: {parts}")

    if len(parts) == 2:
        lat_part = parts[0].strip()
        lon_part = parts[1].strip()

        st.write(f"Latitude part: '{lat_part}'")
        st.write(f"Longitude part: '{lon_part}'")

        # Extract hemisphere indicators
        lat_hem = None
        lon_hem = None

        if 'N' in lat_part:
            lat_hem = 'N'
        elif 'S' in lat_part:
            lat_hem = 'S'

        if 'E' in lon_part:
            lon_hem = 'E'
        elif 'W' in lon_part:
            lon_hem = 'W'

        st.write(f"Hemisphere indicators: Lat={lat_hem}, Lon={lon_hem}")

        # Remove hemisphere indicators
        lat_part_clean = lat_part.replace('N', '').replace('S', '').strip()
        lon_part_clean = lon_part.replace('E', '').replace('W', '').strip()

        st.write(f"After removing hemisphere: Lat='{lat_part_clean}', Lon='{lon_part_clean}'")

        # Remove symbols
        lat_part_nosym = lat_part_clean.replace('°', ' ').replace("'", ' ').replace('"', ' ')
        lon_part_nosym = lon_part_clean.replace('°', ' ').replace("'", ' ').replace('"', ' ')

        st.write(f"After removing symbols: Lat='{lat_part_nosym}', Lon='{lon_part_nosym}'")

        # Split into components
        lat_components = lat_part_nosym.split()
        lon_components = lon_part_nosym.split()

        st.write(f"Latitude components: {lat_components}")
        st.write(f"Longitude components: {lon_components}")

        # Try to convert to decimal
        try:
            def to_decimal(deg, mnt=0, sec=0, hem=None):
                deg = float(deg)
                mnt = float(mnt) if mnt else 0
                sec = float(sec) if sec else 0
                dec = deg + mnt / 60.0 + sec / 3600.0
                if hem in ['S', 'W']:
                    dec = -dec
                return dec

            lat_deg = lat_components[0] if len(lat_components) >= 1 else None
            lat_min = lat_components[1] if len(lat_components) >= 2 else None
            lat_sec = lat_components[2] if len(lat_components) >= 3 else None

            lon_deg = lon_components[0] if len(lon_components) >= 1 else None
            lon_min = lon_components[1] if len(lon_components) >= 2 else None
            lon_sec = lon_components[2] if len(lon_components) >= 3 else None

            lat = to_decimal(lat_deg, lat_min, lat_sec, lat_hem)
            lon = to_decimal(lon_deg, lon_min, lon_sec, lon_hem)

            st.write(f"Converted to decimal: Lat={lat}, Lon={lon}")

            if -90 <= lat <= 90 and -180 <= lon <= 180:
                st.write("✅ Valid coordinates!")
                return lat, lon
            else:
                st.write("❌ Coordinates out of valid range")
        except Exception as e:
            st.write(f"❌ Error during conversion: {str(e)}")

    # Try the original parser
    try:
        coords = converter.parse_any_coordinate_format(coord_str)
        if coords:
            lat, lon = coords
            st.write(f"Original parser result: Lat={lat}, Lon={lon}")
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                st.write("✅ Valid coordinates from original parser!")
                return lat, lon
            else:
                st.write("❌ Original parser coordinates out of valid range")
        else:
            st.write("❌ Original parser returned None")
    except Exception as e:
        st.write(f"❌ Error in original parser: {str(e)}")

    st.write("❌ Failed to parse coordinates")
    return None


def parse_hk_grid(grid_str):
    """
    Parse HK1980 Grid reference in various formats.
    Returns standardized grid reference if successful, None if parsing fails.
    """
    if not grid_str:
        return None

    # Remove all spaces and convert to uppercase
    clean_str = grid_str.strip().upper().replace(" ", "")

    # Match pattern like KK369077
    pattern = re.compile(r'^(GE|HE|JK|KK)(\d+)$')
    match = pattern.match(clean_str)

    if match:
        square_id, numbers = match.groups()
        if len(numbers) % 2 != 0:
            return None  # Invalid format - must have even number of digits
        return f"{square_id}{numbers}"

    return None


def display_coordinate_result(lat, lon, grid_ref):
    """Helper function to display coordinate search results."""
    # Create two columns for the results
    col1, col2 = st.columns(2)

    with col1:
        st.success("Coordinates found!")
        st.markdown(f"**WGS84 Coordinates:**")
        st.markdown(f"- Latitude: `{lat:.6f}`")
        st.markdown(f"- Longitude: `{lon:.6f}`")
        st.markdown(f"**HK1980 Grid:**")
        st.markdown(f"- Grid Reference: `{grid_ref}`")

    with col2:
        # Add a copy button for the coordinates
        st.text_area("Copy Coordinates",
                     f"WGS84: {lat:.6f}, {lon:.6f}\nHK1980 Grid: {grid_ref}",
                     height=100,
                     key="copy_coords")

    # Show the location on a map
    st.subheader("Map View")
    st.map(pd.DataFrame({'lat': [lat], 'lon': [lon]}), zoom=14)


if __name__ == "__main__":
    main()
