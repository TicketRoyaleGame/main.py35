import asyncio
from datetime import datetime
import io
import json
import os
from threading import Thread
from flask import Flask
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageOps

# --- שרת HTTP קטן ברקע (כדי ש-Render יהיה מרוצה ויפתח פורט 8080) ---
app = Flask("")


@app.route("/")
def home():
  return "Bot is running 24/7!"


def run_flask():
  app.run(host="0.0.0.0", port=8080)


def keep_alive():
  t = Thread(target=run_flask)
  t.start()


# הפעלת השרת ברקע
keep_alive()

# הגדרות ראשיות - מזהה הבעלים שלך
OWNER_ID = 961945951780630541
TOKEN = os.getenv("TOKEN", "YOUR_BOT_TOKEN_HERE")

DATA_FILE = "database.json"


# --- ניהול מסד הנתונים המקומי ---
class Database:

  def __init__(self, filename=DATA_FILE):
    self.filename = filename
    self.load()

  def load(self):
    if not os.path.exists(self.filename):
      self.data = {
          "users": {},
          "logs": [],
          "blocked": [],
          "maintenance": False,
          "announcement": "",
      }
      self.save()
    else:
      with open(self.filename, "r", encoding="utf-8") as f:
        self.data = json.load(f)

  def save(self):
    with open(self.filename, "w", encoding="utf-8") as f:
      json.dump(self.data, f, ensure_ascii=False, indent=4)

  def log_action(self, user_id, username, action):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    self.data["logs"].insert(
        0, {"time": timestamp, "user_id": user_id, "name": username, "action": action}
    )
    if len(self.data["logs"]) > 100:
      self.data["logs"].pop()

    str_id = str(user_id)
    if str_id not in self.data["users"]:
      self.data["users"][str_id] = {"name": username, "uses": 0}
    self.data["users"][str_id]["uses"] += 1
    self.save()


db = Database()


# --- מחלקה מותאמת אישית לבדיקת הרשאות ותחזוקה לכל פקודה ---
class MyCheckCommandTree(app_commands.CommandTree):

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    user_id = interaction.user.id

    # בדיקת חסימה
    if user_id in db.data["blocked"]:
      await interaction.response.send_message(
          "❌ נחסמת מהיכולת להשתמש באפליקציה זו.", ephemeral=True
      )
      return False

    # בדיקת מצב תחזוקה
    if db.data["maintenance"] and user_id != OWNER_ID:
      await interaction.response.send_message(
          "🛠️ האפליקציה נמצאת כעת במצב תחזוקה. נסה שוב מאוחר יותר.", ephemeral=True
      )
      return False

    return True


# --- הגדרת הבוט ---
class MyDiscordApp(commands.Bot):

  def __init__(self):
    intents = discord.Intents.default()
    super().__init__(
        command_prefix="!", intents=intents, tree_cls=MyCheckCommandTree
    )

  async def setup_hook(self):
    await self.tree.sync()
    print(f"הבוט התחבר בהצלחה בתור {self.user}")


bot = MyDiscordApp()


# --- פאנל ניהול אינטראקטיבי ---
class AdminPanelView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(
      label="רענן נתונים", style=discord.ButtonStyle.primary, emoji="🔄"
  )
  async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
    db.load()
    embed = create_admin_embed()
    await interaction.response.edit_message(embed=embed, view=self)

  @discord.ui.button(
      label="הורד דוח (TXT)", style=discord.ButtonStyle.secondary, emoji="📥"
  )
  async def download_report(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    report_content = json.dumps(db.data, ensure_ascii=False, indent=4)
    file = discord.File(
        fp=io.BytesIO(report_content.encode("utf-8")), filename="bot_report.txt"
    )
    await interaction.response.send_message(
        "הנה דוח הנתונים המלא של האפליקציה:", file=file, ephemeral=True
    )

  @discord.ui.button(
      label="נקה לוגים", style=discord.ButtonStyle.danger, emoji="🧹"
  )
  async def clear_logs(self, interaction: discord.Interaction, button: discord.ui.Button):
    db.data["logs"] = []
    db.save()
    embed = create_admin_embed()
    await interaction.response.send_message(
        "יומן הפעילות נוקה בהצלחה!", ephemeral=True
    )
    await interaction.message.edit(embed=embed)

  @discord.ui.button(
      label="החלף מצב תחזוקה", style=discord.ButtonStyle.secondary, emoji="🛠️"
  )
  async def toggle_maintenance(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    db.data["maintenance"] = not db.data["maintenance"]
    db.save()
    status = "מופעל (נעול לציבור)" if db.data["maintenance"] else "כבוי (פתוח לכולם)"
    embed = create_admin_embed()
    await interaction.response.send_message(
        f"מצב תחזוקה שונה ל: {status}", ephemeral=True
    )
    await interaction.message.edit(embed=embed)


def create_admin_embed():
  total_users = len(db.data["users"])
  total_uses = sum(u["uses"] for u in db.data["users"].values())
  maint_status = "🟢 פעיל" if not db.data["maintenance"] else "🔴 במצב תחזוקה"

  embed = discord.Embed(
      title="🛡️ פאנל ניהול ובקרה סודי",
      color=discord.Color.dark_embed(),
      timestamp=datetime.now(),
  )
  embed.add_field(name="סטטוס מערכת", value=maint_status, inline=True)
  embed.add_field(name="סה״כ משתמשים", value=str(total_users), inline=True)
  embed.add_field(name="סה״כ הפעלות פקודה", value=str(total_uses), inline=True)

  logs_text = ""
  for log in db.data["logs"][:5]:
    logs_text +=
