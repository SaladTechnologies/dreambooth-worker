import os

log_level = os.getenv("LOG_LEVEL", "INFO").upper()

# Directory where training data is stored
instance_dir = os.getenv("INSTANCE_DIR", "/instance_images")
class_dir = os.getenv("CLASS_DIR", "/class_images")

# Directory where training output is stored
output_dir = os.getenv("OUTPUT_DIR", "/output")

api_base_url = os.getenv("API_URL", None)
api_key = os.getenv("API_KEY", None)

if api_base_url is None or api_key is None:
    raise ValueError("API_URL and API_KEY must be set.")

os.makedirs(instance_dir, exist_ok=True)
os.makedirs(class_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

# Salad Machine and Container Group IDs
salad_machine_id = os.getenv("SALAD_MACHINE_ID", None)
salad_container_group_id = os.getenv("SALAD_CONTAINER_GROUP_ID", None)
salad_container_group_name = os.getenv("SALAD_CONTAINER_GROUP_NAME", None)
salad_organization_name = os.getenv("SALAD_ORGANIZATION_NAME", None)
salad_project_name = os.getenv("SALAD_PROJECT_NAME", None)


heartbeat_interval = int(os.getenv("HEARTBEAT_INTERVAL", "30"))

wandb_api_key = os.getenv("WANDB_API_KEY", None)
