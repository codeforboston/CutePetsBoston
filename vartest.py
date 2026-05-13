import json
import sys
import traceback
from pathlib import Path
from datetime import datetime, timezone

def main():
    Path("my_file.txt").touch(exist_ok=True)
    with open("my_file.txt", "r+") as f:
        try:
            data = json.load(f)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Failed to load json file - {type(e).__name__}:{e}", file=sys.stderr)
            traceback.print_exc()
            data = {}
        f.seek(0)
        if "pet_list" not in data:
            data["pet_list"] = [{"name": "Spike", "id": 124, "timestamp": datetime.now(timezone.utc).isoformat()}]
        else:
            data["pet_list"].append({"name": "Spot", "id": 123, "timestamp": datetime.now(timezone.utc).isoformat()})
        json.dump(data, f)
        f.truncate()


if __name__ == "__main__":
    main()
