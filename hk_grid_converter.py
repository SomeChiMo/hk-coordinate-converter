# hk_grid_converter.py

import requests
import json
import re
from typing import Optional, Tuple, Dict, Any


class HKGridConverter:
    """
    A class to handle bidirectional conversions between WGS84 coordinates
    and the Hong Kong 1980 Grid System using the official Lands Department API.
    Includes a robust parser for various coordinate string formats.
    """
    _API_URL = "https://www.geodetic.gov.hk/transform/v2/"
    _cache: Dict[str, Any] = {}

    def _call_api(self, params: Dict[str, Any]) -> Dict[str, Any]:
        cache_key = json.dumps(params, sort_keys=True)
        if cache_key in self._cache:
            return self._cache[cache_key]
        try:
            response = requests.get(self._API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if "ErrorCode" not in data:
                self._cache[cache_key] = data
            return data
        except requests.exceptions.RequestException as e:
            return {"ErrorCode": "Network Error", "ErrorMsg": str(e)}
        except json.JSONDecodeError:
            return {"ErrorCode": "Invalid Response", "ErrorMsg": "Could not parse JSON from API."}

    def parse_any_coordinate_format(self, coord_str: str) -> Optional[Tuple[float, float]]:
        """
        A robust parser that attempts to convert a string from various common
        formats (DMS, DM, DD) into a (latitude, longitude) tuple.
        Returns None if parsing fails.
        """
        text = coord_str.strip().upper()

        # Helper to convert DMS/DM components to decimal
        def to_decimal(deg, mnt, sec, hem):
            dec = float(deg) + float(mnt) / 60.0 + float(sec or 0) / 3600.0
            return -dec if hem in ['S', 'W'] else dec

        # Pattern 1: DMS/DM with hemisphere letters (e.g., 22°18.5'N 114°12.75'E)
        pattern_dms_dm = re.compile(
            r"(\d{1,2})[\s°]*"
            r"(\d{1,2}(?:\.\d+)?)\s*['′]?\s*"
            r"(?:(\d{1,2}(?:\.\d+)?)\s*[\"″]\s*)?"
            r"([NS])"
            r"[\s,;]*"
            r"(\d{1,3})[\s°]*"
            r"(\d{1,2}(?:\.\d+)?)\s*['′]?\s*"
            r"(?:(\d{1,2}(?:\.\d+)?)\s*[\"″]\s*)?"
            r"([EW])"
        )
        match = pattern_dms_dm.search(text)
        if match:
            try:
                g = match.groups()
                lat = to_decimal(g[0], g[1], g[2], g[3])
                lon = to_decimal(g[4], g[5], g[6], g[7])
                return lat, lon
            except (ValueError, TypeError):
                pass

        # Pattern 2: Decimal Degrees (e.g., 22.3193, 114.1694)
        pattern_dd = re.compile(r"^(-?\d+\.?\d*)\s*[,;\s]\s*(-?\d+\.?\d*)$")
        match_dd = pattern_dd.match(text)
        if match_dd:
            try:
                lat, lon = float(match_dd.group(1)), float(match_dd.group(2))
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return lat, lon
            except (ValueError, TypeError):
                pass

        return None

    def lat_lon_to_hk_grid(self, lat: float, lon: float) -> Tuple[Optional[str], Optional[str]]:
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return None, "Invalid latitude or longitude values."
        params = {"inSys": "wgsgeog", "lat": lat, "long": lon}
        data = self._call_api(params)
        if "ErrorCode" in data:
            return None, data.get("ErrorMsg", "An unknown API error occurred.")
        utm_ref_zone = data.get('utmRefZone')
        utm_ref_e = data.get('utmRefE')
        utm_ref_n = data.get('utmRefN')
        if utm_ref_zone and utm_ref_e and utm_ref_n:
            return f"{utm_ref_zone} {utm_ref_e}{utm_ref_n}", None
        return None, "API response did not contain a formatted grid reference."

    def hk_grid_to_lat_lon(self, grid_str: str) -> Tuple[Optional[Tuple[float, float]], Optional[str]]:
        grid_str = grid_str.strip().upper().replace(" ", "")
        match = re.match(r'^(GE|HE|JK|KK)(\d+)$', grid_str)
        if not match:
            return None, "Invalid HK Grid format. Expected format like 'KK123456'."
        square_id, numbers = match.groups()
        if len(numbers) % 2 != 0:
            return None, "Grid numbers must have an even number of digits."
        digits = len(numbers) // 2
        easting, northing = numbers[:digits], numbers[digits:]
        utm_zone = f"50Q-{square_id}" if square_id in ["JK", "KK"] else f"49Q-{square_id}"
        params = {"inSys": "utmref", "outSys": "wgsgeog", "zone": utm_zone, "e": easting, "n": northing}
        data = self._call_api(params)
        if "ErrorCode" in data:
            return None, data.get("ErrorMsg", "An unknown API error occurred.")
        lat, lon = data.get('wgsLat'), data.get('wgsLong')
        if lat is not None and lon is not None:
            return (lat, lon), None
        return None, "API response was missing latitude/longitude data."
