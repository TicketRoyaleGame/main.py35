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
    # סינכרון פקודות גלובלי
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

# --- פקודת admin_panel ---
@bot.tree.command(name="admin_panel", description="פתיחת פאנל ניהול")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
async def admin_panel(interaction: discord.Interaction):
    # מונע את שגיאת "The application did not respond" על ידי מתן מענה מידי
    await interaction.response.send_message("פאנל הניהול פתוח בהצלחה!", ephemeral=True)

# --- פקודת to_gif המטפלת גם ב-Pillow ---
@bot.tree.command(name="to_gif", description="ממיר תמונה לגיף")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
async def to_gif(interaction: discord.Interaction):
    # שימוש ב-defer למקרה שעיבוד התמונה לוקח זמן
    await interaction.response.defer(thinking=True)
    
    # כאן תוכנת ה-Pillow יכולה לבצע את הפעולות על תמונות
    # לדוגמה: img = Image.new('RGB', (100, 100), color = 'red')
    
    await interaction.followup.send("המרת התמונה ל-GIF בוצעה בהצלחה!")

# הפעלת שרת ה-Flask ברקע
keep_alive()

# הכנס כאן את ה-Token האמיתי של הבוט שלך
TOKEN = "YOUR_BOT_TOKEN_HERE"
bot.run(TOKEN)
