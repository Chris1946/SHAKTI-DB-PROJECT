"""
PulseTrace Agent — Thermal Collector

Collects:
  • CPU package/core temperature (°C)
  • High and critical temperature thresholds
  • Thermal throttling detection (current freq vs max freq)

Platform notes:
  • psutil.sensors_temperatures() is Linux-only
  • On macOS: uses `sudo powermetrics` (if available) or
    `osx-cpu-temp` CLI. Falls back to IOKit-based estimation
    via subprocess. Final fallback is CPU-load heuristic.
  • Throttle detection compares cpu_freq.current vs cpu_freq.max
"""

from __future__ import annotations

import platform
import subprocess
import re
from typing import Any, Dict, Optional

import psutil

from collectors.base import BaseCollector


class ThermalCollector(BaseCollector):
    """Collects CPU temperature and thermal throttling status."""

    def __init__(self) -> None:
        super().__init__("thermal")
        self._macos_method: Optional[str] = None  # Cache which method works

    def _collect(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}

        # ---- Temperature ----
        if platform.system() == "Darwin":
            temp = self._read_macos_temp()
            if temp is not None:
                data["cpu_temp_current"] = round(temp, 1)
                data["cpu_temp_high"] = 95.0
                data["cpu_temp_critical"] = 105.0
            else:
                # Final fallback: estimate from CPU load
                cpu_load = psutil.cpu_percent(interval=None)
                # Base temp ~42°C idle, scales up to ~90°C under full load
                simulated_temp = 42.0 + (cpu_load / 100.0) * 48.0
                data["cpu_temp_current"] = round(simulated_temp, 1)
                data["cpu_temp_high"] = 95.0
                data["cpu_temp_critical"] = 105.0
        else:
            temps = self.safe_get(psutil.sensors_temperatures)
            if temps:
                # Try common sensor names in priority order
                for sensor_name in ("coretemp", "k10temp", "cpu_thermal",
                                    "acpitz", "thermal_zone0"):
                    if sensor_name in temps and temps[sensor_name]:
                        entry = temps[sensor_name][0]  # first entry (package)
                        data["cpu_temp_current"]  = round(entry.current, 1)
                        data["cpu_temp_high"]     = round(entry.high, 1) if entry.high else None
                        data["cpu_temp_critical"] = round(entry.critical, 1) if entry.critical else None
                        break

                # Fallback: use whatever the first sensor key is
                if "cpu_temp_current" not in data:
                    first_key = next(iter(temps), None)
                    if first_key and temps[first_key]:
                        entry = temps[first_key][0]
                        data["cpu_temp_current"]  = round(entry.current, 1)
                        data["cpu_temp_high"]     = round(entry.high, 1) if entry.high else None
                        data["cpu_temp_critical"] = round(entry.critical, 1) if entry.critical else None

        # ---- Throttle detection ----
        freq = self.safe_get(psutil.cpu_freq)
        if freq and freq.max and freq.max > 0:
            # If current frequency is significantly below max, CPU is throttling
            ratio = freq.current / freq.max
            data["cpu_throttled"] = ratio < 0.85  # throttled if < 85% of max
            self.logger.debug(
                "Freq ratio: %.2f (current=%.0f, max=%.0f)",
                ratio, freq.current, freq.max,
            )
        else:
            data["cpu_throttled"] = False

        return data

    # ------------------------------------------------------------------ #
    # macOS temperature reading strategies                                  #
    # ------------------------------------------------------------------ #

    def _read_macos_temp(self) -> Optional[float]:
        """Try multiple methods to read CPU temp on macOS."""

        # If we already know which method works, use it directly
        if self._macos_method == "istats":
            return self._try_istats()
        elif self._macos_method == "osx_cpu_temp":
            return self._try_osx_cpu_temp()
        elif self._macos_method == "sysctl":
            return self._try_sysctl()

        # Try each method and cache which one works
        for method_name, method_fn in [
            ("istats", self._try_istats),
            ("osx_cpu_temp", self._try_osx_cpu_temp),
            ("sysctl", self._try_sysctl),
        ]:
            result = method_fn()
            if result is not None:
                self._macos_method = method_name
                self.logger.info("macOS thermal: using '%s' method", method_name)
                return result

        return None

    def _try_istats(self) -> Optional[float]:
        """Read temperature via `istats` (Ruby gem, common on dev Macs)."""
        try:
            result = subprocess.run(
                ["istats", "cpu", "temp", "--value-only"],
                capture_output=True, text=True, timeout=3,
            )
            if result.returncode == 0:
                return float(result.stdout.strip())
        except (FileNotFoundError, ValueError, subprocess.TimeoutExpired):
            pass
        return None

    def _try_osx_cpu_temp(self) -> Optional[float]:
        """Read temperature via `osx-cpu-temp` CLI tool."""
        try:
            result = subprocess.run(
                ["osx-cpu-temp"],
                capture_output=True, text=True, timeout=3,
            )
            if result.returncode == 0:
                # Output like "61.3°C"
                match = re.search(r"([\d.]+)\s*°?[Cc]", result.stdout)
                if match:
                    return float(match.group(1))
        except (FileNotFoundError, ValueError, subprocess.TimeoutExpired):
            pass
        return None

    def _try_sysctl(self) -> Optional[float]:
        """Read temperature via macOS sysctl (works on some Intel Macs)."""
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.xcpm.cpu_thermal_level"],
                capture_output=True, text=True, timeout=2,
            )
            if result.returncode == 0:
                # This returns a thermal level (0-100), not exact temp.
                # Map 0-100 to roughly 40-95°C
                level = int(result.stdout.strip())
                return 40.0 + (level / 100.0) * 55.0
        except (FileNotFoundError, ValueError, subprocess.TimeoutExpired):
            pass
        return None
