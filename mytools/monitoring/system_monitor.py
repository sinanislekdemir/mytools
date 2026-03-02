"""GPU and memory monitoring utilities."""

import os
from typing import Dict

from ..core.logger import Logger


class GPUMonitor:
    """Monitor GPU status using nvidia-smi or nouveau drivers."""

    def __init__(self):
        """Initialize GPU monitor."""
        self.logger = Logger.get_logger()
        # Add caching for GPU process data
        self._gpu_cache = {}
        self._gpu_cache_time = {}
        self._gpu_cache_timeout = 1.0  # Cache for 1 second
        self._has_nvidia_smi = None
        self._nouveau_cards = None

    def _check_nvidia_smi(self) -> bool:
        """Check if nvidia-smi is available."""
        if self._has_nvidia_smi is None:
            result = os.popen("command -v nvidia-smi 2>/dev/null").read().strip()
            self._has_nvidia_smi = bool(result)
        return self._has_nvidia_smi

    def _find_nouveau_cards(self) -> list:
        """Find nouveau GPU cards in sysfs."""
        if self._nouveau_cards is not None:
            return self._nouveau_cards

        cards = []
        try:
            drm_path = "/sys/class/drm"
            if not os.path.exists(drm_path):
                self._nouveau_cards = []
                return []

            for card_dir in os.listdir(drm_path):
                if card_dir.startswith("card") and "-" not in card_dir:
                    driver_path = os.path.join(drm_path, card_dir, "device/driver")
                    if os.path.islink(driver_path):
                        driver = os.path.basename(os.readlink(driver_path))
                        if driver == "nouveau":
                            cards.append(os.path.join(drm_path, card_dir, "device"))
        except Exception as e:
            self.logger.warning(f"Error finding nouveau cards: {e}")

        self._nouveau_cards = cards
        return cards

    def _get_nouveau_info(self, width: int) -> Dict[str, str]:
        """Get GPU information from nouveau driver via sysfs."""
        try:
            cards = self._find_nouveau_cards()
            if not cards:
                return {"Error": "No nouveau GPU detected".ljust(width, " ")}

            card_path = cards[0]
            gpu_info = {}

            temp = "N/A"
            try:
                hwmon_path = os.path.join(card_path, "hwmon")
                if os.path.exists(hwmon_path):
                    for hwmon_dir in os.listdir(hwmon_path):
                        temp_file = os.path.join(hwmon_path, hwmon_dir, "temp1_input")
                        if os.path.exists(temp_file):
                            with open(temp_file, "r") as f:
                                temp = f"{int(f.read().strip()) // 1000}°C"
                            break
            except Exception as e:
                self.logger.warning(f"Error reading nouveau temperature: {e}")

            mem_total = "N/A"
            mem_used = "N/A"
            mem_free = "N/A"
            mem_util = "N/A"
            try:
                vram_total_file = os.path.join(card_path, "mem_info_vram_total")
                vram_used_file = os.path.join(card_path, "mem_info_vram_used")

                if os.path.exists(vram_total_file):
                    with open(vram_total_file, "r") as f:
                        total_bytes = int(f.read().strip())
                        mem_total = f"{total_bytes // (1024**2)} MiB"

                if os.path.exists(vram_used_file):
                    with open(vram_used_file, "r") as f:
                        used_bytes = int(f.read().strip())
                        mem_used = f"{used_bytes // (1024**2)} MiB"

                        if os.path.exists(vram_total_file):
                            free_bytes = total_bytes - used_bytes
                            mem_free = f"{free_bytes // (1024**2)} MiB"
                            mem_util = f"{(used_bytes * 100 // total_bytes)} %"
            except Exception as e:
                self.logger.warning(f"Error reading nouveau memory: {e}")

            gpu_info = {
                "GPU temp": temp.ljust(width, " "),
                "GPU utilization": "N/A (nouveau)".ljust(width, " "),
                "Memory utilization": mem_util.ljust(width, " "),
                "Memory temp": "N/A".ljust(width, " "),
                "Memory total": mem_total.ljust(width, " "),
                "Memory free": mem_free.ljust(width, " "),
                "Memory used": mem_used.ljust(width, " "),
            }

            return gpu_info

        except Exception as e:
            self.logger.warning(f"Error getting nouveau GPU info: {e}")
            return {
                "Error": f"GPU monitoring error: {str(e)}"[:width].ljust(width, " ")
            }

    def get_nvidia_info(self, width: int) -> Dict[str, str]:
        """Get GPU information using nvidia-smi or nouveau drivers."""
        try:
            import time

            # Check cache first
            cache_key = f"nvidia_info_{width}"
            current_time = time.time()

            if (
                cache_key in self._gpu_cache
                and cache_key in self._gpu_cache_time
                and current_time - self._gpu_cache_time[cache_key]
                < self._gpu_cache_timeout
            ):
                return self._gpu_cache[cache_key]

            # Try nvidia-smi first
            if self._check_nvidia_smi():
                command = (
                    "nvidia-smi --query-gpu=temperature.gpu,utilization.gpu,utilization.memory,"
                    "temperature.memory,memory.total,memory.free,memory.used --format=csv 2>/dev/null"
                )
                result = os.popen(command).read().split("\n")

                if len(result) >= 2 and result[1].strip():
                    data = result[1].split(", ")
                    if len(data) >= 7:
                        gpu_info = {
                            "GPU temp": f"{data[0]}°C".ljust(width, " "),
                            "GPU utilization": f"{data[1]}".ljust(width, " "),
                            "Memory utilization": f"{data[2]}".ljust(width, " "),
                            "Memory temp": f"{data[3]}°C".ljust(width, " "),
                            "Memory total": f"{data[4]}".ljust(width, " "),
                            "Memory free": f"{data[5]}".ljust(width, " "),
                            "Memory used": f"{data[6]}".ljust(width, " "),
                        }

                        # Cache the result
                        self._gpu_cache[cache_key] = gpu_info
                        self._gpu_cache_time[cache_key] = current_time
                        return gpu_info

            # Fallback to nouveau
            gpu_info = self._get_nouveau_info(width)

            # Cache the result
            self._gpu_cache[cache_key] = gpu_info
            self._gpu_cache_time[cache_key] = current_time
            return gpu_info

        except Exception as e:
            self.logger.warning(f"Error getting GPU info: {e}")
            return {
                "Error": f"GPU monitoring error: {str(e)}"[:width].ljust(width, " ")
            }

    def get_gpu_processes(self, max_processes: int = 20) -> list:
        """Get GPU processes using full nvidia-smi output to capture all GPU processes."""
        try:
            import time

            # Check cache first
            cache_key = f"gpu_processes_{max_processes}"
            current_time = time.time()

            if (
                cache_key in self._gpu_cache
                and cache_key in self._gpu_cache_time
                and current_time - self._gpu_cache_time[cache_key]
                < self._gpu_cache_timeout
            ):
                return self._gpu_cache[cache_key]

            # Use full nvidia-smi to get all GPU processes (Graphics + Compute)
            command = "nvidia-smi 2>/dev/null"
            result = os.popen(command).read().strip()

            if not result:
                processes = [["No nvidia-smi output"]]
                self._gpu_cache[cache_key] = processes
                self._gpu_cache_time[cache_key] = current_time
                return processes

            processes = [["GPU", "PID", "Type", "GPU MEM", "Command"]]

            # Parse the processes section
            lines = result.split("\n")
            in_processes_section = False
            process_data = []

            for line in lines:
                if "Processes:" in line:
                    in_processes_section = True
                    continue
                elif (
                    in_processes_section
                    and line.strip().startswith("|")
                    and not line.strip().startswith("|==")
                ):
                    # Skip header lines
                    if "GPU" in line and "PID" in line and "Type" in line:
                        continue
                    if "ID" in line and "ID" in line:
                        continue

                    # Parse actual process lines: |    0   N/A  N/A            3590      G   cosmic-comp                             402MiB |
                    parts = [p.strip() for p in line.split() if p.strip() != "|"]
                    if len(parts) >= 5:
                        try:
                            gpu_id = parts[0]
                            pid = parts[3]
                            proc_type = parts[4]  # G, C, C+G

                            # Find memory usage (ends with MiB)
                            memory_str = "0 MB"
                            memory_mb = 0
                            for part in parts:
                                if part.endswith("MiB"):
                                    memory_mb = int(part[:-3])
                                    memory_bytes = memory_mb * 1024 * 1024
                                    memory_str = self._bytes_to_human_readable_gpu(
                                        memory_bytes
                                    )
                                    break

                            # Get process name (everything between type and memory)
                            command = "unknown"
                            type_idx = -1
                            mem_idx = -1
                            for i, part in enumerate(parts):
                                if part in ["G", "C", "C+G"]:
                                    type_idx = i
                                elif part.endswith("MiB"):
                                    mem_idx = i
                                    break

                            if (
                                type_idx != -1
                                and mem_idx != -1
                                and mem_idx > type_idx + 1
                            ):
                                command_parts = parts[type_idx + 1 : mem_idx]
                                command = " ".join(command_parts)

                            # Truncate long command names to show ...BaseName.ext...
                            if len(command) > 25:
                                basename = os.path.basename(command)
                                if len(basename) <= 25:
                                    command = "..." + basename + "..."
                                else:
                                    command = "..." + basename[:19] + "..."

                            process_data.append(
                                [gpu_id, pid, proc_type, memory_str, command, memory_mb]
                            )

                        except (ValueError, IndexError):
                            continue

            # Sort by memory usage (descending)
            process_data.sort(key=lambda x: x[5], reverse=True)

            # Add sorted processes to the result (without the memory value used for sorting)
            for proc in process_data[:max_processes]:
                processes.append([proc[0], proc[1], proc[2], proc[3], proc[4]])

            # Add summary row showing totals
            try:
                gpu_total_cmd = "nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null"
                gpu_total_result = os.popen(gpu_total_cmd).read().strip()
                if gpu_total_result:
                    total_gpu_mb = int(gpu_total_result.split("\n")[0])
                    total_processes_mb = sum(proc[5] for proc in process_data)

                    total_gpu_str = self._bytes_to_human_readable_gpu(
                        total_gpu_mb * 1024 * 1024
                    )
                    total_proc_str = self._bytes_to_human_readable_gpu(
                        total_processes_mb * 1024 * 1024
                    )

                    processes.append(["", "", "", "---", "---"])
                    processes.append(
                        ["SUM", "PROC", "", total_proc_str, "Process Total"]
                    )
                    processes.append(["GPU", "TOTL", "", total_gpu_str, "GPU Total"])
            except Exception as e:
                self.logger.warning(f"Error calculating GPU totals: {e}")

            # Cache the result
            self._gpu_cache[cache_key] = processes
            self._gpu_cache_time[cache_key] = current_time
            return processes

        except Exception as e:
            self.logger.warning(f"Error getting GPU processes: {e}")
            # Fallback to the simpler query method
            return self._get_gpu_processes_fallback(max_processes)

    def _get_gpu_processes_fallback(self, max_processes: int) -> list:
        """Fallback method using compute apps query."""
        try:
            command = "nvidia-smi --query-compute-apps=pid,process_name,gpu_uuid,used_memory --format=csv,noheader,nounits 2>/dev/null"
            result = os.popen(command).read().strip()

            if not result:
                return [["No GPU processes running"]]

            processes = [["GPU", "PID", "Type", "GPU MEM", "Command"]]
            lines = result.split("\n")

            for i, line in enumerate(lines[:max_processes]):
                if line.strip():
                    parts = [part.strip() for part in line.split(",")]
                    if len(parts) >= 4:
                        pid = parts[0]
                        process_name = parts[1]
                        gpu_uuid = parts[2][-1:]  # Last char of UUID for GPU ID
                        memory_mb = parts[3]

                        # Convert memory to human readable
                        try:
                            memory_bytes = int(memory_mb) * 1024 * 1024  # MB to bytes
                            memory_str = self._bytes_to_human_readable_gpu(memory_bytes)
                        except ValueError:
                            memory_str = f"{memory_mb} MB"

                        # Truncate long process names to show ...BaseName.ext...
                        if len(process_name) > 30:
                            basename = os.path.basename(process_name)
                            if len(basename) <= 30:
                                process_name = "..." + basename + "..."
                            else:
                                process_name = "..." + basename[:24] + "..."

                        processes.append(
                            [
                                gpu_uuid,
                                pid,
                                "C+G",
                                memory_str,
                                process_name,
                                str(memory_mb) if memory_mb.isdigit() else "0",
                            ]
                        )

            # Sort by memory usage (descending)
            header = processes[0]
            data_rows = processes[1:]
            data_rows.sort(
                key=lambda x: int(x[5]) if x[5].isdigit() else 0, reverse=True
            )

            # Remove the sorting helper column before returning
            sorted_processes = [header] + [
                [row[0], row[1], row[2], row[3], row[4]] for row in data_rows
            ]
            return sorted_processes

        except Exception as e:
            self.logger.warning(f"Error in fallback GPU processes: {e}")
            return [["Error getting GPU processes"]]

    def _bytes_to_human_readable_gpu(self, bytes_value: int) -> str:
        """Convert bytes to human-readable format for GPU memory."""
        mb = bytes_value / (1024 * 1024)
        gb = mb / 1024

        if gb >= 1:
            return f"{gb:.1f} GB"
        else:
            return f"{mb:.0f} MB"


class MemoryMonitor:
    """Monitor system memory usage."""

    def __init__(self):
        """Initialize memory monitor."""
        self.logger = Logger.get_logger()
        # Add caching for memory data
        self._memory_cache = None
        self._memory_cache_time = 0
        self._memory_cache_timeout = 1.0  # Cache for 1 second

    def bytes_to_human_readable(self, bytes_value: int) -> str:
        """Convert bytes to human-readable format."""
        kb = bytes_value / 1024
        mb = kb / 1024
        gb = mb / 1024
        tb = gb / 1024

        if tb >= 1:
            return f"{tb:.2f} TB".rjust(10, " ")
        elif gb >= 1:
            return f"{gb:.2f} GB".rjust(10, " ")
        elif mb >= 1:
            return f"{mb:.2f} MB".rjust(10, " ")
        elif kb >= 1:
            return f"{kb:.2f} KB".rjust(10, " ")
        else:
            return "0 KB".rjust(10, " ")

    def get_memory_info(self) -> Dict[str, str]:
        """Get system memory information."""
        try:
            import time

            # Check cache first
            current_time = time.time()
            if (
                self._memory_cache is not None
                and current_time - self._memory_cache_time < self._memory_cache_timeout
            ):
                return self._memory_cache

            mem_total = 0
            mem_available = 0
            swap_total = 0
            swap_free = 0

            with open("/proc/meminfo", "r") as file:
                for line in file:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    byte_value = int(value.split(" ")[0]) * 1024

                    if key == "MemTotal":
                        mem_total = byte_value
                    elif key == "MemAvailable":
                        mem_available = byte_value
                    elif key == "SwapTotal":
                        swap_total = byte_value
                    elif key == "SwapFree":
                        swap_free = byte_value

            ram_info = f"Available {self.bytes_to_human_readable(mem_available)} Total: {self.bytes_to_human_readable(mem_total)}"
            swap_info = f"Available {self.bytes_to_human_readable(swap_free)} Total: {self.bytes_to_human_readable(swap_total)}"

            memory_info = {
                "Ram ": ram_info,
                "Swap": swap_info,
            }

            # Cache the result
            self._memory_cache = memory_info
            self._memory_cache_time = current_time
            return memory_info

        except Exception as e:
            self.logger.exception(f"Error getting memory info: {e}")
            return {
                "Ram ": "Error reading memory info",
                "Swap": "Error reading swap info",
            }
