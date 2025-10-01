#!/usr/bin/env python3
import time

# Size of each allocation block in MB
BLOCK_SIZE_MB = 10
# How many blocks to allocate
NUM_BLOCKS = 20
# Delay between allocations (seconds)
DELAY = 2

blocks = []
print(f"Allocating {NUM_BLOCKS * BLOCK_SIZE_MB} MB total, in {BLOCK_SIZE_MB} MB chunks...")

for i in range(NUM_BLOCKS):
    # Allocate a block filled with zeros
    block = bytearray(BLOCK_SIZE_MB * 1024 * 1024)
    blocks.append(block)
    print(f"[{i+1}/{NUM_BLOCKS}] Allocated {BLOCK_SIZE_MB} MB")
    time.sleep(DELAY)

print("All allocations complete. Press Ctrl+C to exit and free memory.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting and freeing memory.")
