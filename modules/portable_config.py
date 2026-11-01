import os
import json
from PyQt5.QtCore import QSettings

CONFIG_FILENAME = "portable_config.json"

def get_app_dir():
    """Returns the base directory of the ArchiveMaster application."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_config_path():
    """Returns the absolute path to portable_config.json."""
    return os.path.join(get_app_dir(), CONFIG_FILENAME)

def load_portable_config():
    """
    Loads configuration from portable_config.json.
    If not found, migrates existing keys from QSettings.
    """
    config_path = get_config_path()
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading portable config: {e}")

    # Fallback / Migration from QSettings (Windows Registry)
    settings = QSettings("MyCompany", "ArchiveMaster")
    legacy_gemini_key = settings.value("gemini_api_key", "")
    legacy_theme = settings.value("theme", "Dark")

    config = {
        "gemini_api_keys": [legacy_gemini_key] if legacy_gemini_key else [],
        "groq_api_keys": [],
        "openrouter_keys": [],
        "active_provider": "auto",
        "theme": legacy_theme,
        "auto_library_search": True,
        "auto_enrich_recommendations": True
    }
    save_portable_config(config)
    return config

def save_portable_config(config):
    """Saves configuration dictionary to portable_config.json."""
    config_path = get_config_path()
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving portable config: {e}")
        return False

def get_all_api_keys():
    """Returns dictionary of all configured API keys."""
    cfg = load_portable_config()
    return {
        "gemini": cfg.get("gemini_api_keys", []),
        "groq": cfg.get("groq_api_keys", []),
        "openrouter": cfg.get("openrouter_keys", [])
    }

def update_api_keys(gemini_keys=None, groq_keys=None, openrouter_keys=None, theme=None):
    """Updates API keys and saves to portable_config.json."""
    cfg = load_portable_config()
    if gemini_keys is not None:
        cfg["gemini_api_keys"] = [k.strip() for k in gemini_keys if k.strip()]
    if groq_keys is not None:
        cfg["groq_api_keys"] = [k.strip() for k in groq_keys if k.strip()]
    if openrouter_keys is not None:
        cfg["openrouter_keys"] = [k.strip() for k in openrouter_keys if k.strip()]
    if theme is not None:
        cfg["theme"] = theme
    return save_portable_config(cfg)
