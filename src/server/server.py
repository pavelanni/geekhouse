from microdot import Microdot
from config_handler import ConfigHandler
from routes import Routes
from utils import connect_wifi

class IoTServer:
    def __init__(self, config_file='config.json'):
        # Initialize components
        self.app = Microdot()
        self.config_handler = ConfigHandler(config_file)

        # Load configuration
        self.config_handler.load_config()

        # Setup routes
        self.routes = Routes(self.app, self.config_handler)

    def run(self):
        """Start the server"""
        try:
            # Connect to WiFi
            ip = connect_wifi(
                self.config_handler.wifi_config["ssid"],
                self.config_handler.wifi_config["password"]
            )

            # Start the server
            port = self.config_handler.server_config.get('port', 80)
            print(f'Starting HATEOAS-enabled IoT server on http://{ip}:{port}')
            self.app.run(port=port, debug=True)

        except Exception as e:
            print(f"Server error: {str(e)}")
            raise

# Create boot.py or main.py with this code:
if __name__ == '__main__':
    server = IoTServer()
    server.run()