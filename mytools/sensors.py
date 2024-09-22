# Read sensors from /sys/
import curses
import os

from mytools.ui import draw_panel

combined = False
prev_times = None
hide_command = False


def switch_combined():
    global combined
    combined = not combined


def switch_hide_command():
    global hide_command
    hide_command = not hide_command


def bytes_to_human_readable(bytes: int) -> str:
    kb = bytes / 1024
    mb = kb / 1024
    gb = mb / 1024
    tb = gb / 1024
    if tb >= 1:
        return f"{tb:.2f} TB".rjust(10, " ")
    if gb >= 1:
        return f"{gb:.2f} GB".rjust(10, " ")
    if mb >= 1:
        return f"{mb:.2f} MB".rjust(10, " ")
    if kb >= 1:
        return f"{kb:.2f} KB".rjust(10, " ")
    return "0 KB".rjust(10, " ")


def get_nvidia_smi(width: int) -> dict:
    """Run nvidia-smi and get params."""
    command = "nvidia-smi --query-gpu=temperature.gpu,utilization.gpu,utilization.memory,temperature.memory,memory.total,memory.free,memory.used --format=csv 2>/dev/null"
    result = os.popen(command).read().split("\n")
    if len(result) < 2:
        return {"Error": "NVIDIA SMI not found".ljust(width, " ")}
    
    return {
        "GPU temp": f"{result[1].split(', ')[0]}°C".ljust(width, " "),
        "GPU utilization": f"{result[1].split(', ')[1]}".ljust(width, " "),
        "Memory utilization": f"{result[1].split(', ')[2]}".ljust(width, " "),
        "Memory temp": f"{result[1].split(', ')[3]}°C".ljust(width, " "),
        "Memory total": f"{result[1].split(', ')[4]}".ljust(width, " "),
        "Memory free": f"{result[1].split(', ')[5]}".ljust(width, " "),
        "Memory used": f"{result[1].split(', ')[6]}".ljust(width, " "),
    }


def read_file(file_path: str) -> str:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} not found")

    with open(file_path, "r") as file:
        return file.readline().strip()


def get_thermal_zones() -> list[str]:
    zones = []
    for zone in os.listdir("/sys/class/thermal/"):
        if zone.startswith("thermal_zone"):
            zones.append(zone)
    zones = sorted(zones)
    return zones


def get_top_n_processes(n: int, sort="-rss") -> list[list]:
    command = f"ps aux --sort={sort}"
    result = os.popen(command).read().split("\n")
    processes = []
    processes.append(
        [
            "PID",
            "USER",
            "%MEM",
            "%CPU",
            "COMMAND",
            "RSS",
            "VSZ",
        ]
    )
    if not combined:
        for line in result[1:]:
            if not line:
                continue
            line_parts = line.split()
            if line_parts[10] == "ps":
                continue
            pre = ""
            if sort == "-rss":
                if float(line_parts[3]) > 50:
                    pre = "RED!"
                elif float(line_parts[3]) > 20:
                    pre = "YELLOW!"
            if sort == "-%cpu":
                if float(line_parts[2]) > 50:
                    pre = "RED!"
                elif float(line_parts[2]) > 20:
                    pre = "YELLOW!"
            processes.append(
                [
                    pre + line_parts[1],
                    line_parts[0],
                    line_parts[3],
                    line_parts[2],
                    " ".join(line_parts[10:]),
                    bytes_to_human_readable(int(line_parts[5])),
                    bytes_to_human_readable(int(line_parts[4])),
                ]
            )
            if len(processes) == n + 1:
                break
    else:
        cmdmap = {}
        for line in result[1:]:
            if not line:
                continue
            line_parts = line.split()
            cmd = line_parts[10]
            if cmd == "ps":
                continue
            if cmd not in cmdmap:
                cmdmap[cmd] = [
                    line_parts[1],
                    line_parts[0],
                    0,
                    0,
                    line_parts[10],
                    0,
                    0,
                ]

            mem = float(cmdmap[cmd][2]) + float(line_parts[3])
            cpu = float(cmdmap[cmd][3]) + float(line_parts[2])
            mem_str = f"{mem:.2f}"
            cpu_str = f"{cpu:.2f}"
            pre = ""
            if sort == "-rss":
                if mem > 50:
                    pre = "RED!"
                elif mem > 20:
                    pre = "YELLOW!"
            else:
                if cpu > 50:
                    pre = "RED!"
                elif cpu > 20:
                    pre = "YELLOW!"
            cmdmap[cmd][2] = mem_str
            cmdmap[cmd][3] = cpu_str
            cmdmap[cmd][5] = str(int(cmdmap[cmd][5]) + int(line_parts[5]))
            cmdmap[cmd][6] = str(int(cmdmap[cmd][6]) + int(line_parts[4]))
            cmdmap[cmd][0] = pre + line_parts[1]
        procs = [
            [
                cmdmap[cmd][0],
                cmdmap[cmd][1],
                cmdmap[cmd][2],
                cmdmap[cmd][3],
                cmdmap[cmd][4],
                bytes_to_human_readable(int(cmdmap[cmd][5])),
                bytes_to_human_readable(int(cmdmap[cmd][6])),
            ]
            for cmd in cmdmap
        ]
        procs = procs[:n]

        if sort == "-%cpu":
            procs.sort(key=lambda x: float(x[3]), reverse=True)
        else:
            procs.sort(key=lambda x: float(x[2]), reverse=True)
        processes.extend(procs)
    if hide_command:
        for proc in processes[1:]:
            proc[4] = ""
    return processes


def get_total_and_free_memory(num_lines: int) -> dict:
    mem_total = 0
    mem_free = 0
    mem_available = 0
    with open("/proc/meminfo", "r") as file:
        for line in file:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            kb_value = int(value.split(" ")[0])
            if key == "MemTotal":
                mem_total = kb_value
            if key == "MemFree":
                mem_free = kb_value
            if key == "MemAvailable":
                mem_available = kb_value

    procs = get_top_n_processes(num_lines - 3)
    result = {
        "Total": mem_total,
        "Free": mem_free,
        "Available": mem_available,
        "Top processes": procs,
    }
    return result


def read_cpu_times():
    with open("/proc/stat", "r") as f:
        lines = f.readlines()

    cpu_times = []
    for line in lines:
        if line.startswith("cpu"):  # Get all CPU lines including cpu0, cpu1, etc.
            times = line.split()[
                1:8
            ]  # Extract times (user, nice, system, idle, iowait, irq, softirq)
            cpu_times.append(list(map(int, times)))

    return cpu_times


def calculate_cpu_usage(prev_times, curr_times):
    cpu_usages = []
    for prev, curr in zip(prev_times, curr_times):
        prev_idle = prev[3] + prev[4]
        curr_idle = curr[3] + curr[4]

        prev_total = sum(prev)
        curr_total = sum(curr)

        total_diff = curr_total - prev_total
        idle_diff = curr_idle - prev_idle

        usage_percentage = (
            100 * (total_diff - idle_diff) / total_diff if total_diff > 0 else 0
        )
        cpu_usages.append(usage_percentage)

    return cpu_usages


def get_processes_cpu(n: int) -> dict:
    procs = get_top_n_processes(n, "-%cpu")
    return {"Top processes": procs}


def get_cpu_count_and_usage_per_core() -> dict:
    global prev_times

    if prev_times is None:
        prev_times = read_cpu_times()

    curr_times = read_cpu_times()
    cpu_usages = calculate_cpu_usage(prev_times, curr_times)

    result = {}
    for i, usage in enumerate(cpu_usages):
        if i == 0:
            result["Total"] = f"Total: {usage:.2f}%"
        else:
            if usage > 50:
                result[f"Core {i}"] = f"RED!{usage:.2f}%"
            elif usage > 20:
                result[f"Core {i}"] = f"YELLOW!{usage:.2f}%"
            else:
                result[f"Core {i}"] = f"{usage:.2f}%"

    prev_times = curr_times

    return result


def read_temp(thermal_zone: str) -> dict:
    temp = read_file(f"/sys/class/thermal/{thermal_zone}/temp")
    ttype = read_file(f"/sys/class/thermal/{thermal_zone}/type")
    return {"type": ttype.strip(), "temp": float(temp.strip()) / 1000}


def get_trip_points(thermal_zone: str) -> list[dict]:
    trip_points = []
    for trip in os.listdir(f"/sys/class/thermal/{thermal_zone}"):
        # check if file name is like trip_point_<decimal>_temp
        if trip.startswith("trip_point") and trip.endswith("_temp"):
            try:
                temp = read_file(f"/sys/class/thermal/{thermal_zone}/{trip}")
                action = read_file(
                    f"/sys/class/thermal/{thermal_zone}/{trip.replace('temp', 'type')}"
                )
            except FileNotFoundError as e:
                print(e)
                continue
            trip_points.append(
                {"temp": float(temp.strip()) / 1000, "action": action.strip()}
            )
    return trip_points


def get_thermal_data() -> dict:
    data = {}
    for zone in get_thermal_zones():
        temp = read_temp(zone)
        data[zone] = f"Type: {temp['type']}: {temp['temp']}°C"
        if get_trip_points(zone):
            data[zone] += " ("
            for trip in get_trip_points(zone):
                data[zone] += f"{trip['temp']}°C {trip['action']}, "
            data[zone] = data[zone][:-2] + ")"

    return data


def system_loop(stdscr: curses.window):
    height, width = stdscr.getmaxyx()
    thermal_area_height = len(get_thermal_zones()) + 2
    cpu_area_height = height - thermal_area_height - 1
    gpu_width = min(width // 2 - 5, 50)
    memory_width = width - gpu_width - 2
    # Draw a panel to the first quarter of the screen
    draw_panel(
        stdscr,
        "GPU",
        get_nvidia_smi(gpu_width),
        1,
        0,
        gpu_width + 2,
        10,
    )
    draw_panel(
        stdscr,
        "CPU Usage",
        get_cpu_count_and_usage_per_core(),
        11,
        0,
        gpu_width + 2,
        cpu_area_height - thermal_area_height - 1,
    )
    draw_panel(
        stdscr,
        "Memory",
        get_total_and_free_memory(cpu_area_height // 2 - 2),
        1,
        gpu_width + 2,
        memory_width,
        cpu_area_height // 2,
    )
    draw_panel(
        stdscr,
        "CPU",
        get_processes_cpu(cpu_area_height // 2 - 2),
        cpu_area_height // 2 + 1,
        gpu_width + 2,
        memory_width,
        cpu_area_height // 2 + 1,
    )
    draw_panel(
        stdscr,
        "Thermal zones",
        get_thermal_data(),
        cpu_area_height + 1,
        0,
        width,
        thermal_area_height,
    )
