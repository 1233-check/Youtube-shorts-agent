import os
import json
import random
from moviepy.editor import *
from google import genai
from google.cloud import texttospeech
from google.auth.exceptions import DefaultCredentialsError

# --- YOUTUBE API IMPORTS ---
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- CONFIGURATION ---
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

# --- API KEYS (Loaded from GitHub Secrets) ---
# NOTE: GEMINI_API_KEY is used as a fallback. 
# GCP_SA_KEY is required for premium TTS/Pro models.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY") 
GCP_SA_KEY_PATH = "gcp_service_account.json" # Path to your Service Account Key file

# --- 1. SEO & SCRIPT AGENT (GEMINI 2.5 PRO) ---

def generate_script_and_materials(client):
    """Uses the powerful Gemini 2.5 Pro model for script and SEO generation."""
    
    MATERIAL_CATEGORIES = [
        "FOOD (e.g., Frozen Steak, Cheese Block)", 
        "PLASTIC/RUBBER (e.g., Bowling Ball, Car Tire)", 
        "BUILDING MATERIAL (e.g., Brick, Ceramic Tile)", 
        "HOUSEHOLD ITEM (e.g., Old Smartphone, Cast Iron Skillet)"
    ]
    
    prompt = f"""
    You are an expert viral YouTube Shorts SEO & Script Agent using the high-end Gemini 2.5 Pro model. 
    Your goal is maximum retention and monetization. Your output MUST be ONLY a single JSON block.

    **Goal:** Select ONE material category and choose a unique, highly surprising material. 
    **Material Categories:** {', '.join(MATERIAL_CATEGORIES)}
    
    **CRITICAL HOOK INSTRUCTION:** The FIRST SCRIPT SEGMENT MUST create a massive curiosity gap and grab the viewer's attention in under 3 seconds.
    
    Your output MUST be a single JSON object with the following structure:
    {{
        "material_name": "The unique material selected",
        "keyword": "A single, strong keyword for stock footage",
        "prediction": "PASS or FAIL",
        "clip_duration": 4, 
        "script_segments": [
            {{"text": "Viral, high-energy hook/question designed to stop the scroll.", "type": "hook"}}, 
            {{"text": "The material reveal.", "type": "reveal"}},
            {{"text": "Suspenseful commentary on the grind.", "type": "grind_action"}},
            {{"text": "The final outcome and CTA.", "type": "outcome"}}
        ],
        "seo_metadata": {{
            "title": "Short, catchy title optimized for US search (MUST be under 60 characters).",
            "description": "Exciting description with a strong comment CTA.",
            "tags": "A comma-separated list of 10-15 high-value, relevant tags for the US audience"
        }}
    }}
    """
    try:
        # Use the powerful Gemini 2.5 Pro model
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt
        )
        return json.loads(response.text.strip())
    except Exception as e:
        print(f"Error generating script: {e}")
        # FALLBACK SCRIPT (Using simplified model if Pro fails)
        return {
            "material_name": "Glass Bottle",
            "keyword": "glass bottle breaking",
            "prediction": "FAIL",
            "clip_duration": 5,
            "script_segments": [
                {"text": "This challenge should be absolutely impossible. Watch this!", "type": "hook"},
                {"text": "Testing the mighty Glass Bottle.", "type": "reveal"},
                {"text": "The sparks are flying and the glass is holding strong.", "type": "grind_action"},
                {"text": "The bottle wins. Nothing even happened! Comment what's next!", "type": "outcome"}
            ],
            "seo_metadata": {
                "title": "Angle Grinder vs Glass Bottle! (Impossible?) #shorts",
                "description": "Can the angle grinder cut this glass bottle? Watch this impossible challenge! What should we test next? Comment below!",
                "tags": "#AngleGrinder, #GlassBottle, #Challenge, #DIY, #PowerTools, #shorts, #Experiment"
            }
        }

# --- 2. PREMIUM GOOGLE CLOUD TTS (FOR HIGH RETENTION) ---

def create_tts_audio(text, filename="temp_audio.mp3"):
    """
    Uses Google Cloud Text-to-Speech (Wavenet) for premium, human-quality voiceover,
    billing against the GCP credit.
    """
    try:
        # Authentication is handled by setting the GOOGLE_APPLICATION_CREDENTIALS 
        # environment variable using the Service Account Key file (Source 1.4, 1.5)
        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Use a high-quality WaveNet voice with an American English accent
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Wavenet-D",  # A high-quality male voice
            ssml_gender=texttospeech.SsmlVoiceGender.MALE
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        with open(filename, "wb") as out:
            out.write(response.audio_content)
        
        return AudioFileClip(filename)
        
    except DefaultCredentialsError:
        print("ERROR: GCP Service Account Credentials not found. Falling back to gTTS (lower quality).")
        # FALLBACK to standard gTTS if Service Account fails
        from gtts import gTTS
        try:
            tts = gTTS(text=text, lang='en', tld='us') 
            tts.save(filename)
            return AudioFileClip(filename)
        except Exception as e:
            print(f"gTTS fallback failed: {e}")
            return None


def download_stock_clip(keyword, duration):
    """
    Loads placeholder/stock video. Corrects aspect ratio to 9:16.
    """
    PLACEHOLDER_PATH = "assets/placeholder.mp4" 
    if os.path.exists(PLACEHOLDER_PATH):
         clip = VideoFileClip(PLACEHOLDER_PATH).subclip(0, duration)
         return clip.fx(vfx.resize, newsize=(1080, 1920))
    else:
         raise FileNotFoundError(f"Placeholder video not found at {PLACEHOLDER_PATH}.")

def create_text_overlay(text, duration, is_result=False, result_status="FAIL"):
    """Creates a stylized TextClip."""
    font = 'Arial-Bold'
    if is_result:
        text_content = f"{text}\n{'✅ CUT' if result_status == 'PASS' else '❌ NO CUT'}"
        font_size = 80
        fill_color = 'yellow'
    else:
        text_content = text
        font_size = 70
        fill_color = 'white'
    
    txt_clip = TextClip(
        text_content, 
        fontsize=font_size, 
        color=fill_color,
        font=font, 
        bg_color='black',
        stroke_color='black',
        stroke_width=2
    ).set_pos(('center', 'center')).set_duration(duration)
    return txt_clip

def assemble_video(script_data, video_clip):
    """Assembles video with high-retention cuts and premium audio."""
    
    clips = []
    
    BGM_PATH = "assets/bgm.mp3"
    try:
        bgm_clip = AudioFileClip(BGM_PATH).volumex(0.15) 
    except Exception:
        bgm_clip = None

    # Clip 1: THE HOOK (2.5 seconds)
    hook_clip_duration = 2.5 
    hook_audio = create_tts_audio(script_data['script_segments'][0]['text'])
    material_text_clip = create_text_overlay(script_data['material_name'], hook_clip_duration, is_result=False)
    hook_video_clip = video_clip.subclip(0, hook_clip_duration).set_audio(hook_audio)
    
    final_hook_clip = CompositeVideoClip([hook_video_clip, material_text_clip.set_start(0).set_duration(hook_clip_duration)], size=(1080, 1920)) 
    clips.append(final_hook_clip)

    # Clip 2: Grind Action and Tension (4.0-5.0 seconds)
    action_clip_duration = script_data['clip_duration'] 
    action_text = " ".join([seg['text'] for seg in script_data['script_segments'] if seg['type'] in ['reveal', 'grind_action']])
    action_audio = create_tts_audio(action_text)

    action_video_clip = video_clip.subclip(hook_clip_duration, hook_clip_duration + action_clip_duration).set_audio(action_audio)
    clips.append(action_video_clip)
    
    # Clip 3: Result Reveal (2.0 seconds)
    result_clip_duration = 2 
    result_text_clip = create_text_overlay(script_data['material_name'], result_clip_duration, is_result=True, result_status=script_data['prediction'])
    outcome_audio = create_tts_audio(script_data['script_segments'][3]['text'])
    
    reveal_video_clip = action_video_clip.to_ImageClip(t=action_video_clip.duration - 0.1).set_duration(result_clip_duration).set_audio(outcome_audio)
    final_reveal_clip = CompositeVideoClip([reveal_video_clip, result_text_clip.set_start(0).set_duration(result_clip_duration)], size=(1080, 1920))
    clips.append(final_reveal_clip)

    # Concatenate and mix audio
    final_video = concatenate_videoclips(clips)
    if bgm_clip:
        bgm_looped = afx.audio_loop(bgm_clip, duration=final_video.duration)
        final_video = final_video.set_audio(CompositeAudioClip([final_video.audio, bgm_looped]))

    return final_video

# --- 3. YOUTUBE UPLOAD ---

def get_authenticated_service():
    """Authenticates non-interactively using the Refresh Token from GitHub Secrets."""
    creds = Credentials(
        token=None,
        refresh_token=os.environ.get("YOUTUBE_REFRESH_TOKEN"),
        client_id=os.environ.get("YOUTUBE_CLIENT_ID"),
        client_secret=os.environ.get("YOUTUBE_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES
    )
    if creds.refresh_token:
        creds.refresh(Request())
    else:
        raise ValueError("YOUTUBE_REFRESH_TOKEN is missing or invalid.")
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=creds)

def upload_to_youtube(video_path, script_data):
    """Uploads the video using the SEO metadata."""
    
    try:
        youtube = get_authenticated_service()
    except Exception as e:
        print(f"❌ AUTHENTICATION FAILED. Cannot upload: {e}")
        return

    seo_data = script_data['seo_metadata']
    body = dict(
        snippet=dict(
            title=seo_data['title'],
            description=seo_data['description'],
            tags=[tag.strip() for tag in seo_data['tags'].split(',')],
            categoryId='28' # Science & Technology
        ),
        status=dict(
            privacyStatus='public' # Change this to 'unlisted' or 'private' for testing!
        )
    )
    media_file = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media_file
    )
    response = insert_request.execute()
    print(f"✅ Upload successful! Video ID: {response['id']}")


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    
    # 0. Setup Service Account Key file from GitHub Secret (for GCP services)
    # The JSON key must be stored in a GitHub Secret (e.g., GCP_SERVICE_ACCOUNT_KEY)
    # and written to a file that the library can read for authentication.
    gcp_sa_json = os.environ.get("GCP_SERVICE_ACCOUNT_KEY")
    if gcp_sa_json:
        try:
            with open(GCP_SA_KEY_PATH, "w") as f:
                f.write(gcp_sa_json)
            # Set the environment variable that the Google Cloud libraries look for
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GCP_SA_KEY_PATH
        except Exception as e:
            print(f"Failed to write GCP Service Account file: {e}. Proceeding with API Key fallback.")

    # 1. Initialize Gemini Client (Uses environment variable or service account credentials)
    try:
        # Client will try to use the GOOGLE_APPLICATION_CREDENTIALS first
        client = genai.Client()
    except Exception:
        # Fallback to the GEMINI_API_KEY if service account fails
        client = genai.Client(api_key=GEMINI_API_KEY)

    # 2. Execute Script, Assemble Video, and Upload
    script_data = generate_script_and_materials(client)
    print(f"✅ Script Generated for Material: {script_data['material_name']}")
    
    try:
        video_clip = download_stock_clip(script_data['keyword'], script_data['clip_duration'] + 5)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        exit()

    final_video_clip = assemble_video(script_data, video_clip)
    
    OUTPUT_FILE = f"output/{script_data['material_name'].replace(' ', '_').lower()}_short.mp4"
    if not os.path.exists('output'):
        os.makedirs('output')

    print(f"🎥 Rendering video to {OUTPUT_FILE}...")
    final_video_clip.write_videofile(
        OUTPUT_FILE, 
        codec='libx264', audio_codec='aac', temp_audiofile='temp-audio.m4a', 
        remove_temp=True, fps=30, bitrate='5000k'
    )
    print("✅ Video Render Complete.")

    upload_to_youtube(OUTPUT_FILE, script_data)
    print("--- Daily AI Agent Run Finished ---")
