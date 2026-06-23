import json
import sys

print(json.dumps(json.load(sys.stdin), indent=2, sort_keys=True))
