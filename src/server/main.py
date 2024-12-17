from server import IoTServer

def main():
    try:
        # Create and run server with default config file
        server = IoTServer('config.json')
        server.run()
    except Exception as e:
        print(f"Application error: {str(e)}")
        # In production, you might want to implement a retry mechanism
        # or fallback configuration

if __name__ == '__main__':
    main()