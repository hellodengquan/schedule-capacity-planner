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

CONFIG_LIMITS = {
    "knapsack_max_iterations": (1, 10000),
    "knapsack_max_items": (1, 500),
    "reorder_debounce_ms": (100, 5000),
    "time_granularity": (0.0625, 8.0),
}

_config = None


def _validate_config(config):
    """验证配置值，防止 OOM 和非法值"""
    validated = dict(config)
    for key, (min_val, max_val) in CONFIG_LIMITS.items():
        if key in validated:
            val = validated[key]
            if isinstance(val, (int, float)):
                if val < min_val:
                    validated[key] = min_val
                elif val > max_val:
                    validated[key] = max_val
    if validated.get('knapsack_max_iterations'):
        iterations = int(validated['knapsack_max_iterations'])
        threshold = iterations * 100000
        if threshold > 1e9:
            validated['knapsack_max_iterations'] = 10000
    return validated


def load_config():
    global _config
    if _config is not None:
        return _config
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                merged = {**DEFAULT_CONFIG, **user_config}
                _config = _validate_config(merged)
                return _config
        except Exception:
            pass
    _config = _validate_config(dict(DEFAULT_CONFIG))
    return _config


def save_config(new_config):
    global _config
    config = load_config()
    updated = {**config, **new_config}
    validated = _validate_config(updated)
    _config = validated
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(validated, f, indent=2, ensure_ascii=False)


def get_config(key, default=None):
    config = load_config()
    return config.get(key, default if default is not None else DEFAULT_CONFIG.get(key))


def reset_config():
    global _config
    if os.path.exists(CONFIG_PATH):
        os.remove(CONFIG_PATH)
    _config = _validate_config(dict(DEFAULT_CONFIG))
