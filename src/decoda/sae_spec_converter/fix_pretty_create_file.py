import sys
from datetime import datetime, timezone

if __name__ == "__main__":
    output = []
    for line in sys.stdin:
        if "parse_args" in line:
            continue
        if "import pretty_j1939.describe" in line:
            line = "#" + line
        output.append(line)

    output = output[:-2]
    for line in output:
        sys.stdout.write(line)
