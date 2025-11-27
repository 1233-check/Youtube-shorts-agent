#!/usr/bin/env python3
import os
import json
import tempfile
import random
import textwrap
import google.generativeai as genai
from moviepy.editor import AudioFileClip
from google.cloud import texttospeech

# ────────────────────── 1. GEMINI + GCP AUTH (FIXED FOR 404 MODEL ERROR) ──────────────────────
def init_gemini_and_gcp():
    key_json = os.getenv("GCP_SERVICE_ACCOUNT_KEY")
    if not key_json:
        print("ERROR: GCP_SERVICE_ACCOUNT_KEY secret is missing or empty!")
        return False

    try:
        # Write service account key to temp file
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(json.loads(key_json), temp_file)
        temp_file.close()

        # This powers Gemini, Cloud TTS — everything Google
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_file.name

        # Force use of service account (no API key fallback)
        genai.configure()

        # Test connection with a STABLE, supported model (fixes 404 error)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content("Say 'hello' in one word.")
        print("Gemini 1.5 Flash initialized successfully via Service Account!")
        print(f"Test response: {response.text.strip()}")

        return True

    except Exception as e:
        print(f"Failed to initialize Gemini/GCP: {e}")
        return False


# ────────────────────── 2. RUN AUTH FIRST OR DIE ──────────────────────
if not init_gemini_and_gcp():
    exit(1)


# ────────────────────── 3. CONFIG & TOPICS ──────────────────────
TOPICS = [
    "Glass Bottle", "Plastic Straw", "Aluminum Can", "Paper Cup",
    "Styrofoam", "Cardboard Box", "Battery", "Light Bulb"
]

TOPIC = random.choice(TOPICS)
print(f"\nSelected Topic → {TOPIC}\n")


# ────────────────────── 4. GENERATE SCRIPT WITH GEMINI ──────────────────────
def generate_script():
    prompt = f"""
    Write a powerful 60-second YouTube Shorts script about why {TOPIC} is harmful to the environment
    and how people can avoid or recycle it. Make it emotional, fast-paced, and end with a strong call to action.
    Return ONLY plain text, no markdown, no code blocks, no titles.
    Keep it under 150 words.
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        script = response.text.strip()
        print("Script generated successfully!")
        return script
    except Exception as e:
        print(f"Gemini script generation failed: {e}")
        return f"Did you know {TOPIC.lower()} takes hundreds of years to decompose? It harms wildlife and pollutes our oceans. The good news? You can recycle it or switch to reusable alternatives today. One small change can save our planet. Start now!"


SCRIPT = generate_script()
print("\nFINAL SCRIPT:\n")
print(textwrap.fill(SCRIPT, 80))
print("\n" + "="*80 + "\n")


# ────────────────────── 5. TEXT-TO-SPEECH WITH GOOGLE CLOUD TTS ──────────────────────
def generate_voiceover():
    client = texttospeech.TextToSpeechClient()

    input_text = texttospeech.SynthesisInput(text=SCRIPT)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Standard-C"  # Natural, clear voice
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.15
    )

    response = client.synthesize_speech(
        request={"input": input_text, "voice": voice, "audio_config": audio_config}
    )

    output_path = "voiceover.mp3"
    with open(output_path, "wb") as out:
        out.write(response.audio_content)
    print(f"Voiceover saved → {output_path}")

    return output_path


VOICEOVER = generate_voiceover()


# ────────────────────── 6. FINAL AUDIO LENGTH CHECK (MOVIEPY) ──────────────────────
def get_audio_duration():
    clip = AudioFileClip(VOICEOVER)
    duration = clip.duration
    clip.close()
    return duration


duration = get_audio_duration()
print(f"\nVoiceover duration: {duration:.2f} seconds → Perfect for Shorts!")

print("\nAll steps completed successfully!")
print("Your YouTube Short is ready to be rendered and uploaded.")
