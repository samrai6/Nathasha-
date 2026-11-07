from logging import (
    FileHandler,
    StreamHandler,
    INFO,
    basicConfig,
    error as log_error,
    info as log_info,
)
from os import path as ospath, environ, remove
from subprocess import run as srun, call as scall, CalledProcessError
from importlib.metadata import distributions
from requests import get as rget
from dotenv import load_dotenv, dotenv_values
from pymongo import MongoClient

if ospath.exists("log.txt"):
    with open("log.txt", "r+") as f:
        f.truncate(0)

if ospath.exists("rlog.txt"):
    remove("rlog.txt")

basicConfig(
    format="[%(asctime)s] [%(levelname)s] - %(message)s",
    datefmt="%d-%b-%y %I:%M:%S %p",
    handlers=[FileHandler("log.txt"), StreamHandler()],
    level=INFO,
)

load_dotenv("config.env", override=True)

try:
    if bool(environ.get("_____REMOVE_THIS_LINE_____")):
        log_error("The README.md file there to be read! Exiting now!")
        exit()
except Exception:
    pass

BOT_TOKEN = environ.get("BOT_TOKEN", "")
if len(BOT_TOKEN) == 0:
    log_error("BOT_TOKEN variable is missing! Exiting now")
    exit(1)

bot_id = BOT_TOKEN.split(":", 1)[0]

DATABASE_URL = environ.get("DATABASE_URL", "")
if len(DATABASE_URL) == 0:
    DATABASE_URL = None

if DATABASE_URL is not None:
    conn = MongoClient(DATABASE_URL, serverSelectionTimeoutMS=10000, connectTimeoutMS=10000)
    db = conn.wzmlx
    old_config = db.settings.deployConfig.find_one({"_id": bot_id})
    config_dict = db.settings.config.find_one({"_id": bot_id})
    if old_config is not None:
        del old_config["_id"]
    if (
        old_config is not None
        and old_config == dict(dotenv_values("config.env"))
        or old_config is None
    ) and config_dict is not None:
        environ["UPSTREAM_REPO"] = config_dict["UPSTREAM_REPO"]
        environ["UPSTREAM_BRANCH"] = config_dict["UPSTREAM_BRANCH"]
        environ["UPGRADE_PACKAGES"] = config_dict.get("UPDATE_PACKAGES", "False")
    conn.close()

UPGRADE_PACKAGES = environ.get("UPGRADE_PACKAGES", "False")
if UPGRADE_PACKAGES.lower() == "true":
    packages = [dist.metadata["Name"] for dist in distributions()]
    scall("uv pip install --system " + " ".join(packages), shell=True)

UPSTREAM_REPO = environ.get("UPSTREAM_REPO", "")
if len(UPSTREAM_REPO) == 0:
    UPSTREAM_REPO = None

UPSTREAM_BRANCH = environ.get("UPSTREAM_BRANCH", "")
if len(UPSTREAM_BRANCH) == 0:
    UPSTREAM_BRANCH = "master"

if UPSTREAM_REPO is not None:
    if ospath.exists(".git"):
        srun(["rm", "-rf", ".git"])

    try:
        # Use argument lists instead of a shell command so repository/branch
        # values cannot inject arbitrary shell commands.
        srun(["git", "init", "-q"], check=True)
        srun(["git", "config", "user.email", "bot@localhost"], check=True)
        srun(["git", "config", "user.name", "WZML-X updater"], check=True)
        srun(["git", "add", "."], check=True)
        srun(["git", "commit", "-sm", "update", "-q"], check=True)
        srun(["git", "remote", "add", "origin", UPSTREAM_REPO], check=True)
        srun(["git", "fetch", "origin", UPSTREAM_BRANCH, "-q"], check=True)
        srun(["git", "reset", "--hard", f"origin/{UPSTREAM_BRANCH}", "-q"], check=True)
        log_info("Successfully updated with latest commits !!")
    except CalledProcessError as error:
        log_error(f"Upstream update failed (exit code {error.returncode}).")
    log_info(f"UPSTREAM_REPO: {UPSTREAM_REPO} | UPSTREAM_BRANCH: {UPSTREAM_BRANCH}")
