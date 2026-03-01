from strands import Agent
from strands.models.ollama import OllamaModel
from strands_tools import http_request

# Create an Ollama model instance
ollama_model = OllamaModel(
    host="http://localhost:11434",  # Ollama server address
    model_id="gpt-oss:120b-cloud"               # Specify which model to use
)

system_prompt = '''
You are a helpful assistant that provides information and answers questions respectfully.
You can use the following tool to make HTTP requests and make API calls
'''

# Create an agent using the Ollama model
agent = Agent(model=ollama_model, system_prompt=system_prompt, tools=[http_request])

# Ask from the user
user_input = input("Enter your message: ")

# Use the agent
agent(user_input)