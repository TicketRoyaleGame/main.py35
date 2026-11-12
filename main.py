import asyncio
from datetime import datetime
import io
import json
import os
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageOps

# הגדרות ראשיות - החלף את הערכים בנתונים שלך
OWNER_ID = 123456789012345678  # מספר הזיהוי האישי שלך בדיסקורד (Discord ID)
TOKEN = "YOUR_BOT_TOKEN_HERE"  # הטוקן של הבוט מפורטל המפתחים

DATA_FILE = "database.json"


# --- ניהול מסד הנתונים המקומי ---
class Database:

  def __init__(self, filename=DATA_FILE):
    self.filename = filename
    self.load()

  def load(self):
    if not os.path.exists(self.filename):
      self.data = {
          "users": {},  # {user_id: {"name": str, "uses": int}}
          "logs": [],  # רשימת פעולות
          "blocked": [],  # רשימת משתמשים חסומים
          "maintenance": False,  # מצב תחזוקה
          "announcement": "",  # הודעת מערכת שתוצמת תחת תשובות
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
    # שמירת 100 לוגים אחרונים בלבד למניעת התנפחות הקובץ
    if len(self.data["logs"]) > 100:
      self.data["logs"].pop()

    # עדכון מונה שימושים למשתמש
    str_id = str(user_id)
    if str_id not in self.data["users"]:
      self.data["users"][str_id] = {"name": username, "uses": 0}
    self.data["users"][str_id]["uses"] += 1
    self.save()


db = Database()


# --- הגדרת הבוט ---
class MyDiscordApp(commands.Bot):

  def __init__(self):
    intents = discord.Intents.default()
    super().__init__(command_prefix="!", intents=intents)

  async def setup_hook(self):
    await self.tree.sync()
    print(f"הבוט התחבר בהצלחה בתור {self.user}")


bot = MyDiscordApp()


# --- בדיקות אבטחה ותחזוקה (Middleware) ---
@bot.tree.before_invoke
async def check_permissions(interaction: discord.Interaction):
  user_id = interaction.user.id

  # בדיקת חסימה
  if user_id in db.data["blocked"]:
    await interaction.response.send_message(
        "❌ נחסמת מהיכולת להשתמש באפליקציה זו.", ephemeral=True
    )
    raise app_commands.CheckFailure("Blocked user")

  # בדיקת מצב תחזוקה (רק הבעלים יכול להשתמש)
  if db.data["maintenance"] and user_id != OWNER_ID:
    await interaction.response.send_message(
        "🛠️ האפליקציה נמצאת כעת במצב תחזוקה ונפתחת מחדש בקרוב. נסה שוב מאוחר יותר.",
        ephemeral=True,
    )
    raise app_commands.CheckFailure("Maintenance mode")


# --- מחלקות אינטראקטיביות (Views & Modals) ---


# פאנל ניהול אינטראקטיבי עם כפתורים
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

  # הצגת 5 לוגים אחרונים
  logs_text = ""
  for log in db.data["logs"][:5]:
    logs_text += f"`{log['time']}` | **{log['name']}**: {log['action']}\n"
  if not logs_text:
    logs_text = "אין פעילויות רשומות כרגע."

  embed.add_field(
      name="📋 יומן פעילות אחרון (5 שורות)", value=logs_text, inline=False
  )
  return embed


# סקר אינטראקטיבי עם כפתורים
class PollView(discord.ui.View):

  def __init__(self, options):
    super().__init__(timeout=180)
    self.votes = {opt: set() for opt in options}

    for opt in options:
      button = discord.ui.Button(
          label=opt, style=discord.ButtonStyle.secondary
      )
      button.callback = self.create_callback(opt)
      self.add_item(button)

  def create_callback(self, option):
    async def button_callback(interaction: discord.Interaction):
      user_id = interaction.user.id
      # הסרת הצבעה קודמת של המשתמש אם קיימת
      for opt in self.votes:
        if user_id in self.votes[opt]:
          self.votes[opt].remove(user_id)

      # הוספת ההצבעה החדשה
      self.votes[option].add(user_id)

      # עדכון הטקסט בסקר
      desc = "📊 **סקר חדש!** בחר באפשרות המועדפת עליך:\n\n"
      for opt, voters in self.votes.items():
        desc += f"🔹 **{opt}**: {len(voters)} קולות\n"

      embed = interaction.message.embeds[0]
      embed.description = desc
      await interaction.response.edit_message(embed=embed, view=self)

    return button_callback


# --- פקודות האפליקציה (Slash Commands) ---


@bot.tree.command(name="poll", description="צור סקר אינטראקטיבי עם כפתורים לחיצים")
@app_commands.describe(
    question="שאלת הסקר", options="אפשרויות מופרדות בפסיקים (למשל: תפוח,בננה,אפרסק)"
)
async def poll(interaction: discord.Interaction, question: str, options: str):
  db.log_action(interaction.user.id, interaction.user.name, "יצר סקר")
  opts = [o.strip() for o in options.split(",")]
  if len(opts) < 2 or len(opts) > 5:
    await interaction.response.send_message(
        "❌ יש להזין בין 2 ל-5 אפשרויות מופרדות בפסיקים.", ephemeral=True
    )
    return

  desc = f"📊 **סקר חדש: {question}**\n\n"
  for opt in opts:
    desc += f"🔹 **{opt}**: 0 קולות\n"

  embed = discord.Embed(title=question, description=desc, color=discord.Color.blue())
  view = PollView(opts)
  footer_text = (
      f"\n\n*נוצר על ידי {interaction.user.name}* | {db.data['announcement']}"
      if db.data["announcement"]
      else f"\n\n*נוצר על ידי {interaction.user.name}*"
  )
  embed.set_footer(text=footer_text)

  await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="remind", description="קבע תזכורת אישית לעוד מספר דקות")
@app_commands.describe(minutes="מספר הדקות להמתנה", message="תוכן התזכורת")
async def remind(interaction: discord.Interaction, minutes: int, message: str):
  db.log_action(
      interaction.user.id, interaction.user.name, f"הגדיר תזכורת ל-{minutes} דקות"
  )
  await interaction.response.send_message(
      f"✅ תזכורת הוגדרה! אשלח לך הודעה פרטית עוד {minutes} דקות.", ephemeral=True
  )

  await asyncio.sleep(minutes * 60)
  try:
    await interaction.user.send(f"⏰ **תזכורת:** {message}")
  except Exception:
    pass


@bot.tree.command(name="invert", description="הפוך צבעים (נגטיב) לתמונה שהעלית")
@app_commands.describe(image="העלה כאן תמונה לעיבוד")
async def invert(interaction: discord.Interaction, image: discord.Attachment):
  db.log_action(
      interaction.user.id, interaction.user.name, "הפעיל אפקט נגטיב על תמונה"
  )
  if not image.content_type or not image.content_type.startswith("image/"):
    await interaction.response.send_message(
        "❌ הקובץ שהועלה אינו תמונה תקינה.", ephemeral=True
    )
    return

  await interaction.response.defer(thinking=True)

  try:
    img_bytes = await image.read()
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    inverted_img = ImageOps.invert(img)

    output = io.BytesIO()
    inverted_img.save(output, format="PNG")
    output.seek(0)

    file = discord.File(fp=output, filename="inverted.png")
    footer = db.data["announcement"]
    content = f"הנה התמונה ההפוכה שלך! {footer}" if footer else "הנה התמונה ההפוכה שלך!"
    await interaction.followup.send(content=content, file=file)
  except Exception as e:
    await interaction.followup.send(
        f"❌ אירעה שגיאה בעיבוד התמונה: {e}", ephemeral=True
    )


@bot.tree.command(name="to_gif", description="המר תמונה רגילה לקובץ GIF")
@app_commands.describe(image="העלה תמונה להמרה")
async def to_gif(interaction: discord.Interaction, image: discord.Attachment):
  db.log_action(interaction.user.id, interaction.user.name, "המר תמונה ל-GIF")
  if not image.content_type or not image.content_type.startswith("image/"):
    await interaction.response.send_message(
        "❌ הקובץ שהועלה אינו תמונה תקינה.", ephemeral=True
    )
    return

  await interaction.response.defer(thinking=True)

  try:
    img_bytes = await image.read()
    img = Image.open(io.BytesIO(img_bytes))

    output = io.BytesIO()
    img.save(output, format="GIF")
    output.seek(0)

    file = discord.File(fp=output, filename="converted.gif")
    footer = db.data["announcement"]
    content = f"הנה קובץ ה-GIF שלך! {footer}" if footer else "הנה קובץ ה-GIF שלך!"
    await interaction.followup.send(content=content, file=file)
  except Exception as e:
    await interaction.followup.send(
        f"❌ אירעה שגיאה בהמרת התמונה: {e}", ephemeral=True
    )


# --- פאנל הניהול הסודי (נגיש אך ורק לבעלים ב-ID) ---
@bot.tree.command(name="admin_panel", description="[סודי - לבעלים בלבד] פתח את פאנל הבקרה")
async def admin_panel(interaction: discord.Interaction):
  if interaction.user.id != OWNER_ID:
    # אבטחה: שליחת התראה לבעלים על ניסיון פריצה
    try:
      owner_user = await bot.fetch_user(OWNER_ID)
      await owner_user.send(
          f"🚨 **התרעת אבטחה!** המשתמש `{interaction.user.name}` (ID: `{interaction.user.id}`) ניסה לגשת לפאנל הניהול הסודי שלך."
      )
    except Exception:
      pass

    await interaction.response.send_message(
        "❌ פקודה זו אינה קיימת או שאין לך הרשאה לגשת אליה.", ephemeral=True
    )
    return

  db.log_action(interaction.user.id, interaction.user.name, "פתח את פאנל הניהול")
  embed = create_admin_embed()
  view = AdminPanelView()
  await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# --- פקודת ניהול להגדרת הודעת מערכת (Announcement) ---
@bot.tree.command(name="set_announcement", description="[סודי] הגדר הודעת מערכת שתופיע מתחת לתשובות")
@app_commands.describe(text="הטקסט שיופיע (השאר ריק כדי לאפס)")
async def set_announcement(interaction: discord.Interaction, text: str = ""):
  if interaction.user.id != OWNER_ID:
    await interaction.response.send_message("❌ אין לך הרשאה.", ephemeral=True)
    return

  db.data["announcement"] = text
  db.save()
  await interaction.response.send_message(
      f"✅ הודעת המערכת עודכנה בהצלחה ל: `{text}`", ephemeral=True
  )


# --- פקודת חסימת משתמש ---
@bot.tree.command(name="block_user", description="[סודי] חסום משתמש סורق משימוש בבוט")
@app_commands.describe(user_id="מספר הזיהוי (ID) של המשתמש לחסימה")
async def block_user(interaction: discord.Interaction, user_id: str):
  if interaction.user.id != OWNER_ID:
    await interaction.response.send_message("❌ אין לך הרשאה.", ephemeral=True)
    return

  try:
    uid = int(user_id)
    if uid not in db.data["blocked"]:
      db.data["blocked"].append(uid)
      db.save()
      await interaction.response.send_message(
          f"✅ המשתמש עם ה-ID `{uid}` נחסם בהצלחה.", ephemeral=True
      )
    else:
      await interaction.response.send_message(
          "⚠️ המשתמש כבר נמצא ברשימת החסומים.", ephemeral=True
      )
  except ValueError:
    await interaction.response.send_message(
        "❌ יש להזין מספר ID תקין (ספרות בלבד).", ephemeral=True
    )


# הפעלת הבוט
bot.run(TOKEN)