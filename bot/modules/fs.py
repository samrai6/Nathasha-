#!/usr/bin/env python3
from pyrogram import filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex, create
from pyrogram.enums import ChatType, ChatMemberStatus
from bot import bot, config_dict, OWNER_ID, LOGGER, DATABASE_URL
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage
from bot.helper.ext_utils.db_handler import DbManger

config_dict.setdefault("FS_SOURCE_CHANNEL", None)
config_dict.setdefault("FS_DUMP_CHANNELS", [])
config_dict.setdefault("LEECH_ENABLED", True)
pending_input = {}
seen_media_groups = set()


async def save_fs_settings():
    if not DATABASE_URL:
        return
    await DbManger().update_config({
        "FS_SOURCE_CHANNEL": config_dict.get("FS_SOURCE_CHANNEL"),
        "FS_DUMP_CHANNELS": config_dict.get("FS_DUMP_CHANNELS", []),
        "LEECH_ENABLED": config_dict.get("LEECH_ENABLED", True),
    })


def fs_menu_text():
    source = config_dict.get("FS_SOURCE_CHANNEL")
    dumps = config_dict.get("FS_DUMP_CHANNELS", [])
    source_text = source["title"] if source else "Not set"
    return (
        "<b>📂 Forward Settings</b>\n\n"
        f"<b>Source Channel:</b> {source_text}\n"
        f"<b>Dump Channels:</b> {len(dumps)}\n"
        f"<b>Mirror / Clone / Leech:</b> {'ON ✅' if config_dict.get('LEECH_ENABLED', True) else 'OFF ❌'}"
    )


def fs_menu():
    buttons = ButtonMaker()
    buttons.ibutton("➕ Set Source Channel", "fs source")
    buttons.ibutton("➕ Add Dump Channel", "fs add")
    buttons.ibutton("📋 View Dump Channels", "fs view")
    buttons.ibutton("➖ Remove Dump Channel", "fs remove")
    state = "ON ✅" if config_dict.get("LEECH_ENABLED", True) else "OFF ❌"
    buttons.ibutton(f"Mirror / Clone / Leech: {state}", "fs leech_toggle")
    return buttons.build_menu(2)


async def fs_command(_, message):
    await sendMessage(message, fs_menu_text(), fs_menu())


async def ask_channel(query, action):
    pending_input[query.from_user.id] = action
    label = "Source Channel" if action == "source" else "Dump Channel"
    await editMessage(
        query.message,
        f"Send the {label} @username or channel ID.\n"
        "You can also forward a post from that channel here.",
    )


async def fs_callback(_, query):
    if query.from_user.id != OWNER_ID:
        return await query.answer("Only the owner can change these settings.", show_alert=True)
    data = query.data.split()
    action = data[1]
    if action in ("source", "add"):
        await ask_channel(query, action)
    elif action == "leech_toggle":
        config_dict["LEECH_ENABLED"] = not config_dict.get("LEECH_ENABLED", True)
        await save_fs_settings()
        await editMessage(query.message, fs_menu_text(), fs_menu())
    elif action == "view":
        dumps = config_dict.get("FS_DUMP_CHANNELS", [])
        if not dumps:
            return await query.answer("No dump channels added.", show_alert=True)
        buttons = ButtonMaker()
        for item in dumps:
            buttons.ibutton(item["title"], f"fs info {item['id']}")
        buttons.ibutton("⬅️ Back", "fs back")
        await editMessage(query.message, "<b>Dump Channels</b>", buttons.build_menu(1))
    elif action == "info":
        chat_id = int(data[2])
        item = next((x for x in config_dict.get("FS_DUMP_CHANNELS", []) if int(x["id"]) == chat_id), None)
        if item:
            buttons = ButtonMaker()
            buttons.ibutton("🗑 Remove", f"fs rm {chat_id}")
            buttons.ibutton("⬅️ Back", "fs view")
            await editMessage(query.message, f"<b>{item['title']}</b>", buttons.build_menu(1))
    elif action == "remove":
        dumps = config_dict.get("FS_DUMP_CHANNELS", [])
        if not dumps:
            return await query.answer("No dump channels added.", show_alert=True)
        buttons = ButtonMaker()
        for item in dumps:
            buttons.ibutton(f"❌ {item['title']}", f"fs rm {item['id']}")
        buttons.ibutton("⬅️ Back", "fs back")
        await editMessage(query.message, "<b>Select a dump channel to remove</b>", buttons.build_menu(1))
    elif action == "rm":
        chat_id = int(data[2])
        config_dict["FS_DUMP_CHANNELS"] = [
            x for x in config_dict.get("FS_DUMP_CHANNELS", [])
            if int(x["id"]) != chat_id
        ]
        await save_fs_settings()
        await editMessage(query.message, fs_menu_text(), fs_menu())
    elif action == "back":
        await editMessage(query.message, fs_menu_text(), fs_menu())
    await query.answer()


async def fs_input(_, message):
    action = pending_input.pop(message.from_user.id, None)
    if not action:
        return
    try:
        forwarded_chat = getattr(message, "forward_from_chat", None)
        if forwarded_chat:
            chat = forwarded_chat
        else:
            value = (message.text or "").strip()
            if not value:
                raise ValueError("Send a channel username or numeric ID.")
            chat = await bot.get_chat(int(value) if value.lstrip("-").isdigit() else value)
        if chat.type != ChatType.CHANNEL:
            raise ValueError("Please send a channel, not a group or user.")
        member = await bot.get_chat_member(chat.id, bot.me.id)
        if member.status not in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR):
            raise ValueError("Please make the bot an admin in this channel first.")
        item = {"id": int(chat.id), "title": chat.title or str(chat.id)}
        if action == "source":
            config_dict["FS_SOURCE_CHANNEL"] = item
            result = f"Source channel set: <b>{item['title']}</b>"
        else:
            dumps = config_dict.setdefault("FS_DUMP_CHANNELS", [])
            if any(int(x["id"]) == item["id"] for x in dumps):
                result = "This dump channel is already added."
            else:
                dumps.append(item)
                result = f"Dump channel added: <b>{item['title']}</b>"
        await save_fs_settings()
        await sendMessage(message, result + "\n\n" + fs_menu_text(), fs_menu())
    except Exception as e:
        await sendMessage(message, f"Could not set channel: {e}")
        

async def relay_source_post(client, message):
    source = config_dict.get("FS_SOURCE_CHANNEL")
    dumps = config_dict.get("FS_DUMP_CHANNELS", [])
    if not source or not dumps or message.chat.id != int(source["id"]):
        return
    try:
        if message.media_group_id:
            group_id = str(message.media_group_id)
            if group_id in seen_media_groups:
                return
            seen_media_groups.add(group_id)
            for dump in dumps:
                await client.copy_media_group(
                    chat_id=int(dump["id"]),
                    from_chat_id=message.chat.id,
                    message_id=message.id,
                )
            return
        for dump in dumps:
            await client.copy_message(
                chat_id=int(dump["id"]),
                from_chat_id=message.chat.id,
                message_id=message.id,
                reply_markup=message.reply_markup,
            )
    except Exception as e:
        LOGGER.error(f"Source-to-dump copy failed: {e}")


bot.add_handler(
    MessageHandler(fs_command, filters=command(BotCommands.FsCommand) & filters.private & filters.user(OWNER_ID))
)
bot.add_handler(
    CallbackQueryHandler(fs_callback, filters=regex(r"^fs ") & filters.user(OWNER_ID))
)
bot.add_handler(
    MessageHandler(fs_input, filters=filters.private & filters.user(OWNER_ID))
)
bot.add_handler(
    MessageHandler(
        relay_source_post,
        filters=create(lambda _, __, message: bool(
            config_dict.get("FS_SOURCE_CHANNEL")
            and message.chat.id == int(config_dict["FS_SOURCE_CHANNEL"]["id"])
        )),
    )
)
