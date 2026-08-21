import random

# Output file
output_file = "midi_sequence.txt"

num_lines = 250

with open(output_file, "w") as f:
    for i in range(num_lines):
        first = round(i * 5, 1)        # increases by 0.5
        second = random.randint(1, 10)  # rnd duration
        third = random.randint(1, 60)   # random note value
        fourth = 100                     # fixed

        f.write(f"{first},{second},{third},{fourth}\n")

print(f"✅ Created {num_lines} MIDI-style lines in {output_file}")
