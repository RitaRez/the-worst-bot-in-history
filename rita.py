from discord.ext import commands
from TTS.api import TTS  # Ensure TTS is installed: pip install TTS
from secretive import GOOGLE_API_KEY, BOT_TOKEN, prompt_default, prompt_default_pt, prompt_gemini 
import google.generativeai as genai
import emoji, re, schedule, os, asyncio, torch, discord

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

async def greet_office_hour():
    print("Greeting office hour")

    wav_path = "output.wav"
    tts.tts_to_file(text="Howdy everyone! Sorry I'm late.", speaker_wav="target.wav", language="en", file_path=wav_path)

    guild = bot.guilds[0]
    general_channel = discord.utils.get(guild.voice_channels, name="general")
    if general_channel is not None:
        await general_channel.connect()
        print(f"Joined {general_channel.name}")
    else:
        print("Voice channel not found")

    await play_audio(general_channel, wav_path)


async def leave_voice_channel():
    if bot.voice_clients:
        for vc in bot.voice_clients:
            await vc.disconnect()
            print(f"Disconnected from {vc.channel.name}")
    else:
        print("Not connected to any voice channel")

# Run the schedule within an async loop
async def schedule_tasks():
    schedule.every().monday.at("14:02").do(lambda: asyncio.create_task(greet_office_hour()))
    schedule.every().monday.at("14:30").do(lambda: asyncio.create_task(leave_voice_channel()))
    schedule.every().monday.at("14:32").do(lambda: asyncio.create_task(greet_office_hour()))
    schedule.every().monday.at("15:00").do(lambda: asyncio.create_task(leave_voice_channel()))
    schedule.every().wednesday.at("14:02").do(lambda: asyncio.create_task(greet_office_hour()))
    schedule.every().wednesday.at("14:30").do(lambda: asyncio.create_task(leave_voice_channel()))
    schedule.every().wednesday.at("14:32").do(lambda: asyncio.create_task(greet_office_hour()))
    schedule.every().wednesday.at("15:00").do(lambda: asyncio.create_task(leave_voice_channel()))
    schedule.every().tuesday.at("14:32").do(lambda: asyncio.create_task(greet_office_hour()))
    schedule.every().tuesday.at("15:00").do(lambda: asyncio.create_task(leave_voice_channel()))
    schedule.every().tuesday.at("15:02").do(lambda: asyncio.create_task(greet_office_hour()))
    schedule.every().tuesday.at("15:30").do(lambda: asyncio.create_task(leave_voice_channel()))
    schedule.every().thursday.at("14:32").do(lambda: asyncio.create_task(greet_office_hour()))
    schedule.every().thursday.at("15:00").do(lambda: asyncio.create_task(leave_voice_channel()))
    schedule.every().thursday.at("15:02").do(lambda: asyncio.create_task(greet_office_hour()))
    schedule.every().thursday.at("15:30").do(lambda: asyncio.create_task(leave_voice_channel()))

    while True:
        schedule.run_pending()
        await asyncio.sleep(1)


# Function to play audio in a voice channel
async def play_audio(voice_channel, wav_path: str):
    # Connect to the voice channel if the bot isn't already connected
    if voice_channel.guild.voice_client is None:
        await voice_channel.connect()
    elif voice_channel.guild.voice_client.channel != voice_channel:
        await voice_channel.guild.voice_client.move_to(voice_channel)

    # Play the audio file
    audio_source = discord.FFmpegPCMAudio(wav_path)
    voice_channel.guild.voice_client.play(audio_source, after=lambda e: print('done', e))

# Add setup_hook to start scheduling
@bot.event
async def setup_hook():
    bot.loop.create_task(schedule_tasks())

# Define a conversation history globally or as part of the user's session
conversation_history = []

async def generate_response(author_name, text, language="en", be_rita=True):
    global conversation_history

    if be_rita:
        if language == "en":
            text = f"{prompt_default} {text}"
        else:
            text = f"{prompt_default_pt} {text}"
    else:
        text = f"{prompt_gemini} {text}"

    # Add the user message to the conversation history
    conversation_history.append(f"User: {text}")

    # Prepare the entire conversation as input to the model
    conversation_text = "\n".join(conversation_history)

    # Generate response using Generative model and pass the conversation history
    response = gen_model.generate_content(conversation_text)

    # Process the response and clean it
    answer = emoji.replace_emoji(response.text, replace='').strip()

    # Optionally remove unnecessary punctuation or phrases in non-English languages
    # if language != "en":
    #     if answer[-1] in ['.']:
    #         answer = answer[:-1]
    #     answer = re.sub(r'^[Oo]i!*,* *', '', answer)

    if language == "en":
        answer = f"Hey {author_name}, {answer}!"
    else:
        answer = f"Oi {author_name}, {answer}!"


    # Add the bot's response to the conversation history
    conversation_history.append(f"Bot: {answer}")

    # Return the bot's answer for output
    return answer


# Function to join voice channel and play audio
async def join_and_play(ctx, message, language="en", be_rita=True):
    answer = await generate_response(ctx.author.display_name, message.content, language, be_rita)

    # Check if the user is in a voice channel
    if ctx.author.voice is None:
        if language == "en":
            await ctx.send(f"You need to be in a voice channel for me to talk to you! But, {answer}")
        else:
            await ctx.send(f"Você precisa estar em um canal de voz para eu falar com você! Mas, {answer}")
        return

    # Audio file path (or generate audio using the tts model)
    wav_path = "output.wav"
    tts.tts_to_file(text=answer, speaker_wav="target.wav", language=language, file_path=wav_path)

    # Pass the user's voice channel to play_audio
    voice_channel = ctx.author.voice.channel
    await play_audio(voice_channel, wav_path)


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
