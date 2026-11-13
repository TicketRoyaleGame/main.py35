import os
import threading
from flask import Flask
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageOps

# --- הגדרת שרת ה-Flask לשמירה על חיבור פעיל (Keep-Alive) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.start()

# --- הגדרת הבוט וההרשאות ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    # סינכרון גלובלי של פקודות ה-Slash
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

# --- דוגמה לפקודת Slash המותאמת ל-User Install (DMs ושרתים) ---
@bot.tree.command(name="hello", description="אומר שלום ומציג את שם המשתמש")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"הי {interaction.user.name}, הבוט פועל בהצלחה!")

# הפעלת שרת ה-Flask ברקע
keep_alive()

# הכנס כאן את ה-Token של הבוט שלך במקום המחרוזת
TOKEN = "YOUR_BOT_TOKEN_HERE"
bot.run(TOKEN)
