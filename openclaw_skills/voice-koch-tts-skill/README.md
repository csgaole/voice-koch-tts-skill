# voice-koch-tts-skill-v1.0

OpenClaw skill wrapper for:

- microphone recording
- local ASR
- LLM intent understanding
- Koch robot execution
- TTS playback

Non-robot requests:

- weather questions return live weather by voice
- unrelated chat returns a short spoken reply without moving the robot

## Run

```bash
bash run_voice_control_tts.sh --local-only
```

## Options

```bash
bash run_voice_control_tts.sh --local-only --dry-run
bash run_voice_control_tts.sh --local-only --mute-tts
```
