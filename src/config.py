import os
import json

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'planner_config.json')

DEFAULT_CONFIG = {
    "time_granularity": 0.25,
    "knapsack_max_iterations": 100,
    "knapsack_max_items": 200,
    "default_capacity_per_sprint": 40.0,
    "reorder_debounce_ms": 500,
    "cycle_detection_undirected": True
}

_config = None


def load_config():
    global _config
    if _config is not None:
        return _config
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                _config = {**DEFAULT_CONFIG, **user_config}
                return _config
        except Exception:
            pass
    _config = dict(DEFAULT_CONFIG)
    return _config


def save_config(new_config):
    global _config
    config = load_config()
    config.update(new_config)
    _config = config
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_config(key, default=None):
    config = load_config()
    return config.get(key, default if default is not None else DEFAULT_CONFIG.get(key))


def reset_config():
    global _config
    if os.path.exists(CONFIG_PATH):
        os.remove(CONFIG_PATH)
    _config = dict(DEFAULT_CONFIG)
