from microdot import Microdot, Response
import network
import json
from machine import Pin, PWM, ADC
import time

# WiFi credentials
SSID = 'Your WiFi SSID'
PASSWORD = 'Your WiFi Password'

# Initialize Microdot
app = Microdot()

# Hardware setup
leds = {"yellow": Pin(2, Pin.OUT), "white": Pin(3, Pin.OUT)}
sensors_water = {"roof": ADC(1)}
sensors_light = {"roof": ADC(0)}

temp_sensor = ADC(4)       # Internal temperature sensor
light_sensor = ADC(26)     # Light sensor on GPIO 26

def connect_wifi():
    """Connect to WiFi network"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)

    # Wait for connection
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

# API Routes
@app.route('/sensors/light/<id>')
async def get_sensors_light(request, id):
    """Read values from sensors"""

    sensor = sensors_light.get(id)
    if sensor == None:
        return Response(json.dumps({
            'light': f"Invalid sensor ID: {id}"
        }), headers={'Content-Type': 'application/json'})

    level = sensor.read_u16()
    return Response(json.dumps({
        'light': f"ID: {id}, level: {level}"
    }), headers={'Content-Type': 'application/json'})

@app.route('/sensors/water/<id>')
async def get_sensors_water(request, id):
    """Read values from sensors"""
    sensor = sensors_water.get(id)
    if sensor == None:
        return Response(json.dumps({
            'water': f"Invalid sensor ID: {id}"
        }), headers={'Content-Type': 'application/json'})

    level = sensor.read_u16()
    return Response(json.dumps({
        'water': f"ID: {id}, level: {level}"
    }), headers={'Content-Type': 'application/json'})

@app.route('/status')
async def get_status(request):
    """Get system status"""
    led_status = {k:leds[k].value() for k in leds}
    return Response(json.dumps({
        'leds': led_status,
        'uptime': time.ticks_ms()
    }), headers={'Content-Type': 'application/json'})

@app.post('/leds/<id>')
async def toggle_led(request, id):
    print(f"Setting LED {id}")
    """Toggle LED state"""
    led = leds.get(id)
    if led == None:
        return Response(json.dumps({
            'led_state': f"Invalid LED: {id}"
        }), headers={'Content-Type': 'application/json'})

    led.toggle()
    return Response(json.dumps({
        'led_state': led.value()
    }), headers={'Content-Type': 'application/json'})


def main():
    # Connect to WiFi
    ip = connect_wifi()
    print(f'Starting server on http://{ip}:80')

    # Start the server
    app.run(port=80)

if __name__ == '__main__':
    main()