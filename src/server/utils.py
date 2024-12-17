from microdot import Response
import json
import network
import time

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

def apply_calibration(raw_value, config):
    """Apply calibration to raw sensor value"""
    if not config or "type" not in config:
        return raw_value

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

def connect_wifi(ssid, password):
    """Connect to WiFi network"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)

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