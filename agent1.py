from strands import Agent
from strands_tools import http_request

agent = Agent(model="apac.anthropic.claude-sonnet-4-20250514-v1:0")
print(agent.model)  # Add this line to see default model

user_input = input("Enter your message: ")
agent(user_input)