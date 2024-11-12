from microdot import Microdot, Response
import network
import json
from machine import Pin, PWM, ADC
import time

class IoTServer:
    def __init__(self, config_file='config.json'):
        self.app = Microdot()
        self.leds = {}
        self.sensors = {}
        self.load_config(config_file)
        self.setup_routes()

    def load_config(self, config_file):
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
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

            print(f"Configuration loaded: {len(self.leds)} LEDs, {len(self.sensors)} sensors")
        except Exception as e:
            print(f"Error loading configuration: {str(e)}")
            raise

    def save_config(self):
        """Save current configuration back to JSON file"""
        config = {
            "wifi": self.wifi_config,
            "server": self.server_config,
            "leds": {},
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
            with open('config.json', 'w') as f:
                json.dump(config, f)
            print("Configuration saved successfully")
        except Exception as e:
            print(f"Error saving configuration: {str(e)}")

    def create_response(self, data, links=None):
        """Create HATEOAS response with data and links"""
        response = {
            "data": data,
            "_links": links or {}
        }
        return Response(
            json.dumps(response),
            headers={'Content-Type': 'application/json'}
        )

    def apply_calibration(self, raw_value, config):
        """Apply calibration to raw sensor value"""
        if config["type"] == "linear":
            m = config["params"]["m"]
            b = config["params"]["b"]
            return m * raw_value + b
        elif config["type"] == "polynomial":
            coeffs = config["params"]["coefficients"]
            result = 0
            for power, coeff in enumerate(coeffs):
                result += coeff * (raw_value ** power)
            return result
        return raw_value

    def connect_wifi(self):
        """Connect to WiFi network"""
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(self.wifi_config["ssid"], self.wifi_config["password"])

        max_wait = 10
        while max_wait > 0:
            if wlan.status() < 0 or wlan.status() >= 3:
                break
            max_wait -= 1
            print('Waiting for connection...')
            time.sleep(1)

        if wlan.status() != 3:
            raise RuntimeError('Network connection failed')
        else:
            print('Connected')
            status = wlan.ifconfig()
            print('IP:', status[0])

        return status[0]

    def setup_routes(self):
        """Setup all API routes"""

        @self.app.route('/')
        async def get_api_root(request):
            """Root endpoint providing API navigation"""
            links = {
                "self": {"href": "/"},
                "leds": {"href": "/leds"},
                "sensors": {"href": "/sensors"},
                "status": {"href": "/status"}
            }
            return self.create_response({"message": "Welcome to IoT API"}, links)

        @self.app.route('/leds')
        async def get_leds(request):
            """Get all LEDs with their metadata and available actions"""
            led_data = {}
            for led_id, led_info in self.leds.items():
                led_data[led_id] = {
                    "color": led_info["color"],
                    "location": led_info["location"],
                    "state": led_info["pin"].value(),
                    "_links": {
                        "self": {"href": f"/leds/{led_id}"},
                        "toggle": {"href": f"/leds/{led_id}/toggle"},
                    }
                }

            links = {
                "self": {"href": "/leds"},
                "filter_by_color": {"href": "/leds/filter?color={color}",
                                "templated": True},
                "filter_by_location": {"href": "/leds/filter?location={location}",
                                    "templated": True}
            }

            return self.create_response(led_data, links)

        @self.app.route('/leds/filter')
        async def filter_leds(request):
            """Filter LEDs by color or location"""
            color = request.args.get('color')
            location = request.args.get('location')

            filtered_leds = {}
            for led_id, led_info in self.leds.items():
                if ((color and led_info["color"] == color) or
                    (location and led_info["location"] == location) or
                    (not color and not location)):
                    filtered_leds[led_id] = {
                        "color": led_info["color"],
                        "location": led_info["location"],
                        "state": led_info["pin"].value(),
                        "_links": {
                            "self": {"href": f"/leds/{led_id}"},
                            "toggle": {"href": f"/leds/{led_id}/toggle"}
                        }
                    }

            links = {
                "self": {"href": f"/leds/filter?color={color or ''}&location={location or ''}"},
                "all_leds": {"href": "/leds"}
            }

            return self.create_response(filtered_leds, links)

        @self.app.route('/leds/<led_id>/toggle', methods=['POST'])
        async def toggle_led(request, led_id):
            """Toggle LED state"""
            if led_id not in self.leds:
                return self.create_response(
                    {"error": f"Invalid LED: {led_id}"},
                    {"all_leds": {"href": "/leds"}}
                )

            led = self.leds[led_id]["pin"]
            led.toggle()

            return self.create_response(
                {
                    "id": led_id,
                    "state": led.value(),
                    "color": self.leds[led_id]["color"],
                    "location": self.leds[led_id]["location"]
                },
                {
                    "self": {"href": f"/leds/{led_id}/toggle"},
                    "led": {"href": f"/leds/{led_id}"},
                    "all_leds": {"href": "/leds"}
                }
            )

        @self.app.route('/sensors')
        async def get_sensors(request):
            """Get all sensors with their metadata and available actions"""
            sensor_data = {}
            for sensor_id, sensor_info in self.sensors.items():
                sensor_data[sensor_id] = {
                    "type": sensor_info["type"],
                    "location": sensor_info["location"],
                    "unit": sensor_info["unit"],
                    "_links": {
                        "self": {"href": f"/sensors/{sensor_id}"},
                        "read": {"href": f"/sensors/{sensor_id}/value"},
                        "config": {"href": f"/sensors/{sensor_id}/config"}
                    }
                }

            links = {
                "self": {"href": "/sensors"},
                "filter_by_type": {"href": "/sensors/filter?type={type}",
                                "templated": True},
                "filter_by_location": {"href": "/sensors/filter?location={location}",
                                    "templated": True}
            }

            return self.create_response(sensor_data, links)

        @self.app.route('/sensors/filter')
        async def filter_sensors(request):
            """Filter sensors by type or location"""
            sensor_type = request.args.get('type')
            location = request.args.get('location')

            filtered_sensors = {}
            for sensor_id, sensor_info in self.sensors.items():
                if ((sensor_type and sensor_info["type"] == sensor_type) or
                    (location and sensor_info["location"] == location) or
                    (not sensor_type and not location)):
                    filtered_sensors[sensor_id] = {
                        "type": sensor_info["type"],
                        "location": sensor_info["location"],
                        "unit": sensor_info["unit"],
                        "_links": {
                            "self": {"href": f"/sensors/{sensor_id}"},
                            "read": {"href": f"/sensors/{sensor_id}/value"}
                        }
                    }

            links = {
                "self": {"href": f"/sensors/filter?type={sensor_type or ''}&location={location or ''}"},
                "all_sensors": {"href": "/sensors"}
            }

            return self.create_response(filtered_sensors, links)

        @self.app.route('/sensors/<sensor_id>/value')
        async def get_sensor_value(request, sensor_id):
            """Read calibrated sensor value"""
            if sensor_id not in self.sensors:
                return self.create_response(
                    {"error": f"Invalid sensor: {sensor_id}"},
                    {"all_sensors": {"href": "/sensors"}}
                )

            sensor_info = self.sensors[sensor_id]
            raw_value = sensor_info["pin"].read_u16()
            calibrated_value = self.apply_calibration(raw_value, sensor_info["config"])

            return self.create_response(
                {
                    "id": sensor_id,
                    "raw_value": raw_value,
                    "calibrated_value": calibrated_value,
                    "type": sensor_info["type"],
                    "location": sensor_info["location"],
                    "unit": sensor_info["unit"]
                },
                {
                    "self": {"href": f"/sensors/{sensor_id}/value"},
                    "sensor": {"href": f"/sensors/{sensor_id}"},
                    "config": {"href": f"/sensors/{sensor_id}/config"},
                    "all_sensors": {"href": "/sensors"}
                }
            )

        @self.app.route('/sensors/<sensor_id>/config', methods=['GET'])
        async def get_sensor_config(request, sensor_id):
            """Get sensor configuration"""
            if sensor_id not in self.sensors:
                return self.create_response(
                    {"error": f"Invalid sensor: {sensor_id}"},
                    {"all_sensors": {"href": "/sensors"}}
                )

            sensor_info = self.sensors[sensor_id]
            config_data = {
                "id": sensor_id,
                "type": sensor_info["type"],
                "unit": sensor_info["unit"],
                "config": sensor_info["config"],
                "example_conversion": {
                    "raw": 32768,  # Example mid-range value
                    "converted": self.apply_calibration(32768, sensor_info["config"])
                }
            }

            links = {
                "self": {"href": f"/sensors/{sensor_id}/config"},
                "sensor": {"href": f"/sensors/{sensor_id}"},
                "sensor_value": {"href": f"/sensors/{sensor_id}/value"},
                "update_config": {
                    "href": f"/sensors/{sensor_id}/config",
                    "method": "POST",
                    "templates": {
                        "linear": {
                            "type": "linear",
                            "params": {"m": "number", "b": "number"}
                        },
                        "polynomial": {
                            "type": "polynomial",
                            "params": {"coefficients": "array of numbers"}
                        }
                    }
                }
            }

            return self.create_response(config_data, links)

        @self.app.route('/sensors/<sensor_id>/config', methods=['POST'])
        async def update_sensor_config(request, sensor_id):
            """Update sensor configuration"""
            if sensor_id not in self.sensors:
                return self.create_response(
                    {"error": f"Invalid sensor: {sensor_id}"},
                    {"all_sensors": {"href": "/sensors"}}
                )

            try:
                new_config = json.loads(request.body)

                # Validate configuration
                if new_config["type"] not in ["linear", "polynomial"]:
                    raise ValueError("Invalid configuration type")

                if new_config["type"] == "linear":
                    if "m" not in new_config["params"] or "b" not in new_config["params"]:
                        raise ValueError("Linear calibration requires 'm' and 'b' parameters")
                elif new_config["type"] == "polynomial":
                    if "coefficients" not in new_config["params"]:
                        raise ValueError("Polynomial calibration requires 'coefficients' parameter")

                # Update configuration
                self.sensors[sensor_id]["config"] = new_config

                # Save configuration to file
                self.save_config()

                # Test new configuration with example value
                test_value = 32768  # Example mid-range value
                converted_value = self.apply_calibration(test_value, new_config)

                response_data = {
                    "message": "Configuration updated successfully",
                    "id": sensor_id,
                    "config": new_config,
                    "test_conversion": {
                        "raw": test_value,
                        "converted": converted_value
                    }
                }

                links = {
                    "self": {"href": f"/sensors/{sensor_id}/config"},
                    "sensor": {"href": f"/sensors/{sensor_id}"},
                    "read_value": {"href": f"/sensors/{sensor_id}/value"}
                }

                return self.create_response(response_data, links)
            except Exception as e:
                return self.create_response({"error": str(e)}, {})