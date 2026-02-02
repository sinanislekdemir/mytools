# MyTools - System Monitoring & News Reader

A comprehensive terminal-based system monitoring and RSS news reading tool with a curses TUI interface.

## Features

- **System Monitoring**: CPU usage, memory, temperatures, processes, GPU (NVIDIA)
- **Network Monitoring**: Active connections with reverse DNS lookup
- **RSS News Reader**: Multi-source RSS feed aggregation and reading
- **Clean Architecture**: Modular design with proper separation of concerns
- **Type Safety**: Full type hints throughout the codebase
- **Robust Error Handling**: Comprehensive logging and error management

## Installation

```bash
pip install .
```

For development:
```bash
pip install -e ".[dev]"
```

## Usage

Run the application:
```bash
mytools
```

### Key Bindings

- **F1** / **?**: Help
- **F2**: System monitoring mode
- **F3**: News reading mode  
- **F4**: Network monitoring mode
- **F5**: Home/Kiosk mode (Dashboard with system stats and newsfeed)
- **Q**: Quit

#### System Mode
- **C**: Toggle combined process view
- **H**: Hide command names in process list

#### News Mode
- **Left/Right**: Change news source
- **Up/Down**: Navigate news items
- **Enter**: Read news article
- **O**: Open in browser
- **R**: Refresh current source

#### Network Mode
- **C**: Clean past data
- **H**: Hide HTTP/HTTPS connections
- **D**: Dump data to CSV
- **R**: Refresh

#### Home/Kiosk Mode
- Displays real-time system statistics:
  - GPU temperature and VRAM usage
  - RAM and Swap memory status
  - Top 3 CPU-intensive applications
  - Top 3 memory-intensive applications
- Integrated newsfeed from first 3 configured sources
- Auto-refreshes every minute

## Configuration

Create `~/.news_sources.txt` to add custom RSS feeds:
```
https://example.com/feed.xml
https://another-site.com/rss
```

## Architecture

The codebase has been refactored for maintainability:

```
mytools/
├── core/           # Core functionality
│   ├── config.py   # Configuration management
│   ├── logger.py   # Logging utilities
│   ├── themes.py   # UI themes and constants
│   └── ui.py       # UI drawing utilities
└── monitoring/     # Monitoring modules
    ├── *_monitor.py # Specialized monitors
    ├── sensors.py   # System sensor management
    ├── netwatch.py  # Network monitoring
    └── news_*.py    # News functionality
```

## Development

The project includes comprehensive development tools:

- **Black**: Code formatting
- **isort**: Import sorting  
- **mypy**: Type checking
- **pytest**: Testing framework

Run checks:
```bash
black mytools/
isort mytools/
mypy mytools/
pytest
```

## Screenshot

![MyTools Interface](https://github.com/user-attachments/assets/669db5f9-3e05-441c-bcd2-97eb99b18008)

## License

MIT License - see LICENSE file for details.

## Author

Sinan Islekdemir (sinan@islekdemir.com)
