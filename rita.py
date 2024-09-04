import discord
from discord.ext import commands
import torch
from TTS.api import TTS  # Ensure TTS is installed: pip install TTS
import google.generativeai as genai
import asyncio
import os
from secretive import GOOGLE_API_KEY, BOT_TOKEN, prompt_default, prompt_default_pt 
import emoji

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.voice_states = True

# Create bot instance
bot = commands.Bot(command_prefix="!", intents=intents)

# Define the global variables for the models
tts = None
gen_model = None


@bot.event
async def on_ready():
    global tts, gen_model

    print(f'Logged in as {bot.user.name}')
    print('Bot is ready!')

    # Load Generative model
    print("Loading Generative model...")
    gen_model = genai.GenerativeModel('models/gemini-1.5-flash')
    genai.configure(api_key=GOOGLE_API_KEY)
    
    # Check for CUDA availability
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Running on device: {device}")

    # List available 🐸TTS models
    print("Listing available 🐸TTS models...")
    print(TTS().list_models())

    # Initialize 🐸TTS model
    print("Initializing 🐸TTS model...")
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

    print("TTS model initialized successfully.")


# Function to join voice channel and play audio
async def join_and_play(ctx, message, language="en"):

    if language == "en":
        text = f"{prompt_default} {message.content.lower()}"
    else :
        text = f"{prompt_default_pt} {message.content.lower()}"

    # Generate response using Generative model and wait for the response response = gen_model.generate_content(text)
    response = gen_model.generate_content(text)

    # keep only alphabet characters and space
    answer = emoji.replace_emoji(response.text, replace='')
    
    print(answer)
    print(ctx.author.voice)
    if ctx.author.voice is None:
        await ctx.send(f"You need to be in a voice channel for me to talk to you! But, {answer}")
        return
    

    if not discord.opus.is_loaded():
        try:
            # Load the Opus library manually
            discord.opus.load_opus('/opt/homebrew/lib/libopus.dylib')  # Adjust path if necessary
            print("Opus successfully loaded!")
        except Exception as e:
            print(f"Failed to load Opus: {e}")
    else:
        print("Opus is already loaded!")
    

    voice_channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        await voice_channel.connect()

    # Check if bot is already in a channel or moving to another channel
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()

    # Audio file path (or generate audio using the tts model)
    # Example to generate TTS audio dynamically
    wav_path = "output.wav"
    tts.tts_to_file(text=answer, speaker_wav="target.wav", language=language, file_path=wav_path)


    audio_source = discord.FFmpegPCMAudio(wav_path)
    ctx.voice_client.play(audio_source, after=lambda e: print(f'Finished playing: {e}'))


# Command to listen for "hey rita" in chat
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if "hey rita" in message.content.lower():
        ctx = await bot.get_context(message)
        await join_and_play(ctx, message, language = "en")
    if "oi rita" in message.content.lower():
        ctx = await bot.get_context(message)
        await join_and_play(ctx, message, language = "pt")

    await bot.process_commands(message)


# Command to disconnect bot from voice channel
@bot.command()
async def leave(ctx):
    if ctx.voice_client is not None:
        await ctx.voice_client.disconnect()


# Run bot with your token
bot.run(BOT_TOKEN)
