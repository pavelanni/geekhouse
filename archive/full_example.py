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
led = Pin('LED', Pin.OUT)  # Onboard LED
servo = PWM(Pin(15))       # Servo on GPIO 15
servo.freq(50)             # 50Hz frequency for servo
stepper_pins = [
    Pin(16, Pin.OUT),      # IN1
    Pin(17, Pin.OUT),      # IN2
    Pin(18, Pin.OUT),      # IN3
    Pin(19, Pin.OUT)       # IN4
]
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

def set_servo_angle(angle):
    """Convert angle (0-180) to duty cycle and set servo position"""
    duty = int(((angle / 180) * 6553) + 1638)  # Convert 0-180 to duty cycle
    servo.duty_u16(duty)

def move_stepper(direction, steps):
    """Move stepper motor in specified direction for given steps"""
    sequence = [
        [1,0,0,0],
        [1,1,0,0],
        [0,1,0,0],
        [0,1,1,0],
        [0,0,1,0],
        [0,0,1,1],
        [0,0,0,1],
        [1,0,0,1]
    ]

    for _ in range(steps):
        for step in sequence[::direction]:
            for i in range(4):
                stepper_pins[i].value(step[i])
            time.sleep_ms(2)

# API Routes
@app.route('/sensors')
def get_sensors(request):
    """Read values from sensors"""
    temp_voltage = temp_sensor.read_u16() * (3.3 / 65535)
    temperature = 27 - (temp_voltage - 0.706) / 0.001721
    light = light_sensor.read_u16()

    return Response(json.dumps({
        'temperature': temperature,
        'light_level': light
    }), headers={'Content-Type': 'application/json'})

@app.route('/status')
def get_status(request):
    """Get system status"""
    return Response(json.dumps({
        'led': led.value(),
        'uptime': time.ticks_ms()
    }), headers={'Content-Type': 'application/json'})

@app.post('/led')
def toggle_led(request):
    """Toggle LED state"""
    led.toggle()
    return Response(json.dumps({
        'led_state': led.value()
    }), headers={'Content-Type': 'application/json'})

@app.post('/servo/<angle>')
def control_servo(request, angle):
    """Control servo position"""
    try:
        angle = int(angle)
        if 0 <= angle <= 180:
            set_servo_angle(angle)
            return Response(json.dumps({
                'status': 'success',
                'angle': angle
            }), headers={'Content-Type': 'application/json'})
        else:
            return Response(json.dumps({
                'status': 'error',
                'message': 'Angle must be between 0 and 180'
            }), status_code=400, headers={'Content-Type': 'application/json'})
    except ValueError:
        return Response(json.dumps({
            'status': 'error',
            'message': 'Invalid angle value'
        }), status_code=400, headers={'Content-Type': 'application/json'})

@app.post('/stepper/<direction>/<steps>')
def control_stepper(request, direction, steps):
    """Control stepper motor"""
    try:
        steps = int(steps)
        if direction not in ['cw', 'ccw']:
            raise ValueError('Invalid direction')
        if steps <= 0:
            raise ValueError('Steps must be positive')

        direction_value = 1 if direction == 'cw' else -1
        move_stepper(direction_value, steps)

        return Response(json.dumps({
            'status': 'success',
            'direction': direction,
            'steps': steps
        }), headers={'Content-Type': 'application/json'})
    except ValueError as e:
        return Response(json.dumps({
            'status': 'error',
            'message': str(e)
        }), status_code=400, headers={'Content-Type': 'application/json'})

def main():
    # Connect to WiFi
    ip = connect_wifi()
    print(f'Starting server on http://{ip}:80')

    # Start the server
    app.run(port=80)

if __name__ == '__main__':
    main()