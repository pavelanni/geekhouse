from microdot import Microdot, Response
import network
import json
from json.decoder import JSONDecodeError
from machine import Pin, PWM, ADC
import time

# WiFi credentials
SSID = 'Your WiFi SSID'
PASSWORD = 'Your WiFi Password'

# Initialize Microdot
app = Microdot()

# Hardware setup with metadata and calibration configurations
leds = {
    "yellow_roof": {
        "pin": Pin(2, Pin.OUT),
        "color": "yellow",
        "location": "roof",
        "type": "led"
    },
    "white_garden": {
        "pin": Pin(3, Pin.OUT),
        "color": "white",
        "location": "garden",
        "type": "led"
    }
}

sensors = {
    "roof_water": {
        "pin": ADC(1),
        "type": "water",
        "location": "roof",
        "unit": "level",
        "config": {
            "type": "linear",
            "params": {"m": 1, "b": 0}  # y = mx + b
        }
    },
    "roof_light": {
        "pin": ADC(0),
        "type": "light",
        "location": "roof",
        "unit": "lux",
        "config": {
            "type": "polynomial",
            "params": {"coefficients": [0, 0.1]}  # y = 0.1x
        }
    },
    "temp_internal": {
        "pin": ADC(4),
        "type": "temperature",
        "location": "internal",
        "unit": "celsius",
        "config": {
            "type": "linear",
            "params": {"m": 0.0124, "b": -20.5}  # Default calibration for internal temp
        }
    },
    "garden_light": {
        "pin": ADC(26),
        "type": "light",
        "location": "garden",
        "unit": "lux",
        "config": {
            "type": "polynomial",
            "params": {"coefficients": [0, 0.1]}  # y = 0.1x
        }
    }
}

def apply_calibration(raw_value, config):
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

# [Previous connect_wifi and create_response functions remain the same]

@app.route('/sensors/<sensor_id>/config', methods=['GET'])
async def get_sensor_config(request, sensor_id):
    """Get sensor configuration"""
    if sensor_id not in sensors:
        return create_response(
            {"error": f"Invalid sensor: {sensor_id}"},
            {"all_sensors": {"href": "/sensors"}}
        )

    sensor_info = sensors[sensor_id]
    config_data = {
        "id": sensor_id,
        "type": sensor_info["type"],
        "unit": sensor_info["unit"],
        "config": sensor_info["config"],
        "example_conversion": {
            "raw": 32768,  # Example mid-range value
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

@app.route('/sensors/<sensor_id>/config', methods=['POST'])
async def update_sensor_config(request, sensor_id):
    """Update sensor configuration"""
    if sensor_id not in sensors:
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
        sensors[sensor_id]["config"] = new_config

        # Test new configuration with example value
        test_value = 32768  # Example mid-range value
        converted_value = apply_calibration(test_value, new_config)

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

        return create_response(response_data, links)

    except (JSONDecodeError, KeyError, ValueError) as e:
        return create_response(
            {
                "error": "Invalid configuration format",
                "details": str(e),
                "templates": {
                    "linear": {
                        "type": "linear",
                        "params": {"m": 1.0, "b": 0.0}
                    },
                    "polynomial": {
                        "type": "polynomial",
                        "params": {"coefficients": [0, 1, 0]}  # y = x
                    }
                }
            },
            {
                "self": {"href": f"/sensors/{sensor_id}/config"},
                "sensor": {"href": f"/sensors/{sensor_id}"}
            }
        )

# Update the sensor value endpoint to use calibration
@app.route('/sensors/<sensor_id>/value')
async def get_sensor_value(request, sensor_id):
    """Read calibrated sensor value"""
    if sensor_id not in sensors:
        return create_response(
            {"error": f"Invalid sensor: {sensor_id}"},
            {"all_sensors": {"href": "/sensors"}}
        )

    sensor_info = sensors[sensor_id]
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

def connect_wifi():
    """Connect to WiFi network"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)

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

def create_response(data, links=None):
    """Create HATEOAS response with data and links"""
    response = {
        "data": data,
        "_links": links or {}
    }
    return Response(
        json.dumps(response),
        headers={'Content-Type': 'application/json'}
    )

@app.route('/')
async def get_api_root(request):
    """Root endpoint providing API navigation"""
    links = {
        "self": {"href": "/"},
        "leds": {"href": "/leds"},
        "sensors": {"href": "/sensors"},
        "status": {"href": "/status"}
    }
    return create_response({"message": "Welcome to IoT API"}, links)

@app.route('/leds')
async def get_leds(request):
    """Get all LEDs with their metadata and available actions"""
    led_data = {}
    for led_id, led_info in leds.items():
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

@app.route('/sensors')
async def get_sensors(request):
    """Get all sensors with their metadata and available actions"""
    sensor_data = {}
    for sensor_id, sensor_info in sensors.items():
        sensor_data[sensor_id] = {
            "type": sensor_info["type"],
            "location": sensor_info["location"],
            "unit": sensor_info["unit"],
            "_links": {
                "self": {"href": f"/sensors/{sensor_id}"},
                "read": {"href": f"/sensors/{sensor_id}/value"}
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

@app.route('/leds/filter')
async def filter_leds(request):
    """Filter LEDs by color or location"""
    color = request.args.get('color')
    location = request.args.get('location')

    filtered_leds = {}
    for led_id, led_info in leds.items():
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

@app.route('/sensors/filter')
async def filter_sensors(request):
    """Filter sensors by type or location"""
    sensor_type = request.args.get('type')
    location = request.args.get('location')

    filtered_sensors = {}
    for sensor_id, sensor_info in sensors.items():
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

@app.route('/leds/<led_id>/toggle', methods=['POST'])
async def toggle_led(request, led_id):
    """Toggle LED state"""
    if led_id not in leds:
        return create_response(
            {"error": f"Invalid LED: {led_id}"},
            {"all_leds": {"href": "/leds"}}
        )

    led = leds[led_id]["pin"]
    led.toggle()

    return create_response(
        {
            "id": led_id,
            "state": led.value(),
            "color": leds[led_id]["color"],
            "location": leds[led_id]["location"]
        },
        {
            "self": {"href": f"/leds/{led_id}/toggle"},
            "led": {"href": f"/leds/{led_id}"},
            "all_leds": {"href": "/leds"}
        }
    )


@app.route('/status')
async def get_status(request):
    """Get system status with HATEOAS links"""
    led_states = {led_id: info["pin"].value() for led_id, info in leds.items()}
    status_data = {
        "leds": led_states,
        "uptime": time.ticks_ms()
    }

    links = {
        "self": {"href": "/status"},
        "leds": {"href": "/leds"},
        "sensors": {"href": "/sensors"}
    }

    return create_response(status_data, links)

def main():
    ip = connect_wifi()
    print(f'Starting HATEOAS-enabled IoT server on http://{ip}:80')
    app.run(port=80)

if __name__ == '__main__':
    main()