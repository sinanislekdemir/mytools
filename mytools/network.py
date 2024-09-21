import curses
import subprocess
import time

from mytools.ui import draw_panel

past_data = None
hide_http = False


def clean_past_data():
    global past_data
    past_data = None


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
            "Time",
        ]
    )
    nlist_raw = []
    for line in lines:
        if not line:
            continue
        parts = line.split()
        if hide_http:
            port = parts[4].split(":")[1]
            if port == "80" or port == "443":
                continue

        if len(parts) < 6:
            # make it 6 parts
            parts.extend([""] * (6 - len(parts)))

        parts.append(time.strftime("%H:%M:%S"))
        nlist.append(parts)
        nlist_raw.append(parts)

    if past_data is None:
        past_data = {
            f"{nlist[i][3]}, {nlist[i][4]}, {nlist[i][5]}": nlist[i]
            for i in range(1, len(nlist))
        }

    for i in range(1, len(nlist)):
        check = f"{nlist[i][3]}, {nlist[i][4]}, {nlist[i][5]}"

        if check not in past_data:
            nlist[i][0] = "GREEN!" + nlist[i][0]
            past_data[check] = nlist[i]
            past_data[check][0] = past_data[check][0][6:]

    for key, value in past_data.items():
        if key not in [
            f"{nlist_raw[i][3]}, {nlist_raw[i][4]}, {nlist_raw[i][5]}"
            for i in range(1, len(nlist_raw))
        ]:
            value[0] = "RED!" + value[0]
            nlist.append(value)

    result = {"Network": nlist[:max_items]}

    return result


def network_loop(stdscr: curses.window):
    height, width = stdscr.getmaxyx()
    height -= 2
    items = height - 2
    draw_panel(stdscr, "Network", get_ss_tnp_output(items), 1, 0, width, height - 2)
    stdscr.addstr(
        height - 1, 1, "C: Clean past data H: Hide HTTP", curses.color_pair(0)
    )
