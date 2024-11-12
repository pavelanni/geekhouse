from utils import create_response, apply_calibration
import json

class Routes:
    def __init__(self, app, config_handler):
        self.app = app
        self.config = config_handler
        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/')
        async def get_api_root(request):
            """Root endpoint providing API navigation"""
            links = {
                "self": {"href": "/"},
                "leds": {"href": "/leds"},
                "sensors": {"href": "/sensors"},
                "status": {"href": "/status"}
            }
            return create_response({"message": "Welcome to IoT API"}, links)

        @self.app.route('/leds')
        async def get_leds(request):
            """Get all LEDs with their metadata and available actions"""
            led_data = {}
            for led_id, led_info in self.config.leds.items():
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

            return create_response(led_data, links)

        @self.app.route('/leds/filter')
        async def filter_leds(request):
            """Filter LEDs by color or location"""
            color = request.args.get('color')
            location = request.args.get('location')

            filtered_leds = {}
            for led_id, led_info in self.config.leds.items():
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

            return create_response(filtered_leds, links)

        @self.app.route('/leds/<led_id>/toggle', methods=['POST'])
        async def toggle_led(request, led_id):
            """Toggle LED state"""
            if led_id not in self.config.leds:
                return create_response(
                    {"error": f"Invalid LED: {led_id}"},
                    {"all_leds": {"href": "/leds"}}
                )

            led = self.config.leds[led_id]["pin"]
            led.toggle()

            return create_response(
                {
                    "id": led_id,
                    "state": led.value(),
                    "color": self.config.leds[led_id]["color"],
                    "location": self.config.leds[led_id]["location"]
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
            for sensor_id, sensor_info in self.config.sensors.items():
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

            return create_response(sensor_data, links)

        @self.app.route('/sensors/filter')
        async def filter_sensors(request):
            """Filter sensors by type or location"""
            sensor_type = request.args.get('type')
            location = request.args.get('location')

            filtered_sensors = {}
            for sensor_id, sensor_info in self.config.sensors.items():
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

            return create_response(filtered_sensors, links)

        @self.app.route('/sensors/<sensor_id>/value')
        async def get_sensor_value(request, sensor_id):
            """Read calibrated sensor value"""
            if sensor_id not in self.config.sensors:
                return create_response(
                    {"error": f"Invalid sensor: {sensor_id}"},
                    {"all_sensors": {"href": "/sensors"}}
                )

            sensor_info = self.config.sensors[sensor_id]
            raw_value = sensor_info["pin"].read_u16()
            calibrated_value = apply_calibration(raw_value, sensor_info["config"])

            return create_response(
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
            if sensor_id not in self.config.sensors:
                return create_response(
                    {"error": f"Invalid sensor: {sensor_id}"},
                    {"all_sensors": {"href": "/sensors"}}
                )

            sensor_info = self.config.sensors[sensor_id]
            config_data = {
                "id": sensor_id,
                "type": sensor_info["type"],
                "unit": sensor_info["unit"],
                "config": sensor_info["config"],
                "example_conversion": {
                    "raw": 32768,
                    "converted": apply_calibration(32768, sensor_info["config"])
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

            return create_response(config_data, links)

        @self.app.route('/sensors/<sensor_id>/config', methods=['POST'])
        async def update_sensor_config(request, sensor_id):
            """Update sensor configuration"""
            if sensor_id not in self.config.sensors:
                return create_response(
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
                self.config.sensors[sensor_id]["config"] = new_config

                # Save the updated configuration
                self.config.save_config()

                return create_response(
                    {"message": "Configuration updated successfully"},
                    {"self": {"href": f"/sensors/{sensor_id}/config"}}
                )
            except Exception as e:
                return create_response(
                    {"error": str(e)},
                    {"self": {"href": f"/sensors/{sensor_id}/config"}}
                )