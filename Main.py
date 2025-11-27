import feedparser
import tweepy
import google.generativeai as genai
import time
import random
import logging
import sys
from datetime import datetime

# ==========================================
# 1. PASTE YOUR KEYS HERE
# ==========================================
# --- GEMINI KEY ---

GEMINI_API_KEY = "AIzaSyCRwqluvtkUPix8GBQE-OatNRXt5nEcsCo"



# --- TWITTER/X KEYS ---

TWITTER_API_KEY = "BNiGzOXIT3mS43UrO8nTdhQaO"

TWITTER_API_SECRET = "WpcTNQfP0OGPWLodSHdVGllGGNtWK0J6uqoFwE1rQdplAGBUjS"

ACCESS_TOKEN = "863212626796589056-Rg70ROni1RZczHw9RZHqQdi5629t70x"

ACCESS_SECRET = "AFTPwNm1OYfn97alcYsJJN9Cf80Tm6LdRnQ7o18TRsgO5"

# RSS Feed for Bollywood News (Google News India - High Traffic)
RSS_URL = "https://news.google.com/rss/search?q=Bollywood+gossip+OR+Box+Office+India+OR+Indian+Film+Celebrity&hl=en-IN&gl=IN&ceid=IN:en"

# ==========================================
# 2. SETUP & LOGGING
# ==========================================
# Configures a log file and prints status to the screen
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_log.txt"),
        logging.StreamHandler(sys.stdout)
    ]
)

genai.configure(api_key=GEMINI_API_KEY)

# ==========================================
# 3. INTELLIGENCE FUNCTIONS
# ==========================================
def get_twitter_conn():
    """Initializes the Twitter client"""
    return tweepy.Client(
        consumer_key=TWITTER_API_KEY, consumer_secret=TWITTER_API_SECRET,
        access_token=ACCESS_TOKEN, access_secret=ACCESS_SECRET
    )

def get_bolly_news():
    """Fetches a random top story from RSS"""
    logging.info("🍿 Checking RSS feed for new gossip...")
    try:
        feed = feedparser.parse(RSS_URL)
        if feed.entries:
            # Pick one random story from top 7 for unique timing
            story = random.choice(feed.entries[:7]) 
            logging.info(f"Found Story: {story.title}")
            return f"Headline: {story.title}. Summary: {story.summary}"
    except Exception as e:
        logging.error(f"RSS Parsing Error: {e}")
    return None

def generate_tweet(news_context):
    """Uses Gemini to write the tweet with personality"""
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction="""
        You are a viral Bollywood Twitter influencer. 
        Task: Rewrite the provided news into a dramatic, sarcastic Hinglish tweet.
        
        Rules:
        - Must mix Hindi and English (Hinglish slang is mandatory).
        - Use dramatic words like: 'Bawal', 'Scene', 'Bhai', 'Queen', 'Flop', 'Blockbuster', 'Khatam'.
        - NO hashtags.
        - Max 280 characters.
        - Be controversial or highly supportive to spark engagement.
        """
    )
    response = model.generate_content(news_context)
    return response.text.strip()

# ==========================================
# 4. THE SELF-HEALING LOOP (24/7)
# ==========================================
def run_bot():
    logging.info("--- BOLLYWOOD BOT INITIATING ---")
    client = get_twitter_conn()

    while True:
        try:
            # --- ACTION PHASE ---
            news = get_bolly_news()
            
            if news:
                tweet = generate_tweet(news)
                logging.info(f"📝 Generated Draft: {tweet}")
                
                # Final Safety Check (Self-Correction)
                if len(tweet) > 280:
                    tweet = tweet[:277] + "..."
                
                # POST
                client.create_tweet(text=tweet)
                logging.info("✅ TWEET POSTED SUCCESSFULLY!")
                
            else:
                logging.warning("❌ No fresh gossip found on this cycle.")

            # --- SLEEP (Post 6-7 times a day) ---
            # Wait time: 3.5 hours +/- 15 mins (12600 seconds = 3.5 hours)
            sleep_seconds = 12600 + random.randint(-900, 900)
            
            wake_up_time = datetime.fromtimestamp(datetime.now().timestamp() + sleep_seconds).strftime('%H:%M:%S')
            logging.info(f"💤 Sleeping for {sleep_seconds/60:.0f} mins. Next post approx: {wake_up_time}")
            time.sleep(sleep_seconds)

        # --- AI ERROR HANDLING (SELF-HEAL) ---
        except tweepy.errors.TooManyRequests:
            # Rate Limit Error (429): Pause for a long time
            logging.error("⛔ RATE LIMIT HIT. Waiting 30 mins to heal (1800s)...")
            time.sleep(1800)
            
        except tweepy.errors.Unauthorized:
            # Token Error: Fatal, requires manual key fix
            logging.critical("⛔ INVALID KEYS. Please check your Access Token/Secret. STOPPING.")
            break
            
        except Exception as e:
            # General Crash: Log and attempt restart
            logging.error(f"⚠️ UNHANDLED CRASH: {e}")
            logging.info("🩹 Applying self-healing... Restarting loop in 5 minutes (300s).")
            time.sleep(300)

if __name__ == "__main__":
    run_bot()