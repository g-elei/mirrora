import json
import os

def validate():
    scenarios_path = os.path.join("evaluation", "scenarios.json")
    if not os.path.exists(scenarios_path):
        print(f"Error: {scenarios_path} not found.")
        return False

    with open(scenarios_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    scenarios = data.get("scenarios", [])
    if not scenarios:
        print("Warning: No scenarios found to validate.")
        return False

    for idx, sc in enumerate(scenarios):
        if "id" not in sc or "prompt" not in sc:
            print(f"Validation failed at scenario index {idx}: missing 'id' or 'prompt'.")
            return False

    print("All scenarios validated successfully!")
    return True

if __name__ == "__main__":
    validate()