"""Print the Space's API so you can see endpoint names, parameters and model choices."""
import os
from dotenv import load_dotenv
from gradio_client import Client

load_dotenv()
client = Client(os.getenv("SPACE_ID", "OpenMOSS-Team/MOSS-SoundEffect-v2.0"), token=os.getenv("HF_TOKEN") or None)
client.view_api()
