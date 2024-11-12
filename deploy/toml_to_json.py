#!/usr/bin/env python3
import tomllib  # or 'toml' package
import json
import argparse
from pathlib import Path

def convert_config(toml_path, json_path=None):
    """Convert TOML configuration to JSON format."""
    if json_path is None:
        json_path = Path(toml_path).with_suffix('.json')

    # Read TOML
    with open(toml_path, 'rb') as f:  # tomli requires binary mode
        config = tomllib.load(f)

    # Validate configuration (optional but recommended)
    validate_config(config)

    # Write JSON
    with open(json_path, 'w') as f:
        json.dump(config, f)

    print(f"Configuration converted successfully:")
    print(f"TOML: {toml_path}")
    print(f"JSON: {json_path}")

def validate_config(config):
    """Validate the configuration structure and values."""
    required_sections = ['wifi', 'server', 'leds', 'sensors']
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required section: {section}")

    # Validate WiFi config
    if 'ssid' not in config['wifi'] or 'password' not in config['wifi']:
        raise ValueError("WiFi configuration must include 'ssid' and 'password'")

    # Validate LED configs
    for led_id, led_config in config.get('leds', {}).items():
        required_led_fields = ['pin', 'color', 'location', 'type']
        for field in required_led_fields:
            if field not in led_config:
                raise ValueError(f"LED '{led_id}' missing required field: {field}")

        # Validate pin number
        if not isinstance(led_config['pin'], int):
            raise ValueError(f"LED '{led_id}' pin must be an integer")

    # Validate sensor configs
    for sensor_id, sensor_config in config.get('sensors', {}).items():
        required_sensor_fields = ['pin', 'type', 'location', 'unit', 'adc']
        for field in required_sensor_fields:
            if field not in sensor_config:
                raise ValueError(f"Sensor '{sensor_id}' missing required field: {field}")

        # Validate pin number
        if not isinstance(sensor_config['pin'], int):
            raise ValueError(f"Sensor '{sensor_id}' pin must be an integer")

        # Validate config section if present
        if 'config' in sensor_config:
            if 'type' not in sensor_config['config']:
                raise ValueError(f"Sensor '{sensor_id}' config missing 'type'")

            config_type = sensor_config['config']['type']
            if config_type not in ['linear', 'polynomial']:
                raise ValueError(f"Sensor '{sensor_id}' has invalid config type: {config_type}")

            if 'params' not in sensor_config['config']:
                raise ValueError(f"Sensor '{sensor_id}' config missing 'params'")

def main():
    parser = argparse.ArgumentParser(description='Convert TOML configuration to JSON')
    parser.add_argument('toml_path', type=Path, help='Path to TOML configuration file')
    parser.add_argument('--output', '-o', type=Path, help='Output JSON file path (optional)')
    args = parser.parse_args()

    # Validate that input file exists
    if not args.toml_path.exists():
        raise FileNotFoundError(f"Input file not found: {args.toml_path}")

    # Convert paths to strings for the convert_config function
    toml_path = str(args.toml_path)
    output_path = str(args.output) if args.output else None

    convert_config(toml_path, output_path)

if __name__ == '__main__':
    main()