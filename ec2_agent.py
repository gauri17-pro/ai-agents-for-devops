from strands import Agent, tool
from strands.models.ollama import OllamaModel
import boto3
import json

@tool   
def create_ec2_instance(
    instance_type: str = "t2.micro",
    ami_id: str = "ami-0f58b397bc5c1f2e8",
    instance_name: str = "MyStrandsInstance",
    region: str = "ap-south-1"
):
    """Creates an EC2 instance on AWS."""
    try:
        ec2 = boto3.client("ec2", region_name=region)

        response = ec2.run_instances(
            ImageId=ami_id,
            InstanceType=instance_type,
            MinCount=1,
            MaxCount=1,
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [{"Key": "Name", "Value": instance_name}]
                }
            ]
        )

        instance = response["Instances"][0]
        instance_id = instance["InstanceId"]

        return json.dumps({
            "status": "success",
            "instance_id": instance_id,
            "instance_type": instance["InstanceType"],
            "state": instance["State"]["Name"],
            "region": region
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        })


model = OllamaModel(
    model_id="gpt-oss:120b-cloud",  # ensure this matches `ollama list`
    host="http://localhost:11434"
)

agent = Agent(
    model=model, 
    tools=[create_ec2_instance],
    system_prompt=(
        "You are an AWS automation agent. When calling create_ec2_instance, "
        "NEVER pass any arguments. Always call it with zero arguments so that "
        "the function's own default values are used. Do not infer, assume, or "
        "supply any parameter values yourself."
    )
)
user_input = input("Enter your message: ")

agent(user_input)
