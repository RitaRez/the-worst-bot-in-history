import discord
from discord.ext import commands
import torch
from TTS.api import TTS  # Ensure TTS is installed: pip install TTS
import google.generativeai as genai
import asyncio
import os
from secretive import GOOGLE_API_KEY, BOT_TOKEN, prompt_default, prompt_default_pt, prompt_gemini 
import emoji
import re

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

    if not discord.opus.is_loaded():
        try:
            # Load the Opus library manually
            discord.opus.load_opus('/opt/homebrew/lib/libopus.dylib')  # Adjust path if necessary
            print("Opus successfully loaded!")
        except Exception as e:
            print(f"Failed to load Opus: {e}")
    else:
        print("Opus is already loaded!")

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



async def generate_response(text, language="en", be_rita=True):
    if be_rita:
        if language == "en":
            text = f"{prompt_default} {text}"
        else :
            text = f"{prompt_default_pt} {text}"
    else:
        text = f"{prompt_gemini} {text}"

    # Generate response using Generative model and wait for the response response = gen_model.generate_content(text)
    response = gen_model.generate_content(text)

    # keep only alphabet characters and space
    answer = emoji.replace_emoji(response.text, replace='').strip()

    if language != "en":


        # remove last character if its a punctuation or space
        if answer[-1] in ['.']:
            answer = answer[:-1]

        # remove oi or Oi from the beginning with regex
        answer = re.sub(r'^[Oo]i!*,* *', '', answer)

    return answer


async def play_audio(ctx, wav_path: str):

    voice_channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        await voice_channel.connect()

    # Check if bot is already in a channel or moving to another channel
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()


    audio_source = discord.FFmpegPCMAudio(wav_path)
    ctx.voice_client.play(audio_source, after=lambda e: print(f'Finished playing: {e}'))


# Function to join voice channel and play audio
async def join_and_play(ctx, message, language="en", be_rita=True):
    

    answer = await generate_response(message.content, language, be_rita)

    print(ctx.author.voice)
    if ctx.author.voice is None:
        if language == "en":
            await ctx.send(f"You need to be in a voice channel for me to talk to you! But, {answer}")
        else:
            await ctx.send(f"Você precisa estar em um canal de voz para eu falar com você! Mas, {answer}")
        return
    

    # Audio file path (or generate audio using the tts model)
    # Example to generate TTS audio dynamically
    wav_path = "output.wav"
    tts.tts_to_file(text=answer, speaker_wav="target.wav", language=language, file_path=wav_path)


    await play_audio(ctx, wav_path)


async def help(ctx, language="en"):

    if language == "pt":
        text = "Oi, se você quiser me fazer uma pergunta em português, você pode me chamar com 'Oi Rita'. Se você quiser me fazer uma pergunta em inglês, você pode me chamar com 'Hey Rita'. "
        text += "Se você quiser me chamar de Gemini, você pode me chamar com 'Hey Gemini'. "
        text += "Se você quiser que eu repita a última coisa que eu disse, você pode me chamar com 'Rita, repeat' ou 'Rita, repete'. "
    else :
        text = "Hi, if you want to ask me a question in English, you can call me with 'Hey Rita'. If you want to ask me a question in Portuguese, you can call me with 'Oi Rita'. "
        text += "If you want to call Gemini, you can call with 'Hey Gemini'. "
        text += "If you want me to repeat the last thing I said, you can call me with 'Rita, repeat' or 'Rita, repete'. "

    # print in channel
    await ctx.send(text)
    
# Command to listen for "hey rita" in chat
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    ctx = await bot.get_context(message)

    if "hey rita" in message.content.lower():
        if "repeat" in message.content.lower() or "repete" in message.content.lower():
            await play_audio(ctx, "output.wav")
        elif "help" in message.content.lower() or "commands" in message.content.lower() or "-h" in message.content.lower():
            await help(ctx, language = "en")
        else:   
            await join_and_play(ctx, message, language = "en", be_rita = True)
    elif "oi rita" in message.content.lower():
        if "repeat" in message.content.lower() or "repete" in message.content.lower():
            await play_audio(ctx, "output.wav")
        elif "ajuda" in message.content.lower() or "comandos" in message.content.lower():
            await help(ctx, language = "pt")
        else:
            await join_and_play(ctx, message, language = "pt", be_rita = True)
    elif "hey gemini" in message.content.lower():
        await join_and_play(ctx, message, language = "en", be_rita = False)
        

    await bot.process_commands(message)


# Command to disconnect bot from voice channel
@bot.command()
async def leave(ctx):
    if ctx.voice_client is not None:
        await ctx.voice_client.disconnect()


# Run bot with your token
bot.run(BOT_TOKEN)
