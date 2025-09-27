#!/usr/bin/env python3
"""
txt_to_midi_mido_v2.py

Usage:
    python3 txt_to_midi_mido_v2.py input.txt output.mid [BPM]

Supports formats (auto-detected):
1) CSV per line: onset_seconds,duration_seconds,pitch,velocity
2) Sequential: pitch duration_seconds [velocity]   (onsets cumulative)
3) Rhythmic tokens: pitch duration_token [velocity] where duration_token in w,h,q,e,s,t (needs BPM)

Examples:
CSV:
  0.0,0.5,60,100
  0.5,0.5,C4,100

Sequential:
  C4 0.5 100
  D4 0.5

Rhythmic (default BPM=120):
  C4 q 100
  D4 q
"""

import sys
import re
from mido import Message, MidiFile, MidiTrack, MetaMessage, bpm2tempo

NOTE_TO_SEMITONE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
DURATION_TOKENS = {'w': 4.0, 'h': 2.0, 'q': 1.0, 'e': 0.5, 's': 0.25, 't': 0.125}
NOTE_RE = re.compile(r'^([A-Ga-g])([#b♯♭]?)(-?\d+)$')

def note_name_to_number(name: str) -> int:
    name = name.strip()
    m = NOTE_RE.match(name)
    if not m:
        raise ValueError(f"Invalid note name: {name!r}")
    letter, accidental, octave_s = m.groups()
    letter = letter.upper()
    semitone = NOTE_TO_SEMITONE[letter]
    if accidental in ('#', '♯'):
        semitone += 1
    elif accidental in ('b', '♭'):
        semitone -= 1
    octave = int(octave_s)
    midi = (octave + 1) * 12 + semitone  # C-1 -> 0
    return midi

def parse_pitch(token: str) -> int:
    tok = token.strip()
    # integer-like?
    if re.fullmatch(r'-?\d+', tok):
        return int(tok)
    return note_name_to_number(tok)

def detect_format(lines):
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith('#'):
            continue
        if ',' in s:
            return 'csv'
        parts = s.split()
        if len(parts) >= 2:
            try:
                float(parts[1])
                return 'sequential'
            except ValueError:
                return 'rhythmic'
    return 'sequential'

def read_notes(path, bpm_for_rhythm=120.0):
    with open(path, 'r', encoding='utf-8') as f:
        raw = f.readlines()
    lines = [ln.rstrip('\n') for ln in raw]

    fmt = detect_format(lines)
    notes = []  # (onset_seconds, duration_seconds, pitch_midi, velocity)
    try:
        if fmt == 'csv':
            for i, ln in enumerate(lines, 1):
                s = ln.strip()
                if not s or s.startswith('#'):
                    continue
                parts = [p.strip() for p in s.split(',')]
                if len(parts) < 3:
                    raise ValueError(f"CSV line {i}: need at least onset,duration,pitch -> {s!r}")
                onset = float(parts[0])
                dur = float(parts[1]) if parts[1] != '' else 0.5  # default 0.5s if empty
                if parts[2] == '':
                    raise ValueError(f"Missing pitch on line {i}: {s!r}")
                pitch = parse_pitch(parts[2])
                vel = int(parts[3]) if len(parts) >= 4 and parts[3] != '' else 100
                notes.append((onset, dur, pitch, vel))
        elif fmt == 'sequential':
            t = 0.0
            for i, ln in enumerate(lines, 1):
                s = ln.strip()
                if not s or s.startswith('#'):
                    continue
                parts = s.split()
                if len(parts) < 2:
                    raise ValueError(f"Sequential line {i}: need pitch and duration_seconds -> {s!r}")
                pitch = parse_pitch(parts[0])
                dur = float(parts[1])
                vel = int(parts[2]) if len(parts) >= 3 and parts[2] != '' else 100
                notes.append((t, dur, pitch, vel))
                t += dur
        else:  # rhythmic
            beat_time = 0.0
            for i, ln in enumerate(lines, 1):
                s = ln.strip()
                if not s or s.startswith('#'):
                    continue
                parts = s.split()
                if len(parts) < 2:
                    raise ValueError(f"Rhythmic line {i}: need pitch and duration_token -> {s!r}")
                pitch = parse_pitch(parts[0])
                token = parts[1].lower()
                if token not in DURATION_TOKENS:
                    raise ValueError(f"Rhythmic line {i}: unknown duration token {token!r} in {s!r}")
                beats = DURATION_TOKENS[token]
                onset_seconds = beat_time * 60.0 / bpm_for_rhythm
                dur_seconds = beats * 60.0 / bpm_for_rhythm
                vel = int(parts[2]) if len(parts) >= 3 and parts[2] != '' else 100
                notes.append((onset_seconds, dur_seconds, pitch, vel))
                beat_time += beats
    except Exception as e:
        raise RuntimeError(f"Error parsing file '{path}': {e}")

    notes.sort(key=lambda x: x[0])
    return notes, fmt

def notes_to_midi(notes, out_path, bpm=120.0, ticks_per_beat=480, program=101):
    midi = MidiFile(ticks_per_beat=ticks_per_beat)
    track = MidiTrack()
    midi.tracks.append(track)

    tempo = bpm2tempo(bpm)
    track.append(MetaMessage('set_tempo', tempo=tempo, time=0))
    track.append(Message('program_change', program=program, time=0))

    ticks_per_second = ticks_per_beat * (bpm / 60.0)

    # build on/off events (tick, type, pitch, vel)
    events = []
    for onset, dur, pitch, vel in notes:
        start_tick = int(round(onset * ticks_per_second))
        end_tick = int(round((onset + dur) * ticks_per_second))
        events.append((start_tick, 'on', pitch, vel))
        events.append((end_tick, 'off', pitch, 0))

    # sort: by tick asc; if same tick, OFF before ON
    events.sort(key=lambda e: (e[0], 0 if e[1] == 'off' else 1))

    last_tick = 0
    for tick, typ, pitch, vel in events:
        delta = tick - last_tick
        if delta < 0:
            delta = 0
        if typ == 'on':
            msg = Message('note_on', note=int(pitch), velocity=int(vel), time=delta)
        else:
            msg = Message('note_off', note=int(pitch), velocity=int(vel), time=delta)
        track.append(msg)
        last_tick = tick

    midi.save(out_path)

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 txt_to_midi_mido_v2.py input.txt output.mid [BPM]")
        sys.exit(1)
    in_path = sys.argv[1]
    out_path = sys.argv[2]
    bpm = float(sys.argv[3]) if len(sys.argv) >= 4 else 120.0

    try:
        notes, fmt = read_notes(in_path, bpm_for_rhythm=bpm)
    except Exception as e:
        print("❌ Parsing failed:", e)
        sys.exit(2)

    if not notes:
        print("No notes parsed from file.")
        sys.exit(3)

    try:
        notes_to_midi(notes, out_path, bpm=bpm)
    except Exception as e:
        print("❌ MIDI write failed:", e)
        sys.exit(4)

    print(f"✅ Wrote {len(notes)} notes (detected format: {fmt}) to {out_path} at {bpm} BPM")

if __name__ == "__main__":
    main()
