"""Temperature monitoring utilities."""

import os
from typing import Any, Dict, List

from ..core.logger import Logger


class TemperatureMonitor:
    """Monitor system temperatures."""

    def __init__(self):
        """Initialize temperature monitor."""
        self.logger = Logger.get_logger()

    def read_file(self, file_path: str) -> str:
        """Safely read a system file."""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File {file_path} not found")

            with open(file_path, "r") as file:
                return file.readline().strip()
        except Exception as e:
            self.logger.warning(f"Could not read {file_path}: {e}")
            return ""

    def get_thermal_zones(self) -> List[str]:
        """Get list of available thermal zones."""
        try:
            zones = []
            thermal_path = "/sys/class/thermal/"
            if not os.path.exists(thermal_path):
                return zones

            for zone in os.listdir(thermal_path):
                if zone.startswith("thermal_zone"):
                    zones.append(zone)
            return sorted(zones)
        except Exception as e:
            self.logger.warning(f"Could not list thermal zones: {e}")
            return []

    def read_temperature(self, thermal_zone: str) -> Dict[str, Any]:
        """Read temperature from a specific thermal zone."""
        try:
            temp_path = f"/sys/class/thermal/{thermal_zone}/temp"
            type_path = f"/sys/class/thermal/{thermal_zone}/type"

            temp_str = self.read_file(temp_path)
            type_str = self.read_file(type_path)

            if not temp_str or not type_str:
                return {"type": "unknown", "temp": 0.0, "error": True}

            return {
                "type": type_str.strip(),
                "temp": float(temp_str.strip()) / 1000.0,
                "error": False,
            }
        except Exception as e:
            self.logger.warning(f"Error reading temperature for {thermal_zone}: {e}")
            return {"type": "error", "temp": 0.0, "error": True}

    def get_trip_points(self, thermal_zone: str) -> List[Dict[str, Any]]:
        """Get trip points for a thermal zone."""
        trip_points = []
        try:
            thermal_path = f"/sys/class/thermal/{thermal_zone}"
            if not os.path.exists(thermal_path):
                return trip_points

            for trip in os.listdir(thermal_path):
                if trip.startswith("trip_point") and trip.endswith("_temp"):
                    try:
                        temp_file = f"{thermal_path}/{trip}"
                        action_file = f"{thermal_path}/{trip.replace('temp', 'type')}"

                        temp = self.read_file(temp_file)
                        action = self.read_file(action_file)

                        if temp and action:
                            trip_points.append(
                                {
                                    "temp": float(temp.strip()) / 1000.0,
                                    "action": action.strip(),
                                }
                            )
                    except Exception as e:
                        self.logger.debug(f"Could not read trip point {trip}: {e}")
                        continue
        except Exception as e:
            self.logger.warning(f"Error getting trip points for {thermal_zone}: {e}")

        return trip_points

    def get_all_thermal_data(self) -> Dict[str, str]:
        """Get comprehensive thermal data for all zones."""
        data = {}

        for zone in self.get_thermal_zones():
            temp_data = self.read_temperature(zone)
            if temp_data["error"]:
                data[zone] = "Error reading temperature"
                continue

            info = f"Type: {temp_data['type']}: {temp_data['temp']:.1f}°C"

            trip_points = self.get_trip_points(zone)
            if trip_points:
                info += " ("
                for trip in trip_points:
                    info += f"{trip['temp']:.0f}°C {trip['action']}, "
                info = info[:-2] + ")"  # Remove trailing comma and space

            data[zone] = info

        return data
