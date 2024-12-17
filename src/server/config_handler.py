import json
from machine import Pin, ADC

class ConfigHandler:
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.wifi_config = {}
        self.server_config = {}
        self.leds = {}
        self.sensors = {}
        self.motors = {}

    def load_config(self):
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)

            # Load WiFi configuration
            self.wifi_config = config.get('wifi', {})
            self.server_config = config.get('server', {'port': 80})

            # Initialize LEDs
            for led_id, led_config in config.get('leds', {}).items():
                self.leds[led_id] = {
                    "pin": Pin(led_config["pin"], Pin.OUT),
                    "color": led_config["color"],
                    "location": led_config["location"],
                    "type": led_config["type"]
                }

            # Initialize Motors
            for motor_id, motor_config in config.get('motors', {}).items():
                self.motors[motor_id] = {
                    "pin_on": Pin(motor_config["pin_on"], Pin.OUT),
                    "pin_dir": Pin(motor_config["pin_dir"], Pin.OUT),
                    "type": motor_config["type"],
                    "location": motor_config["location"]
                }

            # Initialize Sensors
            for sensor_id, sensor_config in config.get('sensors', {}).items():
                pin_class = ADC if sensor_config.get("adc", False) else Pin
                self.sensors[sensor_id] = {
                    "pin": pin_class(sensor_config["pin"]),
                    "type": sensor_config["type"],
                    "location": sensor_config["location"],
                    "unit": sensor_config["unit"],
                    "config": sensor_config.get("config", {})
                }

            print(f"Configuration loaded: {len(self.leds)} LEDs, {len(self.sensors)} sensors, {len(self.motors)} motors")
            return True
        except Exception as e:
            print(f"Error loading configuration: {str(e)}")
            raise

    def save_config(self):
        """Save current configuration back to JSON file"""
        config = {
            "wifi": self.wifi_config,
            "server": self.server_config,
            "leds": {},
            "motors": {},
            "sensors": {}
        }

        # Save LED configurations
        for led_id, led_info in self.leds.items():
            config["leds"][led_id] = {
                "pin": led_info["pin"].id(),
                "color": led_info["color"],
                "location": led_info["location"],
                "type": led_info["type"]
            }

        # Save motor configurations
        for motor_id, motor_info in self.motors.items():
            config["motors"][motor_id] = {
                "pin_on": motor_info["pin_on"].id(),
                "pin_dir": motor_info["pin_dir"].id(),
                "type": motor_info["type"],
                "location": motor_info["location"]
            }

        # Save sensor configurations
        for sensor_id, sensor_info in self.sensors.items():
            config["sensors"][sensor_id] = {
                "pin": sensor_info["pin"].id(),
                "type": sensor_info["type"],
                "location": sensor_info["location"],
                "unit": sensor_info["unit"],
                "adc": isinstance(sensor_info["pin"], ADC),
                "config": sensor_info["config"]
            }

        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
            print("Configuration saved successfully")
            return True
        except Exception as e:
            print(f"Error saving configuration: {str(e)}")
            return False