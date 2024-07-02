import yaml

def load_yaml(path):
    try:
        with open(path, 'r') as file:
            content = yaml.safe_load(file)
            return content
    except yaml.YAMLError as e:
        raise ValueError(f"Error loading YAML file '{path}': {e}")
    except Exception as e:
        raise ValueError(f"Unexpected error loading file '{path}': {e}")


