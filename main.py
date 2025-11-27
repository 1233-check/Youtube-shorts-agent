import os
import json
import random
from moviepy.editor import *
from google import genai
from google.cloud import texttospeech
from google.cloud import aiplatform 
from google.auth.exceptions import DefaultCredentialsError
from PIL import Image 
from io import BytesIO
import base64

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

# --- API KEYS & PATHS ---
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY") 
GCP_SA_KEY_PATH = "gcp_service_account.json" 
# CRITICAL: Use your actual Project ID from the Service Account email
PROJECT_ID = "ai-youtube-agent-479510" 

# --- 1. SERVICE ACCOUNT SETUP (Fixes NameError by defining function early) ---

def setup_gcp_credentials():
    """
    Writes the Service Account JSON secret to a file for authentication.
    This must be defined BEFORE being called in __main__.
    """
    gcp_sa_json = os.environ.get("GCP_SERVICE_ACCOUNT_KEY")
    if gcp_sa_json:
        try:
            # Write the JSON content to a temporary file
            with open(GCP_SA_KEY_PATH, "w") as f:
                f.write(gcp_sa_json)
            # Set the environment variable that Google Cloud libraries look for
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GCP_SA_KEY_PATH
            print("✅ GCP Service Account credentials prepared.")
            return True
        except Exception as e:
            print(f"❌ ERROR: Failed to write GCP Service Account file: {e}")
            return False
    return False

# --- 2. SEO & SCRIPT AGENT (GEMINI 2.5 PRO) ---

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
    Your output MUST be ONLY a single JSON block. Do not add any text, comments, or markdown outside of the JSON block.

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
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt
        )
        # Attempt to parse the response; if it fails (e.g., empty string), we go to the fallback
        return json.loads(response.text.strip())
    except Exception as e:
        print(f"❌ ERROR generating script with Gemini 2.5 Pro: {e}")
        # FALLBACK SCRIPT 
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

# --- 3. PREMIUM GOOGLE CLOUD TTS ---

def create_tts_audio(text, filename="temp_audio.mp3"):
    """
    Uses Google Cloud Text-to-Speech (Wavenet) for premium, human-quality voiceover.
    Requires GOOGLE_APPLICATION_CREDENTIALS environment variable to be set.
    """
    try:
        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # High-quality WaveNet voice with an American English accent
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Wavenet-D", 
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
        
    except Exception as e:
        print(f"❌ ERROR: Premium TTS failed ({e}). Returning silent clip.")
        # Return a 1-second silent clip to prevent the moviepy audio mix from crashing
        return AudioClip(lambda t: 0, duration=1).set_fps(44100)

# --- 4. GENERATIVE IMAGE ASSET (Vertex AI/Imagen) ---

def generate_visual_asset(keyword):
    """
    Uses the Vertex AI API (Imagen) to generate a custom, high-quality image 
    based on the script's keyword.
    """
    try:
        # Initialize the Vertex AI client
        aiplatform.init(project=PROJECT_ID, location="us-central1")
        
        prompt = f"Extreme close-up, dramatic photo of a strong angle grinder blade sparking against the material: '{keyword}'. Dark background, high contrast, vertical aspect ratio (9:16)."

        model = aiplatform.Model.list(filter='display_name="imagegeneration"')[0]
        
        response = model.generate_images(
            prompt=prompt,
            config=dict(
                number_of_images=1,
                aspect_ratio="9:16",
                output_mime_type="image/jpeg",
                guidance_scale=10,
                number_of_steps=50
            )
        )
        
        # Decode the image data from the response
        encoded_image = response.generated_images[0].image.image_bytes
        image_data = base64.b64decode(encoded_image)
        image = Image.open(BytesIO(image_data))
        
        # Save the generated image as a temporary placeholder (MoviePy needs a file path)
        temp_image_path = "temp_generated_image.png"
        image.save(temp_image_path)
        
        # Return as a MoviePy ImageClip
        return ImageClip(temp_image_path).set_fps(24)

    except Exception as e:
        print(f"❌ ERROR: Generative AI (Vertex AI) failed: {e}. Falling back to default asset.")
        # FALLBACK: Use the placeholder video if AI generation fails
        PLACEHOLDER_PATH = "assets/placeholder.mp4" 
        if os.path.exists(PLACEHOLDER_PATH):
             clip = VideoFileClip(PLACEHOLDER_PATH).subclip(0, 10)
             return clip.fx(vfx.resize, newsize=(1080, 1920))
        else:
             # TYPO FIXED HERE: Placeholder video not found at correct path
             raise FileNotFoundError(f"CRITICAL: Placeholder video not found at {PLACEHOLDER_PATH}. Cannot assemble video.")

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

def assemble_video(script_data, visual_clip):
    """Assembles video with high-retention cuts and premium audio."""
    
    clips = []
    
    # BGM setup
    BGM_PATH = "assets/bgm.mp3"
    try:
        bgm_clip = AudioFileClip(BGM_PATH).volumex(0.15) 
    except Exception:
        bgm_clip = None

    # Ensure the visual clip has a duration for slicing
    if isinstance(visual_clip, ImageClip):
        visual_clip = visual_clip.set_duration(10).set_fps(24) 
        
    # Clip 1: THE HOOK (2.5 seconds)
    hook_clip_duration = 2.5 
    hook_audio = create_tts_audio(script_data['script_segments'][0]['text'])
    material_text_clip = create_text_overlay(script_data['material_name'], hook_clip_duration, is_result=False)
    hook_video_clip = visual_clip.subclip(0, hook_clip_duration).set_audio(hook_audio)
    
    final_hook_clip = CompositeVideoClip([hook_video_clip, material_text_clip.set_start(0).set_duration(hook_clip_duration)], size=(1080, 1920)) 
    clips.append(final_hook_clip)

    # Clip 2: Grind Action and Tension (4.0-5.0 seconds)
    action_clip_duration = script_data['clip_duration'] 
    action_text = " ".join([seg['text'] for seg in script_data['script_segments'] if seg['type'] in ['reveal', 'grind_action']])
    action_audio = create_tts_audio(action_text)

    action_video_clip = visual_clip.subclip(hook_clip_duration, hook_clip_duration + action_clip_duration).set_audio(action_audio)
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
    
    # Audio mixing
    if bgm_clip:
        bgm_looped = afx.audio_loop(bgm_clip, duration=final_video.duration)
        final_audio_track = CompositeAudioClip([final_video.audio, bgm_looped])
        final_video = final_video.set_audio(final_audio_track)

    return final_video

# --- 5. YOUTUBE UPLOAD (Remains the same) ---

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
            privacyStatus='public' # Set to 'unlisted' for safety during testing
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
    
    # 0. Setup Service Account Key (CRITICAL: Must be run first)
    setup_successful = setup_gcp_credentials()
    
    # 1. Initialize Gemini Client (Uses the simpler API Key for stability)
    try:
        api_key_from_secret = os.environ.get("GEMINI_API_KEY")
        if not api_key_from_secret:
            raise ValueError("GEMINI_API_KEY secret is missing.")
            
        client = genai.Client(api_key=api_key_from_secret)
        print("✅ Gemini Client initialized using API Key.")
        
    except Exception as e:
        print(f"❌ Failed to initialize Gemini Client: {e}")
        print("Please ensure your GEMINI_API_KEY secret is correct.")
        exit()

    # 2. Verify GCP readiness for premium services
    if not setup_successful:
        print("CRITICAL: Failed to load GCP Service Account credentials. Cannot use premium TTS/Vertex AI.")
        exit()

    # 3. Execute Script
    script_data = generate_script_and_materials(client)
    print(f"✅ Script Generated for Material: {script_data['material_name']}")
    
    # 4. Generate NEW VISUAL ASSET
    try:
        visual_clip = generate_visual_asset(script_data['keyword'])
    except FileNotFoundError as e:
        print(f"❌ {e}")
        exit()

    # 5. Assemble Video 
    final_video_clip = assemble_video(script_data, visual_clip)
    
    # 6. Render and Save the File
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

    # 7. Upload to YouTube
    upload_to_youtube(OUTPUT_FILE, script_data)
    print("--- Daily AI Agent Run Finished ---")
