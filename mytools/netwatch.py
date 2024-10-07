import curses
import socket
import subprocess
import time
from functools import lru_cache

from mytools.ui import draw_panel

past_data = {}
hide_http = False
network_list = {}


@lru_cache
def reverse_nslookup(ip):
    try:
        host, _, _ = socket.gethostbyaddr(ip)
        return host
    except Exception:
        return ip


def time_to_str(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"


def clean_past_data():
    global past_data
    for key in list(past_data.keys()):
        if not past_data[key][6]:
            del past_data[key]


def dump_past_data():
    """Dump past data to a CSV file"""
    with open(f"network_{int(time.time())}.csv", "w") as f:
        f.write("State,Local Address,Peer Address,Process,Reverse NS,Time\n")
        for key, value in past_data.items():
            cpy = value.copy()
            cpy[3] = cpy[3].replace(",", " ")
            row = f"{','.join(cpy[:5])}"
            f.write(row + "\n")


def toggle_hide_http():
    global hide_http
    hide_http = not hide_http


def get_ss_tnp_output():
    global past_data
    global network_list

    result = subprocess.run(
        ["ss", "-tnpH"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    lines = result.stdout.decode("utf-8").split("\n")
    nlist = [
        "State",
        "Local Address",
        "Peer Address",
        "Process",
        "Reverse NS",
        "Time",
    ]

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
                parts[3],
                parts[4],
                parts[5],
                reverse_nslookup(parts[4].split(":")[0]),
                time.monotonic(),
                True,
            ]

    for key in past_data:
        if key not in nlist_raw:
            if past_data[key][6]:
                past_data[key][6] = False
                past_data[key][0] = past_data[key][0]
                past_data[key][5] = time.monotonic() - past_data[key][5]

    print_list = []

    for key, value in past_data.items():
        if hide_http and value[2].split(":")[1] in ["80", "443"]:
            continue
        if not value[6]:
            print_list.append(
                [
                    "RED!" + value[0],
                    value[1],
                    value[2],
                    value[3],
                    value[4],
                    time_to_str(value[5]),
                ]
            )
        else:
            now = time.monotonic()
            pre = ""
            if now - value[5] < 30:
                pre = "GREEN!"
            print_list.append(
                [
                    pre + value[0],
                    value[1],
                    value[2],
                    value[3],
                    value[4],
                    time_to_str(now - value[5]),
                ]
            )

    # Move active to top and sort by time
    print_list.sort(key=lambda x: (x[0].startswith("RED!"), x[5]))
    print_list.insert(0, nlist)

    result_dict = {"Network": print_list}
    network_list = result_dict


def network_loop(stdscr: curses.window):
    height, width = stdscr.getmaxyx()
    height -= 1
    items = height - 2
    print_dict = {}
    if "Network" in network_list:
        print_dict["Network"] = network_list["Network"][:items]

    draw_panel(stdscr, "Network", print_dict, 1, 0, width, height)
