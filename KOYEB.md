# Deploy Nathasha on Koyeb

This repository runs a Telegram mirror/leech bot as a long-running worker.

## Create the service

1. In Koyeb, create an App and choose **GitHub** as the deployment source.
2. Select `samrai6/Nathasha-` and branch **`master`**.
3. Choose the **Dockerfile** builder and deploy it as a **Worker** (not a web service).
4. Do not add an HTTP port for the bot worker. The bot does not need an inbound web port unless you intentionally configure `BASE_URL`.
5. Set the required environment variables below, then deploy.

## Required environment variables

| Name | Value |
| --- | --- |
| `BOT_TOKEN` | Telegram bot token from BotFather |
| `OWNER_ID` | Numeric Telegram user ID of the bot owner |
| `TELEGRAM_API` | Telegram API ID |
| `TELEGRAM_HASH` | Telegram API hash |

## Optional environment variables

- `DATABASE_URL`: MongoDB connection URI. Recommended if you want the bot's settings/configuration stored in MongoDB; it is optional for startup.
- `MAX_CONCURRENT_TRANSMISSIONS`: optional Telegram upload/download transmission concurrency; defaults to `4` to reduce memory spikes. Increase only on larger instances.
- `AUTHORIZED_CHATS`, `SUDO_USERS`, `FSUB_IDS`, `LEECH_LOG_ID`, `MIRROR_LOG_ID`, `LINKS_LOG_ID`: set only when you need those features.
- `BASE_URL`: leave empty for a worker-only deployment. If you enable web features, configure the corresponding Koyeb web service/port deliberately.

## Important notes

- Keep `UPSTREAM_REPO` empty. The Koyeb Docker image sets `KOYEB_DEPLOYMENT=true`, which disables upstream source replacement so stale MongoDB settings cannot overwrite this repository at startup.
- Do not add `_____REMOVE_THIS_LINE_____` as an environment variable. It is a safety guard that deliberately exits the app.
- Store credentials as Koyeb Secrets/environment variables. Do not commit tokens, API hashes, or MongoDB passwords to GitHub.
- Koyeb container filesystems may be ephemeral. Do not assume downloaded files survive a redeploy/restart; use supported persistent storage or an external upload destination for files that must persist.
- MongoDB persistence covers bot configuration/state handled by this code; it does not automatically persist the downloads directory.
- This repository starts the Telegram bot, Aria2, and qBittorrent inside the container. Defaults are tuned for a smaller worker: 16 Pyrogram workers, 4 concurrent Telegram transmissions, 3 active Aria2 downloads, and 3 active qBittorrent downloads.
- For real mirror/leech workloads, use an instance with at least 2 GB RAM and sufficient disk; larger files, parallel uploads, media processing, and torrents can need substantially more. A tiny/free instance may restart or run out of memory.
- qBittorrent and Aria2 download data is local to the container unless you configure persistent storage or external upload.

## Startup behavior

`start.sh` checks the four required variables, runs `update.py`, then starts `python3 -m bot` as the main process so termination signals reach the bot.
