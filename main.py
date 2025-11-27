import os
import json
import random
from moviepy.editor import *
from google import genai
from google.cloud import texttospeech
from google.cloud import aiplatform # NEW LIBRARY
from PIL import Image # Pillow library for image handling (usually installed with moviepy dependencies)
import base64
from io import BytesIO

# --- CONFIGURATION (Remains the same) ---
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

# --- API KEYS & PATHS ---
# PEXELS_API_KEY is now useless and can be removed from secrets
GCP_SA_KEY_PATH = "gcp_service_account.json" 
PROJECT_ID = "ai-youtube-agent-479510" # Use your actual Project ID from the service account email

# --- 1. SETUP (Remains the same) ---
# ... setup_gcp_credentials function remains the same ...

# --- 2. GEMINI PRO SCRIPT AGENT (Remains the same) ---
# ... generate_script_and_materials function remains the same, but the prompt should remove the Pexels keyword request ...

# --- NEW: GENERATIVE IMAGE FUNCTION ---

def generate_visual_asset(keyword):
    """
    Uses the Vertex AI API (Imagen) to generate a custom, high-quality image 
    based on the script's keyword. This uses your GCP credit.
    """
    try:
        # Initialize the Vertex AI client
        aiplatform.init(project=PROJECT_ID, location="us-central1")
        
        # Define the prompt for the visual: Material vs Grinder
        prompt = f"Extreme close-up, dramatic photo of a strong angle grinder blade sparking against the material: '{keyword}'. Dark background, high contrast, vertical aspect ratio (9:16)."

        # Configuration for the image generation model (Imagen)
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
        
        # Save the generated image as a temporary placeholder MP4 (MoviePy needs a file path)
        temp_image_path = "temp_generated_image.png"
        image.save(temp_image_path)
        
        # Create a static video clip from the image
        return ImageClip(temp_image_path).set_duration(10).set_fps(24)

    except Exception as e:
        print(f"❌ ERROR: Generative AI (Vertex AI) failed: {e}. Falling back to default asset.")
        # FALLBACK: Use the placeholder video if AI generation fails
        PLACEHOLDER_PATH = "assets/placeholder.mp4" 
        if os.path.exists(PLACEHOLDER_PATH):
             clip = VideoFileClip(PLACEHOLDER_PATH).subclip(0, 10)
             return clip.fx(vfx.resize, newsize=(1080, 1920))
        else:
             raise FileNotFoundError(f"Placeholder video not found at {PLACEHOLDER_PATH}. You must have a fallback asset.")


# --- 3. PREMIUM GOOGLE CLOUD TTS (Remains the same) ---
# ... create_tts_audio function remains the same ...

# --- 4. VIDEO ASSEMBLY & UPLOAD (Adjusted to handle ImageClip) ---

def assemble_video(script_data, video_clip):
    # CRITICAL: If the clip is a static ImageClip, we need to convert it to a VideoClip
    if isinstance(video_clip, ImageClip):
        video_clip = video_clip.set_duration(10).set_fps(24) # Set it to a video clip with duration

    # The rest of the assembly logic (clips, text, audio) remains the same
    # ... (The assembly logic you currently have) ...
    # ...
    # This section needs to be re-added to Main.py, updated for the new structure
    # ...

    clips = []
    
    # BGM setup and rest of the assembly logic (Clip 1, Clip 2, Clip 3)
    # ... (Please ensure the full assemble_video body is in your final script) ...

    # Final assembly example:
    final_video = concatenate_videoclips(clips)
    
    # Audio mixing (assuming bgm_clip and other audio setup is handled)
    # ...
    
    return final_video

# --- 5. UPLOAD (Remains the same) ---
# ... get_authenticated_service and upload_to_youtube remain the same ...

# --- MAIN EXECUTION (Updated) ---
if __name__ == "__main__":
    # Ensure the script runs setup_gcp_credentials() and removes the old download_stock_clip call

    # 0. Setup Service Account Key
    if not setup_gcp_credentials():
        print("CRITICAL: Failed to load GCP credentials. Video generation may fail.")
        exit()

    # 1. Initialize Gemini Client
    # ... (client initialization remains the same) ...

    # 2. Execute Script, Assemble Video, and Upload
    script_data = generate_script_and_materials(client)
    
    # 3. Generate NEW VISUAL ASSET
    try:
        # Use generative AI for the visual asset
        visual_clip = generate_visual_asset(script_data['keyword'])
    except Exception as e:
        print(f"CRITICAL FAILURE: Could not generate visual asset. {e}")
        exit()

    # 4. Assemble Video (using the generated asset)
    # ... (The rest of the main execution logic) ...

    # The rest of the main execution logic must be adapted to use the new generate_visual_asset function.
    # The full Main.py body is too long to reiterate here, but ensure you replace the old download function 
    # with the new generate_visual_asset function and handle the ImageClip object correctly in assemble_video.
