import curses
import socket
import subprocess
import time
from functools import lru_cache

from mytools.ui import draw_panel

past_data = {}
hide_http = False


@lru_cache
def reverse_nslookup(ip):
    try:
        host, _, _ = socket.gethostbyaddr(ip)
        return host
    except socket.herror:
        return ip


def time_to_str(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"


def clean_past_data():
    global past_data
    for key in list(past_data.keys()):
        if not past_data[key][8]:
            del past_data[key]


def toggle_hide_http():
    global hide_http
    hide_http = not hide_http


def get_ss_tnp_output(max_items: int) -> dict:
    global past_data
    result = subprocess.run(
        ["ss", "-tnpH"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    lines = result.stdout.decode("utf-8").split("\n")
    nlist = []
    nlist.append(
        [
            "State",
            "Recv-Q",
            "Send-Q",
            "Local Address",
            "Peer Address",
            "Process",
            "Reverse NS",
            "Time",
        ]
    )
    nlist_raw = []
    for line in lines:
        if not line:
            continue
        parts = line.split()
        parts = [part.strip() for part in parts]
        if len(parts) < 6:
            # make it 6 parts
            parts.extend([""] * (6 - len(parts)))

        key = f"{parts[3]}{parts[4]}{parts[5]}"
        nlist_raw.append(key)
        if key not in past_data:
            past_data[key] = [
                parts[0],
                parts[1],
                parts[2],
                parts[3],
                parts[4],
                parts[5],
                reverse_nslookup(parts[4].split(":")[0]),
                time.monotonic(),
                True,
            ]

    for key in past_data:
        if key not in nlist_raw:
            if past_data[key][8]:
                past_data[key][8] = False
                past_data[key][0] = past_data[key][0]
                past_data[key][7] = time.monotonic() - past_data[key][7]

    print_list = []
    print_list.extend(nlist)

    for key, value in past_data.items():
        if hide_http and value[4].split(":")[1] in ["80", "443"]:
            continue
        if not value[8]:
            print_list.append(
                [
                    "RED!" + value[0],
                    "",
                    "",
                    value[3],
                    value[4],
                    value[5],
                    value[6],
                    time_to_str(value[7]),
                ]
            )
        else:
            now = time.monotonic()
            print_list.append(
                [
                    value[0],
                    value[1],
                    value[2],
                    value[3],
                    value[4],
                    value[5],
                    value[6],
                    time_to_str(now - value[7]),
                ]
            )

    result_dict = {"Network": print_list[:max_items]}

    return result_dict


def network_loop(stdscr: curses.window):
    height, width = stdscr.getmaxyx()
    height -= 1
    items = height - 2
    draw_panel(stdscr, "Network", get_ss_tnp_output(items), 1, 0, width, height)
