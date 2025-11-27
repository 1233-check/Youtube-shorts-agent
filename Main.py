import os
import json
import random
import requests
from google import genai
from moviepy.editor import *
from gtts import gTTS

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
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY") 

# --- 1. SEO & SCRIPT AGENT (US-TARGETED, HIGH-HOOK) ---

def generate_script_and_materials(client):
    """Uses Gemini to generate the cutting challenge details, prioritizing variety, hook, and US SEO."""
    
    MATERIAL_CATEGORIES = [
        "FOOD (e.g., Frozen Steak, Cheese Block, Watermelon, Brick of Instant Noodles)", 
        "PLASTIC/RUBBER (e.g., Car Tire, Hockey Puck, Rubber Boot, Bowling Ball)", 
        "BUILDING MATERIAL (e.g., Drywall, Ceramic Tile, Brick, Mortar)", 
        "FABRIC/PAPER (e.g., Stack of Magazines, Denim, Thick Rope, Phonebook)",
        "HOUSEHOLD ITEM (e.g., Old Smartphone, Cast Iron Skillet, Baseball Bat, Toaster)"
    ]
    
    prompt = f"""
    You are an expert viral YouTube Shorts SEO & Script Agent focused on the 'cutting challenge' niche (Angle Grinder vs. Material).
    Your output MUST be ONLY a single JSON block. Do not add any text, comments, or markdown outside of the JSON block.

    **Goal:** Select ONE material category and choose a unique, surprising material. DO NOT repeat materials used previously.
    **Material Categories:** {', '.join(MATERIAL_CATEGORIES)}
    
    **Tone/Audience:** Use high-energy, American English slang, and focus on curiosity/shock factor.
    
    **CRITICAL HOOK INSTRUCTION:** The FIRST SCRIPT SEGMENT MUST create a massive curiosity gap and grab the viewer's attention in under 3 seconds. DO NOT use generic phrases.
    
    Your output MUST be a single JSON object with the following structure:
    {{
        "material_name": "The unique material selected (e.g., Bowling Ball)",
        "material_category": "The category used (e.g., PLASTIC/RUBBER)",
        "keyword": "A single, strong keyword for stock footage (e.g., bowling ball, grinding plastic)",
        "prediction": "The expected result: PASS or FAIL",
        "clip_duration": 4, 
        "script_segments": [
            {{"text": "A viral, high-energy hook/question designed to stop the scroll.", "type": "hook"}}, 
            {{"text": "The material reveal.", "type": "reveal"}},
            {{"text": "A brief, suspenseful commentary on the grind.", "type": "grind_action"}},
            {{"text": "The final outcome.", "type": "outcome"}}
        ],
        "seo_metadata": {{
            "title": "Short, catchy title optimized for US search (MUST be under 60 characters). Include the material name and #shorts.",
            "description": "A brief, exciting description (under 200 characters). MUST include a question CTA to encourage comments for engagement.",
            "tags": "A comma-separated list of 10-15 high-value, relevant tags for the US audience (e.g., #WillItCut, #AngleGrinder, #Challenge, #shorts)"
        }}
    }}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        # Safely parse the JSON output from the model
        return json.loads(response.text.strip())
    except Exception as e:
        print(f"Error generating script: {e}")
        # FALLBACK SCRIPT
        return {
            "material_name": "Glass Bottle",
            "material_category": "HOUSEHOLD ITEM",
            "keyword": "glass bottle breaking",
            "prediction": "FAIL",
            "clip_duration": 5,
            "script_segments": [
                {"text": "This challenge should be absolutely impossible. Watch this!", "type": "hook"},
                {"text": "Testing the mighty Glass Bottle.", "type": "reveal"},
                {"text": "The sparks are flying and the glass is holding strong.", "type": "grind_action"},
                {"text": "The bottle wins. Nothing even happened!", "type": "outcome"}
            ],
            "seo_metadata": {
                "title": "Angle Grinder vs Glass Bottle! (Impossible?) #shorts",
                "description": "Can the angle grinder cut this glass bottle? Watch this impossible challenge! What should we test next? Comment below! #WillItCut #AngleGrinder",
                "tags": "#AngleGrinder, #GlassBottle, #Challenge, #DIY, #PowerTools, #shorts, #Experiment, #Cutting"
            }
        }

# --- 2. US VOICEOVER & VIDEO ASSET FUNCTIONS ---

def create_tts_audio(text, filename="temp_audio.mp3", accent='us'):
    """Uses gTTS with the 'us' TLD for a free American English accent."""
    try:
        tts = gTTS(text=text, lang='en', tld=accent)
        tts.save(filename)
        return AudioFileClip(filename)
    except Exception as e:
        print(f"gTTS error: {e}")
        return None

def download_stock_clip(keyword, duration):
    """
    Placeholder: Uses Pexels API key (if implemented) or placeholder. 
    Corrects aspect ratio to 9:16.
    """
    PLACEHOLDER_PATH = "assets/placeholder.mp4" 
    
    # --- PEXELS API LOGIC WOULD GO HERE (Using requests library) ---
    # For now, rely on local placeholder
    
    if os.path.exists(PLACEHOLDER_PATH):
         # CRITICAL FIX: Ensure video is 9:16 (1080x1920) to prevent MoviePy compositing crash
         clip = VideoFileClip(PLACEHOLDER_PATH).subclip(0, duration)
         return clip.fx(vfx.resize, newsize=(1080, 1920))
    else:
         raise FileNotFoundError(f"Placeholder video not found at {PLACEHOLDER_PATH}. Please add a default vertical clip for the agent.")

def create_text_overlay(text, duration, is_result=False, result_status="FAIL"):
    """Creates a stylized TextClip (fast cuts, bold look)."""
    font = 'Arial-Bold'
    
    if is_result:
        # Bold, high-contrast text for the final reveal
        text_content = f"{text}\n{'✅ CUT' if result_status == 'PASS' else '❌ NO CUT'}"
        font_size = 80
        fill_color = 'yellow'
    else:
        # Standard text for the material name
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
    """Assembles video with fast cuts, text overlays, and background music for high retention."""
    
    clips = []
    
    # --- ENHANCEMENT: BACKGROUND MUSIC SETUP ---
    BGM_PATH = "assets/bgm.mp3"
    try:
        # Load BGM clip and set low volume
        bgm_clip = AudioFileClip(BGM_PATH).volumex(0.15) 
    except Exception:
        print("Warning: Background music file not found. Video will have no music.")
        bgm_clip = None

    # Clip 1: THE HOOK (2.5 seconds)
    hook_clip_duration = 2.5 
    hook_audio = create_tts_audio(script_data['script_segments'][0]['text'])
    material_text_clip = create_text_overlay(
        script_data['material_name'], 
        hook_clip_duration, 
        is_result=False
    )
    hook_video_clip = video_clip.subclip(0, hook_clip_duration).set_audio(hook_audio)
    final_hook_clip = CompositeVideoClip([
        hook_video_clip, 
        material_text_clip.set_start(0).set_duration(hook_clip_duration)
    ], size=(1080, 1920)) 
    clips.append(final_hook_clip)

    # Clip 2: Grind Action and Tension (4.0-5.0 seconds)
    action_clip_duration = script_data['clip_duration'] 
    action_text = " ".join([seg['text'] for seg in script_data['script_segments'] if seg['type'] in ['reveal', 'grind_action']])
    action_audio = create_tts_audio(action_text)
    action_video_clip = video_clip.subclip(hook_clip_duration, hook_clip_duration + action_clip_duration).set_audio(action_audio)
    clips.append(action_video_clip)
    
    # Clip 3: Result Reveal (2.0 seconds)
    result_clip_duration = 2 
    result_text_clip = create_text_overlay(
        script_data['material_name'], 
        result_clip_duration, 
        is_result=True, 
        result_status=script_data['prediction']
    )
    outcome_audio = create_tts_audio(script_data['script_segments'][3]['text'])
    
    # Use a static frame from the end of the action clip for the reveal
    reveal_video_clip = action_video_clip.to_ImageClip(t=action_video_clip.duration - 0.1).set_duration(result_clip_duration).set_audio(outcome_audio)
    final_reveal_clip = CompositeVideoClip([
        reveal_video_clip, 
        result_text_clip.set_start(0).set_duration(result_clip_duration)
    ], size=(1080, 1920))
    clips.append(final_reveal_clip)

    # Concatenate all clips
    final_video = concatenate_videoclips(clips)
    
    # --- APPLY BGM TO FINAL VIDEO ---
    if bgm_clip:
        bgm_looped = afx.audio_loop(bgm_clip, duration=final_video.duration)
        final_video = final_video.set_audio(CompositeAudioClip([final_video.audio, bgm_looped]))

    return final_video

# --- 3. YOUTUBE UPLOAD (Non-Interactive) ---

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
        raise ValueError("YOUTUBE_REFRESH_TOKEN is missing or invalid. Check GitHub Secrets.")

    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=creds)


def upload_to_youtube(video_path, script_data):
    """Uploads the video using the SEO metadata."""
    
    try:
        youtube = get_authenticated_service()
    except Exception as e:
        print(f"❌ AUTHENTICATION FAILED. Cannot upload: {e}")
        return

    seo_data = script_data['seo_metadata']
    
    # Prepare the video resource body
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

    print(f"🚀 Uploading with SEO Title: {seo_data['title']}")

    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media_file
    )
    
    response = insert_request.execute()
    
    print(f"✅ Upload successful! Video ID: {response['id']}")


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    if not all([GEMINI_API_KEY, os.environ.get("YOUTUBE_CLIENT_ID")]):
        print("Error: Critical API keys not set. Cannot proceed.")
        exit()

    # 1. Initialize Gemini Client
    client = genai.Client(api_key=GEMINI_API_KEY)

    # 2. Generate Script and SEO Metadata
    script_data = generate_script_and_materials(client)
    print(f"✅ Script Generated for Material: {script_data['material_name']}")
    
    # 3. Download/Load Stock Video Clip
    try:
        video_clip = download_stock_clip(
            script_data['keyword'], 
            script_data['clip_duration'] + 5 
        )
    except FileNotFoundError as e:
        print(f"❌ {e}")
        exit()

    # 4. Assemble the Video
    final_video_clip = assemble_video(script_data, video_clip)
    
    # 5. Render and Save the File
    OUTPUT_FILE = f"output/{script_data['material_name'].replace(' ', '_').lower()}_short.mp4"
    if not os.path.exists('output'):
        os.makedirs('output')

    print(f"🎥 Rendering video to {OUTPUT_FILE}...")
    final_video_clip.write_videofile(
        OUTPUT_FILE, 
        codec='libx264',
        audio_codec='aac', 
        temp_audiofile='temp-audio.m4a', 
        remove_temp=True,
        fps=30,
        bitrate='5000k'
    )
    print("✅ Video Render Complete.")

    # 6. Upload to YouTube
    upload_to_youtube(OUTPUT_FILE, script_data)

    print("--- Daily AI Agent Run Finished ---")