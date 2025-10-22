"""MyTools - A comprehensive system monitoring and news reading tool.

This package provides a curses-based terminal user interface for:
- System monitoring (CPU, memory, temperature, processes)
- Network connection monitoring
- RSS news feed reading
- GPU monitoring (NVIDIA)

Usage:
    Run `mytools` from the command line after installation.

    Key bindings:
    - F1/?  : Help
    - F2    : System monitoring mode
    - F3    : News reading mode
    - F4    : Network monitoring mode
    - Q     : Quit
"""

from .core import Config, Logger
from .monitoring import SensorManager, NetworkMonitor, NewsManager

__version__ = "0.2.0"
__author__ = "Sinan Islekdemir"
__email__ = "sinan@islekdemir.com"

__all__ = [
    "Config",
    "Logger",
    "SensorManager",
    "NetworkMonitor",
    "NewsManager",
]
