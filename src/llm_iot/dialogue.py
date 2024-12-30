import os
import requests
import json
from anthropic import Anthropic
from dotenv import load_dotenv
import readline  # Add this import at the top of the file

class IoTController:
    def __init__(self, server_url, api_model="claude-3-5-haiku-20241022"):
        load_dotenv()
        self.server_url = server_url
        self.anthropic = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.api_model = api_model
        self.api_structure = self._explore_api()

    def _explore_api(self):
        """Explore API structure starting from root"""
        structure = {}
        root_response = requests.get(f"{self.server_url}/").json()
        structure['root'] = root_response

        # Explore each link from root
        for endpoint, data in root_response['_links'].items():
            if endpoint != 'self':
                try:
                    response = requests.get(f"{self.server_url}{data['href']}").json()
                    structure[endpoint] = response
                except:
                    continue

        return structure

    def _get_function_call(self, user_input):
        """Get function call from Claude for user input"""
        system_prompt = f"""You are an IoT API assistant. Convert user commands to function calls of the Python requests library to send requests to the IoT server.
API structure: {json.dumps(self.api_structure, indent=2)}
Server URL: {self.server_url}

Respond only with the function call, no explanations."""

        message = self.anthropic.messages.create(
            model=self.api_model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_input}]
        )
        # DEBUG
        print(f"Claude response: {message.content[0].text}")
        return message.content[0].text

    def _convert_to_human_language(self, response):
        prompt = """Convert this IoT API JSON response to concise human language, focusing on the most important information.
        Don't print 'Here is the concise summary' or other explanations; print just the content:

{response}"""

        message = self.anthropic.messages.create(
            model=self.api_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt.format(response=json.dumps(response, indent=2))}]
        )
        return message.content[0].text


    def _format_response(self, response):
        if isinstance(response, dict):
            human_response = self._convert_to_human_language(response)
            return f"\n{human_response}"
        return f"\nResponse: {response}"


    def execute_command(self, function_call):
        # Execute request
        try:
            response = eval(function_call)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def run(self):
        """Main loop"""
        print("\033[1mIoT Controller started. Type 'quit' to exit.\033[0m")

        # Set up readline with history
        histfile = os.path.join(os.path.expanduser("~"), ".iot_controller_history")
        try:
            readline.read_history_file(histfile)
            readline.set_history_length(1000)  # Set maximum history length
        except FileNotFoundError:
            pass

        while True:
            try:
                user_input = input("\n>>> ")
                if user_input.lower() == 'quit':
                    break
                if user_input.lower() == 'help':
                    print(self.api_structure)
                    continue
                if user_input.lower() == '':
                    continue

                # Process command as before...
                function_call = self._get_function_call(user_input)
                response = self.execute_command(function_call)
                formatted_response = self._format_response(response)
                print(formatted_response)

            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
                continue
            except EOFError:
                break

        # Save history when exiting
        try:
            readline.write_history_file(histfile)
        except Exception as e:
            print(f"Error writing history file: {e}")

if __name__ == "__main__":
    #controller = IoTController("http://192.168.29.126")
    controller = IoTController("http://192.168.1.130")
    controller.run()