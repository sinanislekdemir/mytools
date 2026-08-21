"""Configuration module for mytools application."""

import json
from pathlib import Path
from typing import Any, Dict, List


class Config:
    """Central configuration management."""

    # Default news sources
    DEFAULT_NEWS_SOURCES = [
        "https://hackaday.com/blog/feed/",
        "https://www.engadget.com/rss.xml",
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://techcrunch.com/feed/",
        "https://krebsonsecurity.com/feed/",
        "https://www.bleepingcomputer.com/feed/",
        "https://lobste.rs/rss",
    ]

    # HTTP headers for news requests
    ACCEPT_HEADER = (
        "application/atom+xml"
        ",application/rdf+xml"
        ",application/rss+xml"
        ",application/x-netcdf"
        ",application/xml"
        ";q=0.9,text/xml"
        ";q=0.2,*/*"
        ";q=0.1"
    )

    HTTP_HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Accept": ACCEPT_HEADER,
    }

    # UI Settings
    REFRESH_INTERVAL = 1.0  # seconds
    NETWORK_REFRESH_INTERVAL = 0.5  # seconds

    # Performance thresholds
    CPU_WARNING_THRESHOLD = 20.0
    CPU_CRITICAL_THRESHOLD = 50.0
    MEMORY_WARNING_THRESHOLD = 20.0
    MEMORY_CRITICAL_THRESHOLD = 50.0

    # Network settings
    NETWORK_CSV_PREFIX = "network_"

    @classmethod
    def get_news_sources(cls) -> List[str]:
        """Load news sources from file or return defaults."""
        sources_file = Path("news_sources.txt")
        home_sources_file = Path.home() / ".news_sources.txt"

        for path in (sources_file, home_sources_file):
            try:
                if path.exists():
                    with open(path, "r") as f:
                        sources = [line.strip() for line in f.readlines() if line.strip()]
                    if sources:
                        return sources
            except (OSError, IOError, UnicodeDecodeError) as e:
                print(f"Warning: Could not read news sources from {path}: {e}")

        return cls.DEFAULT_NEWS_SOURCES

    @classmethod
    def get_temp_dir(cls) -> Path:
        """Get temporary directory for logs and data files."""
        return Path("/tmp")

    @classmethod
    def get_error_log_path(cls) -> Path:
        """Get path for error log file."""
        return cls.get_temp_dir() / "mytools_error.log"

    @classmethod
    def get_config_file_path(cls) -> Path:
        """Get path to the user configuration file."""
        return Path.home() / ".mytools"

    @classmethod
    def load_user_config(cls) -> Dict[str, Any]:
        """Load user configuration from ~/.mytools file."""
        config_file = cls.get_config_file_path()
        default_config = {"network": {"excluded_processes": []}}

        try:
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Merge with defaults
                    for section, values in default_config.items():
                        if section not in loaded:
                            loaded[section] = values
                        else:
                            for key, default_value in values.items():
                                if key not in loaded[section]:
                                    loaded[section][key] = default_value
                    return loaded
            else:
                return default_config

        except Exception as e:
            print(f"Warning: Error loading config, using defaults: {e}")
            return default_config

    @classmethod
    def save_user_config(cls, config: Dict[str, Any]) -> bool:
        """Save user configuration to ~/.mytools file."""
        try:
            config_file = cls.get_config_file_path()
            config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"Error: Error saving config: {e}")
            return False

    @classmethod
    def get_excluded_processes(cls) -> List[str]:
        """Get list of excluded process keywords."""
        config = cls.load_user_config()
        return config.get("network", {}).get("excluded_processes", [])

    @classmethod
    def set_excluded_processes(cls, keywords: List[str]) -> bool:
        """Set list of excluded process keywords."""
        config = cls.load_user_config()
        if "network" not in config:
            config["network"] = {}
        config["network"]["excluded_processes"] = keywords
        return cls.save_user_config(config)

    @classmethod
    def is_process_excluded(cls, process_name: str) -> bool:
        """Check if a process should be excluded based on keywords."""
        if not process_name:
            return False

        excluded_keywords = cls.get_excluded_processes()
        process_lower = process_name.lower()

        for keyword in excluded_keywords:
            if keyword and keyword.lower() in process_lower:
                return True

        return False
