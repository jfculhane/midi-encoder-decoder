import mido
import csv
import sys
import os

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

def note_name(note_number):
    """Convert MIDI note number to note name with octave."""
    octave = (note_number // 12) - 1
    note = NOTE_NAMES[note_number % 12]
    return f"{note}{octave}"

def midi_to_csv(midi_path, output_path=None):
    """
    Parse a MIDI file and save musical information in CSV format:
    onset_seconds, duration_seconds, pitch, velocity
    """
    if not output_path:
        base, _ = os.path.splitext(midi_path)
        output_path = base + ".csv"

    try:
        mid = mido.MidiFile(midi_path)
    except Exception as e:
        print(f"Error reading MIDI file: {e}")
        return

    tempo = 500000  # default tempo (µs per beat)
    notes = []      # will store tuples of (onset, duration, pitch, velocity)

    # Active notes dictionary: {note_number: (onset_time, velocity)}
    active_notes = {}

    for track in mid.tracks:
        absolute_time = 0
        for msg in track:
            absolute_time += msg.time
            if msg.type == "set_tempo":
                tempo = msg.tempo
            elif msg.type == "note_on" and msg.velocity > 0:
                # Note pressed
                onset = mido.tick2second(absolute_time, mid.ticks_per_beat, tempo)
                active_notes[msg.note] = (onset, msg.velocity)
            elif msg.type in ("note_off", "note_on") and msg.velocity == 0:
                # Note released
                if msg.note in active_notes:
                    onset, velocity = active_notes.pop(msg.note)
                    offset = mido.tick2second(absolute_time, mid.ticks_per_beat, tempo)
                    duration = offset - onset
                    notes.append((onset, duration, note_name(msg.note), velocity))

    # Write CSV
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        """writer.writerow(["onset_seconds", "duration_seconds", "pitch", "velocity"])"""
        for n in notes:
            writer.writerow(n)

    print(f"CSV file saved as: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python midi_to_csv.py <file.mid> [output.csv]")
    else:
        midi_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        midi_to_csv(midi_file, output_file)
