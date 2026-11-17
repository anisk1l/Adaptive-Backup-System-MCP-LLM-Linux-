#!/usr/bin/env python3
import subprocess

# Single entrypoint: tuner decides, then runs backup if safe
subprocess.run(["bash", "./run_adaptive.sh"], check=False)
