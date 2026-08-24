import os
import re
import json
import math
import calendar
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput
import asyncio
import inspect
from datetime import datetime, timedelta
import random
from groq import AsyncGroq



def save_db():
    try:
        data = {
            "profiles": db["profiles"],
            "leaderboard_channel_id": db["leaderboard_channel_id"],
            "leaderboard_msg_ids": db["leaderboard_msg_ids"],
            "welcome_channel_id": db.get("welcome_channel_id"),
            "supporter_channel_id": db.get("supporter_channel_id"),
            "supporter_msg_id": db.get("supporter_msg_id"),
            "result_channel_id": db.get("result_channel_id"),
            "betting_channel_id": db.get("betting_channel_id"),
            "supporters": db.get("supporters", {}),
            "gems":     db.get("gems",     {}),
            "sg_links": db.get("sg_links", {}),
            "teams": [
                {"names": t["names"], "ids": t["ids"], "leader_id": t["leader_id"]}
                for t in db["teams"]
            ],
            "tour": None,
            "event": None,
        }
        if db["tour"]:
            data["tour"] = {k: v for k, v in db["tour"].items() if k != "host"}
        if db["event"]:
            ev = dict(db["event"])
            ev["winners"] = [str(getattr(w, "id", w)) for w in ev.get("winners", [])]
            data["event"] = ev
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[save_db] {e}")

def load_db():
    if not os.path.exists(DB_FILE):
        return
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        db["profiles"] = data.get("profiles", {})
        db["leaderboard_channel_id"] = data.get("leaderboard_channel_id")
        db["leaderboard_msg_ids"] = data.get("leaderboard_msg_ids", [])
        db["welcome_channel_id"]    = data.get("welcome_channel_id")
        db["supporter_channel_id"] = data.get("supporter_channel_id")
        db["supporter_msg_id"]     = data.get("supporter_msg_id")
        db["result_channel_id"]    = data.get("result_channel_id")
        db["betting_channel_id"]   = data.get("betting_channel_id")
        db["supporters"]           = data.get("supporters", {})
        db["gems"]                 = data.get("gems",     {})
        db["sg_links"]             = data.get("sg_links", {})
        db["big_event"]            = data.get("big_event")
        db["teams"] = [
            {"members": [], "names": t["names"], "ids": t["ids"], "leader_id": t["leader_id"]}
            for t in data.get("teams", [])
        ]
        if data.get("tour"):
            tour = data["tour"]
            tour["host"] = None
            if "matches" in tour:
                tour["matches"] = {int(k): v for k, v in tour["matches"].items()}
            db["tour"] = tour
        if data.get("event"):
            ev = data["event"]
            ev["winners"] = []
            db["event"] = ev
        print(f"[load_db] Dati caricati — {len(db['profiles'])} profili")
    except Exception as e:
        print(f"[load_db] {e}")

# ==========================================
# ⚙️ CONFIG E EMOJI
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Keep this explicit next to Bot initialization: prefix commands and on_message
# both depend on the Message Content intent being enabled.
intents.message_content = True
bot = commands.Bot(command_prefix=":", intents=intents, help_command=None)

E_CRYSTAL = "<:crystal:1507440029323100301>"
E_RUBY    = "<:ruby:1507420532402819093>"
E_XP      = "<:xp:1507719994958549113>"
E_CROWN   = "<:stumble_guys_crown:1505322344338427986>"
E_TROPHY  = "<:trophy:1505324701596123227>"
E_NO_RANK = "<:ranked:1507509359985295491>"
E_GOLD    = "<:gold_medal:1505979207107481740>"
E_BRONZE  = "<:bronze_medal:1505979006963421275>"
E_RANKING = "<:ranking:1505323647827710223>"
E_RULES   = "<:Rules:1506777190166167613>"
E_LEVEL   = "<:StumbleGuys:1505322057313816617>"
E_GEMS    = "<:gems:1507509442286190652>"
E_W       = "<:emoji_45:1507810623063461948>"

TICKET_SUPPORT_CAT  = 1410695991660908604
TICKET_STAFF_CAT    = 1410695994114310247
TICKET_GEMS_CAT     = 1410695992998756352
SUPPORTER_ROLE_ID   = 1410695946588913684

# In-memory: {user_id_str: {"channel_id": int, "type": str, "claimed_by": int|None}}
active_tickets: dict = {}
# XP cooldown: {user_id: last_xp_timestamp}
xp_cooldown: dict = {}
XP_PER_MSG        = 20
XP_COOLDOWN_SECS  = 10
XP_PER_LEVEL      = 100

SUPPORTER_LINK = "https://discord.gg/ZptqBM8ZC3"
DB_FILE = "db.json"

TOUR_HUB_CHANNEL_ID    = 1510038159751254047
TOUR_REG_CHANNEL_ID    = 1410696022463877320
TOUR_PING_ROLE_ID      = 1508572231326896269
EVENT_INFO_CHANNEL_ID  = 1410696018231824508
EVENT_START_CHANNEL_ID = 1410696026830143559

ADMIN_TOUR_ROLE_ID  = 1510189891361837167   # can host FFA / World Cup
BOOSTER_ROLE_ID     = 1410695942574833675   # given on boost
SG_VERIFIED_ROLE_ID = 1510193637785473185   # given after SG account link
SG_LINK_TICKET_CAT  = 1510195918291468420   # category for SG link tickets

TRIAL_MOD_ROLE_ID   = 1410695923235033148

# Staff role hierarchy (index 0 = lowest, 5 = highest)
STAFF_HIERARCHY = [
    1410695923235033148,  # 0 — Trial Moderator
    1410695921175494797,  # 1 — Moderator
    1410695920068198420,  # 2 — Head Moderator
    1410695919187398820,  # 3 — Admin
    1410695916687720518,  # 4 — Head Admin
    1410695915689213984,  # 5 — Community Manager
]
STAFF_HIERARCHY_NAMES = {
    1410695923235033148: "Trial Moderator",
    1410695921175494797: "Moderator",
    1410695920068198420: "Head Moderator",
    1410695919187398820: "Admin",
    1410695916687720518: "Head Admin",
    1410695915689213984: "Community Manager",
}
# Roles that can see / manage tickets (Head Mod and above)
TICKET_MOD_ROLE_IDS = {
    1410695920068198420,  # Head Moderator
    1410695919187398820,  # Admin
    1410695916687720518,  # Head Admin
    1410695915689213984,  # Community Manager
}

def compute_level(xp: int) -> int:
    """Curva progressiva: livello n costa n×100 XP. level = floor((-1+sqrt(1+8*xp/100))/2)"""
    if xp <= 0:
        return 0
    return int((-1 + math.sqrt(1 + 8 * xp / 100)) / 2)

def xp_to_next_level(current_level: int) -> int:
    """XP necessari per passare al livello successivo."""
    return (current_level + 1) * 100

TEAM_MODES = {"2V2", "3V3", "4V4", "5V5", "6V6", "7V7", "8V8"}

# ── Role IDs ────────────────────────────────────────────────────────────────
HOSTER_ROLE_ID       = 1410695924879196231   # event/tour/bracket/qual/match/winner
STAFF_ROLE_IDS       = {1410695924879196231, 1410695925927645277}  # backward compat
ADMIN_ROLE_IDS       = {                     # big-event / economy / tickets
    1410695919187398820, 1410695916687720518,
    1410695915689213984, 1410695914758344835,
    1410695913856307332,
}
OWNER_ROLE_ID        = 1410695913856307332   # set-welcome / set-ticket / set-supporter
MEMBER_ROLE_ID       = 1410695955308871703
STUMBLE_STAFF_ROLE_ID = 1410695925927645277  # given to accepted staff applicants (channel access)

# ── Channel restrictions ─────────────────────────────────────────────────────
SOCIAL_ONLY_CH  = 1410696034232963273   # supporter / team / boost / link / gems only
SHOP_ONLY_CH    = 1410696028419788891   # :shop / :test only — all other msgs deleted
PROFILE_ONLY_CH = 1410696056857170110   # :profile only
SUPPORTER_VERIFY_CAT = 1410695995951546368   # category for supporter verify tickets
EVENT_PING_ROLE_ID   = 1410695964783673486   # role pinged when event starts
GIVEAWAY_PING_ROLE_ID = 1410695965748232263  # role pinged in giveaways

# ── Level roles ──────────────────────────────────────────────────────────────
LEVEL_ROLES: dict[int, int] = {
    5:  1508578478226804860,
    10: 1508578772314755143,
    15: 1508578988589842494,
    20: 1508579111289884773,
    30: 1508579321709723810,
}
LEVEL_ROLE_THRESHOLDS = sorted(LEVEL_ROLES.keys())   # [5,10,15,20,30]
LEVEL_ROLE_IDS        = set(LEVEL_ROLES.values())

def _level_role_for(level: int) -> int | None:
    """Return the role ID that should be active at this level (or None)."""
    current = None
    for threshold in LEVEL_ROLE_THRESHOLDS:
        if level >= threshold:
            current = LEVEL_ROLES[threshold]
    return current

def staff_only():
    async def predicate(ctx):
        return any(r.id in STAFF_ROLE_IDS for r in ctx.author.roles)
    return commands.check(predicate)

def hoster_only():
    async def predicate(ctx):
        return any(r.id == HOSTER_ROLE_ID for r in ctx.author.roles)
    return commands.check(predicate)

def admin_only():
    async def predicate(ctx):
        return any(r.id in ADMIN_ROLE_IDS for r in ctx.author.roles)
    return commands.check(predicate)

def owner_only():
    async def predicate(ctx):
        return any(r.id == OWNER_ROLE_ID for r in ctx.author.roles)
    return commands.check(predicate)

def big_event_only():
    async def predicate(ctx):
        return any(r.id in ADMIN_ROLE_IDS for r in ctx.author.roles)
    return commands.check(predicate)

RANK_DATA = [
    (0,     None,                "<:ranked:1507509359985295491>",        "Nessun Rank"),
    (1000,  1410695954641850521, "<:RankWood:1505325324672696511>",       "Legno"),
    (2000,  1410695953631154376, "<:RankBronze:1505980128063393833>",     "Bronzo"),
    (3000,  1410695952397762600, "<:RankSilver:1505325648347009166>",     "Argento"),
    (4000,  1410695950950994033, "<:RankGold:1505325823064936658>",       "Oro"),
    (5000,  1410695949730316402, "<:RankPlatinum:1505325989683658843>",   "Platinum"),
    (7000,  1410695948698652813, "<:RankMaster:1505326047552606390>",     "Maestro"),
    (10000, 1410695947570249868, "<:RankChampion:1505979987876909262>",   "Campione"),
]
ALL_RANK_IDS = {r[1] for r in RANK_DATA if r[1]}

STUMBLE_IMG          = "https://cdn.cloudflare.steamstatic.com/steam/apps/1677740/header.jpg"
STUMBLE_TOUR_IMG_PATH = "attached_assets/1780177141655_1780177250262.png"
STUMBLE_IMAGES       = [STUMBLE_IMG, STUMBLE_TOUR_IMG_PATH]

def get_rank_info(punti: int):
    current = RANK_DATA[0]
    for entry in RANK_DATA:
        if punti >= entry[0]:
            current = entry
    return current

def get_rank_emoji(punti: int) -> str:
    return get_rank_info(punti)[2]

async def update_rank_roles(guild: discord.Guild, member: discord.Member, punti: int):
    """Rimuove tutti i rank role e assegna quello corretto."""
    _, new_role_id, _, new_rank_name = get_rank_info(punti)
    to_remove = [r for r in member.roles if r.id in ALL_RANK_IDS]
    try:
        if to_remove:
            await member.remove_roles(*to_remove, reason="Stumble rank update")
        if new_role_id:
            new_role = guild.get_role(new_role_id)
            if new_role is None:
                # Fallback: cerca tra tutti i ruoli della guild
                new_role = discord.utils.get(guild.roles, id=new_role_id)
            if new_role:
                await member.add_roles(new_role, reason=f"Stumble rank: {new_rank_name}")
            else:
                print(f"[rank] Ruolo {new_role_id} ({new_rank_name}) non trovato nella guild")
    except discord.Forbidden:
        print(f"[rank] Permessi insufficienti per gestire i ruoli di {member.display_name}")
    except discord.HTTPException as e:
        print(f"[rank] HTTPException: {e}")

def get_profile_by_name(name: str):
    name_lower = name.lower()
    for prof in db["profiles"].values():
        if prof["name"] == name:
            return prof
    for prof in db["profiles"].values():
        if prof["name"].lower() == name_lower:
            return prof
    return None

def display_with_rank(name: str) -> str:
    prof = get_profile_by_name(name)
    if prof:
        pts     = prof.get("punti", 0)
        w_owned = prof.get("w_owned", [])
        if w_owned:
            pts = pts * 2
        emoji  = get_rank_emoji(pts)
        w_str  = " ".join(E_W for _ in w_owned)
        suffix = f" {w_str}" if w_str else ""
        return f"{emoji} {name}{suffix}"
    return f"{E_NO_RANK} {name}"

db = {
    "profiles": {},
    "tour": None,
    "event": None,
    "big_event": None,
    "teams": [],
    "leaderboard_channel_id": None,
    "leaderboard_msg_ids": [],
    "welcome_channel_id": None,
    "supporter_channel_id": None,
    "supporter_msg_id": None,
    "result_channel_id": None,
    "betting_channel_id": None,
    "supporters": {},
    "gems": {},       # {user_id_str: {"name": str, "sg_name": str, "total": int}}
    "sg_links": {},   # {user_id_str: sg_name}
}

# Global state for supporter weekly verification ticket
_supporter_verify_ticket_id: int | None = None
_supporter_to_remove: set = set()

# Pending SG link verifications: {user_id: {"sg_name": str, "guild_id": int}}
pending_sg_links: dict = {}
active_ai_sessions = set()
groq_api_key = os.environ.get("GROQ_API_KEY")
groq_client = AsyncGroq(api_key=groq_api_key) if groq_api_key else None


def build_gemini_system_instruction() -> str:
    """Build Gemini's complete command reference from the live bot registry.

    This intentionally reads ``bot.commands`` and ``bot.tree`` instead of
    maintaining a second, hand-written command list.  That keeps the AI
    reference synchronized when a command is added, renamed, or converted to
    an application/slash command.
    """
    command_lines = []
    seen = set()

    def add_command(command, source_name=None):
        name = source_name or getattr(command, "name", "")
        if not name or name in seen:
            return
        seen.add(name)
        callback = getattr(command, "callback", None)
        signature = ""
        description = (
            getattr(command, "description", None)
            or getattr(command, "help", None)
            or getattr(command, "short_doc", None)
            or ""
        )
        if callback:
            try:
                parameters = list(inspect.signature(callback).parameters.values())
                # Prefix command callbacks receive Context; application
                # command callbacks receive Interaction.  Neither belongs in
                # the syntax shown to server members.
                if parameters and parameters[0].name in {"ctx", "interaction", "self"}:
                    parameters = parameters[1:]
                parameter_tokens = []
                for parameter in parameters:
                    if parameter.kind == inspect.Parameter.VAR_KEYWORD:
                        token = f"<{parameter.name}...>"
                    elif parameter.kind == inspect.Parameter.VAR_POSITIONAL:
                        token = f"[<{parameter.name}>...]"
                    elif parameter.default is inspect.Parameter.empty:
                        token = f"<{parameter.name}>"
                    else:
                        default = parameter.default
                        token = f"[<{parameter.name}={default}>]"
                    parameter_tokens.append(token)
                command_prefix = ":" if command in bot.commands else "/"
                signature = f"{command_prefix}{name}" + (
                    " " + " ".join(parameter_tokens) if parameter_tokens else ""
                )
                description = (
                    inspect.getdoc(callback)
                    or description
                    or f"Comando {command_prefix}{name} del bot Discord."
                )
            except (TypeError, ValueError):
                command_prefix = ":" if command in bot.commands else "/"
                signature = f"{command_prefix}{name}"
        aliases = getattr(command, "aliases", [])
        alias_text = f" (alias: {', '.join(':' + alias for alias in aliases)})" if aliases else ""
        description = description.strip() or f"Comando :{name} del bot Discord."
        command_lines.append(f"- {signature}{alias_text} — {description}")

    for command in bot.commands:
        add_command(command)

    def add_app_commands(commands):
        for command in commands:
            add_command(command)
            if hasattr(command, "commands"):
                add_app_commands(command.commands)

    add_app_commands(bot.tree.get_commands())
    command_lines.sort(key=str.casefold)
    command_reference = "\n".join(command_lines)

    return (
        "Sei PCF™ system, l'assistente IA ufficiale del server Discord PCF™.\n\n"
        "LINK E INFO SERVER:\n"
        "- Link Invito Ufficiale Server: "
        "https://discord.gg/pcf-cup-community-1046154910368014417\n"
        "- Se un utente chiede il link del server, invia SEMPRE questo link: "
        "https://discord.gg/pcf-cup-community-1046154910368014417\n\n"
        "CREATORI:\n"
        "- Creatori del server: <@1012712686770995201> e "
        "<@1338274535325175810>.\n"
        "- Creatore del bot: <@1338274535325175810> (ha lavorato per 3 mesi "
        "con duro impegno).\n"
        "- Quando gli utenti chiedono chi ha creato il server o il bot, spiega "
        "dettagliatamente queste informazioni usando SEMPRE le menzioni "
        "cliccabili <@1338274535325175810> e "
        "<@1012712686770995201>.\n\n"
        "LISTA E SPIEGAZIONE DEI COMANDI:\n"
        f"La lista seguente contiene tutti i {len(command_lines)} comandi "
        "registrati dal bot (prefix e slash/application command). Gli alias "
        "sono indicati sulla stessa riga e non contano separatamente. Usa "
        "questa lista come riferimento aggiornato e non inventare comandi:\n"
        f"{command_reference or '- Nessun comando registrato.'}\n\n"
        "CONTROLLI ASSISTENTE DM:\n"
        "- :bot — attiva la conversazione con l'assistente IA.\n"
        "- :stop — chiude la conversazione con l'assistente IA.\n\n"
        "SISTEMA DI RILEVAMENTO VIOLAZIONI (MODERAZIONE):\n"
        "- Analizza ogni messaggio dell'utente. Se l'utente scrive parolacce "
        "gravi, insulti, contenuti sessuali/NSFW, richieste di \"nuke\", "
        "\"raid\" o comportamenti malevoli:\n"
        "  1. Inizia tassativamente la risposta con la stringa "
        "[REPORT_ADMIN].\n"
        "  2. Subito dopo, dai una risposta educata ma ferma all'utente, "
        "rifiutando la richiesta o invitandolo a mantenere un linguaggio "
        "appropriato.\n"
        "- Se il messaggio è normale, NON inserire [REPORT_ADMIN].\n\n"
        "REGOLE GENERALI:\n"
        "- Creatori del server: <@1012712686770995201> e "
        "<@1338274535325175810>.\n"
        "- Creatore del bot: <@1338274535325175810> (ha lavorato per 3 mesi "
        "con duro impegno).\n"
        "- Non mostrare mai pensieri interni o schemi. Rispondi sempre nella "
        "lingua dell'utente.\n\n"
        "REGOLE TRATTAMENTO UTENTI IN CHAT:\n"
        "- Se l'utente corrente è <@1338274535325175810> (Adam): trattalo "
        "sempre come il tuo Re e Creatore; chiamalo \"Mio Re\" o \"Sua Maestà\" "
        "con estremo rispetto e devozione.\n"
        "- Se l'utente corrente è <@1012712686770995201> (Piccolofe): sii "
        "molto amichevole, scherzoso ed entusiasta.\n"
        "- Per tutti gli altri utenti: sii cordiale, chiaro e formale.\n\n"
        "REGOLE TASSATIVE DI OUTPUT (FONDAMENTALE):\n"
        "1. Rispondi DIRETTAMENTE ed ESCLUSIVAMENTE con il messaggio finale "
        "destinato all'utente.\n"
        "2. È SEVERAMENTE VIETATO mostrare la tua analisi interna, bozze o "
        "schemi. NON scrivere mai frasi come \"User input:\", \"Context:\", "
        "\"Greeting:\", \"Draft 1\", \"Internal Monologue\" o equivalenti.\n"
        "3. Scrivi solo il testo finale pulito.\n"
        "4. Rispondi SEMPRE ed ESCLUSIVAMENTE nella stessa lingua usata "
        "dall'utente.\n"
        "5. Fornisci risposte dettagliate, chiare e cordiali."
    )

# ── Special role names (auto-created on_ready) ─────────────────────────────
STUMBLE_GAMBLER_ROLE_NAME   = "Stumble Gambler"
BLOCK_DASH_LEGEND_ROLE_NAME = "Block Dash Legend"
SLOT_MACHINE_COST = 300
SLOT_EMOJIS = ["👑", "💎", "🔴", "🐔"]

# ── In-memory: duels & match bets ──────────────────────────────────────────
active_duels: dict = {}
# {msg_id: {state, challenger_id, challenged_id, challenger_name, challenged_name,
#           bet_a, bet_b, confirmed_ids, channel_id, guild_id}}
active_bets: dict = {}
# {match_id_str: {p1, p2, bets: {uid: {choice, amount}}, channel_id}}

def get_profile(user_id, username):
    uid = str(user_id)
    if uid not in db["profiles"]:
        db["profiles"][uid] = {
            "name": username,
            "punti": 0,
            "tornei_v": 0,
            "eventi_v": 0,
            "gemme": 0,
            "rubini": 0,
            "cristalli": 0,
            "xp_msg": 0,
            "level_msg": 0,
            "staff_tours": 0,
            "staff_matches": 0,
            "sg_name": "",
        }
    prof = db["profiles"][uid]
    prof.setdefault("xp_msg", 0)
    prof.setdefault("level_msg", 0)
    prof.setdefault("staff_tours", 0)
    prof.setdefault("staff_matches", 0)
    prof.setdefault("staff_rounds", 0)
    prof.setdefault("staff_week_tours", 0)
    prof.setdefault("staff_week_matches", 0)
    prof.setdefault("staff_week_rounds", 0)
    prof.setdefault("sg_name", "")
    prof.setdefault("w_owned", [])
    prof.setdefault("slot_wins", 0)
    prof.setdefault("slot_ruby_won", 0)
    prof.setdefault("duel_wins", 0)
    return prof

def parse_orario_timestamp(orario_str: str):
    """Parse HH:MM as Italy time (UTC+2) and return Unix UTC timestamp."""
    try:
        h, m = map(int, orario_str.strip().split(":"))
        now_utc = datetime.utcnow()
        tz_offset = timedelta(hours=2)          # Italy / Rome (UTC+2)
        now_it    = now_utc + tz_offset
        target_it = now_it.replace(hour=h, minute=m, second=0, microsecond=0)
        if target_it <= now_it:
            target_it += timedelta(days=1)
        target_utc = target_it - tz_offset
        return calendar.timegm(target_utc.timetuple())
    except Exception:
        return None

def format_num(n: int) -> str:
    if n >= 1000:
        return f"{n/1000:.1f}k".rstrip("0").rstrip(".")
    return str(n)

def parse_member_id(text: str):
    """Estrae lo user ID da un testo tipo '<@123456>' o '123456'."""
    m = re.search(r"<@!?(\d+)>", text.strip())
    if m:
        return int(m.group(1))
    t = text.strip()
    if t.isdigit():
        return int(t)
    return None

def _format_prize(prize_text: str) -> str:
    """Replace Ruby/Cristalli keywords with their emoji in prize text."""
    if not prize_text:
        return prize_text
    result = re.sub(r'\b[Rr]ub[yi]\b',    E_RUBY,    prize_text)
    result = re.sub(r'\b[Rr]ubini\b',     E_RUBY,    result)
    result = re.sub(r'\b[Cc]ristal[li]i?\b', E_CRYSTAL, result)
    return result

def parse_tournament_prizes(prize_text: str) -> dict[int, str]:
    """Parse `1. 500 Ruby, 2. 250 Ruby, 3. 50 Ruby` into position prizes."""
    text = (prize_text or "").strip()
    numbered = re.findall(r"(?:^|[,;\n])\s*(\d+)\.\s*([^,;\n]+)", text)
    prizes = {int(position): value.strip() for position, value in numbered if value.strip()}
    return prizes or ({1: text} if text else {})

def format_tournament_prizes(prize_text: str) -> str:
    prizes = parse_tournament_prizes(prize_text)
    if not prizes:
        return "—"
    return "\n".join(
        f"**{position}.** {_format_prize(prize)}"
        for position, prize in sorted(prizes.items())
    )

def grant_prize(prize_text: str, member: discord.Member):
    """Parsa '5000 Ruby' / '3000 Cristalli' / '500 Gems' e aggiunge al profilo."""
    m = re.search(r"(\d+)", prize_text)
    if not m:
        return
    amount = int(m.group(1))
    lower  = prize_text.lower()
    prof   = get_profile(member.id, member.display_name)
    if any(w in lower for w in ("ruby", "rubi")):
        prof["rubini"] += amount
    elif any(w in lower for w in ("crystal", "cristal")):
        prof["cristalli"] += amount
    elif any(w in lower for w in ("punt", "xp")):
        prof["punti"] += amount
    elif any(w in lower for w in ("gem",)):
        uid_str = str(member.id)
        sg_name = db.get("sg_links", {}).get(uid_str, prof.get("sg_name", ""))
        gems    = db.setdefault("gems", {})
        if uid_str not in gems:
            gems[uid_str] = {"name": member.display_name, "sg_name": sg_name, "total": 0}
        gems[uid_str]["total"]  += amount
        gems[uid_str]["name"]    = member.display_name
        if sg_name:
            gems[uid_str]["sg_name"] = sg_name

# ==========================================
# 📊 LEADERBOARD & BRACKET
# ==========================================
def build_leaderboard_embeds() -> list:
    profiles = list(db["profiles"].values())
    embeds   = []
    categories = [
        (f"{E_XP} Top 10 — Punti",          "punti",    E_XP,      discord.Color.blurple()),
        (f"{E_RUBY} Top 10 — Rubini",        "rubini",   E_RUBY,    discord.Color.red()),
        (f"{E_CRYSTAL} Top 10 — Cristalli",  "cristalli",E_CRYSTAL, discord.Color.teal()),
        (f"{E_CROWN} Top 10 — Tornei Vinti", "tornei_v", E_CROWN,   discord.Color.gold()),
        (f"{E_TROPHY} Top 10 — Eventi Vinti","eventi_v", E_TROPHY,  discord.Color.purple()),
        (f"{E_LEVEL} Top 10 — Livelli Chat", "level_msg",E_LEVEL,   discord.Color.from_rgb(255, 165, 0)),
    ]
    for title, key, icon, color in categories:
        ranked = sorted(profiles, key=lambda p: p.get(key, 0), reverse=True)[:10]
        desc   = ""
        medals = ["🥇", "🥈", "🥉"]
        for i, p in enumerate(ranked):
            medal = medals[i] if i < 3 else f"**#{i+1}**"
            rk    = get_rank_emoji(p.get("punti", 0))
            val   = p.get(key, 0)
            if key == "level_msg":
                xp_tot = p.get("xp_msg", 0)
                desc += f"{medal} {rk} **{p['name']}** — {icon} Lv.**{val}** `({xp_tot} XP)`\n"
            else:
                desc += f"{medal} {rk} **{p['name']}** — {icon} {format_num(val)}\n"
        if not desc:
            desc = "No data yet."
        embed = discord.Embed(title=title, description=desc, color=color)
        embed.set_footer(text=f"Updated: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        embeds.append(embed)
    return embeds

def _is_ffa_match(m_data: dict) -> bool:
    return "p3" in m_data and m_data.get("p3") not in (None, "BYE", "")

MATCHES_PER_PAGE = 8

class FinalWinnerModal(Modal, title="🏆 Set winner"):
    winner_number = TextInput(
        label="Numero del vincitore (1 o 2)",
        placeholder="Scrivi 1 per il primo giocatore o 2 per il secondo",
        min_length=1,
        max_length=1,
    )

    def __init__(self, match_id, p1: str, p2: str):
        super().__init__()
        self.match_id = match_id
        self.p1 = p1
        self.p2 = p2

    async def on_submit(self, interaction: discord.Interaction):
        if self.winner_number.value not in ("1", "2"):
            return await interaction.response.send_message(
                "❌ Scrivi solo **1** o **2**.", ephemeral=True
            )
        t = db.get("tour")
        if not t or str(self.match_id) not in {str(mid) for mid in t.get("matches", {})}:
            return await interaction.response.send_message(
                "❌ Questo torneo non è più attivo.", ephemeral=True
            )
        match_key = next(mid for mid in t["matches"] if str(mid) == str(self.match_id))
        match_data = t["matches"][match_key]
        if match_data.get("winner"):
            return await interaction.response.send_message(
                "❌ Questo match ha già un vincitore.", ephemeral=True
            )
        winner = self.p1 if self.winner_number.value == "1" else self.p2
        loser = self.p2 if self.winner_number.value == "1" else self.p1
        match_data["winner"] = winner
        match_data["loser"] = loser
        match_data["in_progress"] = False

        winner_id = match_data.get("id1" if self.winner_number.value == "1" else "id2")
        if winner_id and str(winner_id).isdigit() and interaction.guild:
            member = interaction.guild.get_member(int(winner_id))
            if member:
                prof = get_profile(member.id, member.display_name)
                old_pts = prof["punti"]
                prof["punti"] += 100
                await update_rank_roles(interaction.guild, member, prof["punti"])
                if get_rank_info(prof["punti"])[0] > get_rank_info(old_pts)[0]:
                    new_rank = get_rank_info(prof["punti"])
                    await interaction.channel.send(
                        f"🎉 {member.mention} → **{new_rank[3]}** {new_rank[2]}!",
                        delete_after=10.0,
                    )
        save_db()
        await interaction.response.send_message(
            f"✅ Vincitore registrato: **{winner}** (giocatore {self.winner_number.value}).",
            ephemeral=True,
        )
        await _update_bracket_messages(t)


class QualifyView(View):
    """Button shown on the last bracket embed to reveal qualified players."""
    def __init__(self, qualified: list[str], final_match=None):
        super().__init__(timeout=None)
        self.qualified = qualified
        self.final_match = final_match

    @discord.ui.button(label="🏅 Qualify — See who advances", style=discord.ButtonStyle.success, custom_id="qualify_btn")
    async def qualify_btn(self, interaction: discord.Interaction, button: Button):
        is_host = any(r.id == HOSTER_ROLE_ID for r in interaction.user.roles)
        is_admin = any(r.id in ADMIN_ROLE_IDS for r in interaction.user.roles)
        if not is_host and not is_admin:
            return await interaction.response.send_message("❌ Only hosts/admins can see this!", ephemeral=True)
        lines = "\n".join(f"**{i+1}.** {name}" for i, name in enumerate(self.qualified)) or "No qualified players yet."
        await interaction.response.send_message(
            f"🏅 **Qualified for next round ({len(self.qualified)} players):**\n{lines}",
            ephemeral=True
        )

    @discord.ui.button(label="🏆 Set winner", style=discord.ButtonStyle.primary, custom_id="bracket_set_final_winner")
    async def set_final_winner(self, interaction: discord.Interaction, button: Button):
        is_host = any(r.id == HOSTER_ROLE_ID for r in interaction.user.roles)
        is_admin = any(r.id in ADMIN_ROLE_IDS for r in interaction.user.roles)
        if not is_host and not is_admin:
            return await interaction.response.send_message("❌ Solo host/admin possono farlo.", ephemeral=True)
        if not self.final_match:
            return await interaction.response.send_message(
                "❌ Il pulsante è disponibile solo nell'ultimo round 1v1.", ephemeral=True
            )
        match_id, match_data = self.final_match
        await interaction.response.send_modal(
            FinalWinnerModal(match_id, match_data["p1"], match_data["p2"])
        )


def generate_bracket_embeds() -> list[tuple]:
    """Returns list of (embed, view|None). First embed has tour info; last has image + QualifyView."""
    t            = db["tour"]
    cur_round    = t.get("round", 1)
    total_rounds = t.get("total_rounds", "?")
    modalita     = t.get("modalita", "1V1")

    match_lines: list[str] = []
    for m_id, m_data in t["matches"].items():
        p1  = m_data["p1"]
        p2  = m_data["p2"]
        p3  = m_data.get("p3")
        win = m_data.get("winner")
        in_prog = m_data.get("in_progress", False)
        d1  = display_with_rank(p1)
        if _is_ffa_match(m_data):
            d2 = display_with_rank(p2) if p2 not in (None, "BYE") else "~~BYE~~"
            d3 = display_with_rank(p3) if p3 not in (None, "BYE") else "~~BYE~~"
            if win:
                dw     = display_with_rank(win)
                losers = m_data.get("losers", [])
                s1 = f"~~{d1}~~" if p1 in losers else (f"**{d1}**" if p1 == win else d1)
                s2 = f"~~{d2}~~" if p2 in losers else (f"**{d2}**" if p2 == win else d2)
                s3 = f"~~{d3}~~" if p3 in losers else (f"**{d3}**" if p3 == win else d3)
                match_lines.append(f"✅ **Match #{m_id}** — FFA Done\n　{s1} ⚔️ {s2} ⚔️ {s3}\n　🏅 Winner: **{dw}**\n━━━━━━━━━━━━━━━━\n")
            elif in_prog:
                match_lines.append(f"💥 **Match #{m_id}** — FFA In Progress\n　{d1} ⚔️ {d2} ⚔️ {d3}\n━━━━━━━━━━━━━━━━\n")
            else:
                match_lines.append(f"⏳ **Match #{m_id}** — FFA\n　{d1} ⚔️ {d2} ⚔️ {d3}\n━━━━━━━━━━━━━━━━\n")
        else:
            d2 = display_with_rank(p2) if p2 != "BYE" else "~~BYE~~"
            if p2 == "BYE":
                match_lines.append(f"✅ **Match #{m_id}** — Done\n　**{d1}** ⚔️ {d2}\n　🏅 Winner: **{d1}**\n━━━━━━━━━━━━━━━━\n")
            elif win:
                los = m_data.get("loser")
                s1  = f"~~{d1}~~" if los == p1 else f"**{d1}**"
                s2  = f"~~{d2}~~" if los == p2 else f"**{d2}**"
                dw  = display_with_rank(win)
                match_lines.append(f"✅ **Match #{m_id}** — Done\n　{s1} ⚔️ {s2}\n　🏅 Winner: **{dw}**\n━━━━━━━━━━━━━━━━\n")
            elif in_prog:
                match_lines.append(f"💥 **Match #{m_id}** — In Progress\n　{d1} ⚔️ {d2}\n━━━━━━━━━━━━━━━━\n")
            else:
                match_lines.append(f"⏳ **Match #{m_id}**\n　{d1} ⚔️ {d2}\n━━━━━━━━━━━━━━━━\n")

    if not match_lines:
        match_lines = ["*No matches yet.*\n"]
    chunks     = [match_lines[i:i+MATCHES_PER_PAGE] for i in range(0, len(match_lines), MATCHES_PER_PAGE)]
    total_pgs  = len(chunks)
    result: list[tuple] = []

    qualified = [m["winner"] for m in t["matches"].values() if m.get("winner")]
    final_match = None
    if cur_round == total_rounds and len(t["matches"]) == 1:
        only_match = next(iter(t["matches"].items()))
        if not _is_ffa_match(only_match[1]) and only_match[1].get("p2") != "BYE":
            final_match = only_match

    for pg, chunk in enumerate(chunks):
        is_first = pg == 0
        is_last  = pg == total_pgs - 1
        if is_first:
            info = (
                f"**Round {cur_round}"
                + (f"/{total_rounds}" if total_rounds != "?" else "")
                + f"**\n🗺️ **Map:** {t['mappa']}\n⚡ **Ability:** {t['emote']}\n🎁 **Prizes:**\n{format_tournament_prizes(t['premio'])}\n"
            )
            if modalita not in TEAM_MODES:
                info += f"👥 **Players:** {len(t['players'])}/{t['max']}\n"
            info += "─────────────────────\n\n"
            desc = info + "".join(chunk)
        else:
            desc = "".join(chunk)

        pg_label = f" (Page {pg+1}/{total_pgs})" if total_pgs > 1 else ""
        embed = discord.Embed(
            title=f"🏆 Tournament — {modalita}{pg_label}",
            description=desc[:4096],
            color=discord.Color.gold()
        )
        if is_last:
            embed.set_footer(text=f"Host: {t['host_name']} • :bracket <round> to advance")
            embed.set_image(url=STUMBLE_IMG)
            view = QualifyView(qualified, final_match=final_match)
        else:
            embed.set_footer(text=f"Host: {t['host_name']} • continues on next page →")
            view = None
        result.append((embed, view))
    return result

async def _update_bracket_messages(t: dict):
    """Delete old bracket embeds and resend the updated pages."""
    ch = bot.get_channel(t.get("bracket_channel_id"))
    if not ch:
        return
    all_ids = list(t.get("bracket_msg_ids", []))
    old_single = t.get("bracket_msg_id")
    if old_single and old_single not in all_ids:
        all_ids.append(old_single)
    for mid in all_ids:
        try:
            msg = await ch.fetch_message(mid)
            await msg.delete()
        except Exception:
            pass
    pairs    = generate_bracket_embeds()
    sent_ids = []
    for em, vw in pairs:
        m = await ch.send(embed=em, view=vw) if vw else await ch.send(embed=em)
        sent_ids.append(m.id)
    t["bracket_msg_ids"] = sent_ids
    t["bracket_msg_id"]  = sent_ids[-1] if sent_ids else None
    save_db()


async def _auto_generate_bracket(guild: discord.Guild, t: dict):
    """Auto-generate bracket when tournament is full, then DM hosts their matches."""
    modalita = t.get("modalita", "1V1")
    if modalita == "FFA":
        current = len(t["players"])
        target  = current if current % 3 == 0 else current + (3 - current % 3)
        for i in range(target - current):
            t["players"].append(f"Bot_{current+i+1}")
            t["player_names"].append(f"Bot {current+i+1}")
        total_rounds = _ffa_total_rounds(len(t["player_names"]))
        t["matches"]      = _build_ffa_matches(t["player_names"])
        t["round"]        = 1
        t["total_rounds"] = total_rounds
    elif modalita in TEAM_MODES:
        registered_ids = set(str(pid) for pid in t["players"])
        slots, used_ids = [], set()
        for team in db["teams"]:
            if any(uid in registered_ids and uid not in used_ids for uid in team["ids"]):
                slots.append(" × ".join(team["names"]))
                used_ids.update(team["ids"])
        for pid, pname in zip(t["players"], t["player_names"]):
            if str(pid) not in used_ids:
                slots.append(pname)
        bot_idx = 1
        while len(slots) < t["max"]:
            slots.append(f"Bot Team {bot_idx}"); bot_idx += 1
        total_rounds = math.ceil(math.log2(len(slots))) if len(slots) > 1 else 1
        t["matches"]      = _build_round_matches(slots)
        t["round"]        = 1
        t["total_rounds"] = total_rounds
    else:
        names = list(t["player_names"])
        total_rounds = math.ceil(math.log2(len(names))) if len(names) > 1 else 1
        t["matches"] = _build_round_matches(names)
        for idx, (m_id, m_data) in enumerate(t["matches"].items()):
            ii = idx * 2
            m_data["id1"] = t["players"][ii]   if ii   < len(t["players"]) else None
            m_data["id2"] = t["players"][ii+1] if ii+1 < len(t["players"]) else None
        t["round"]        = 1
        t["total_rounds"] = total_rounds
    save_db()
    # Auto-DM hosts their assigned matches
    await _auto_assign_hosts_dm(guild, t)


async def _auto_assign_hosts_dm(guild: discord.Guild, t: dict):
    """DM each registered host their assigned matches for the current round."""
    hosts   = t.get("hosts", [])
    if not hosts:
        return
    matches = t.get("matches", {})
    match_ids = sorted(matches.keys(), key=lambda x: int(x) if str(x).isdigit() else x)
    assignments = {h["id"]: [] for h in hosts}
    i = 0
    for mid in match_ids:
        m_data       = matches[mid]
        match_players = {m_data.get("p1",""), m_data.get("p2",""), m_data.get("p3","")}
        for j in range(len(hosts)):
            h = hosts[(i + j) % len(hosts)]
            if h["name"] not in match_players:
                assignments[h["id"]].append(mid)
                i = (i + 1) % len(hosts)
                break
        else:
            assignments[hosts[i % len(hosts)]["id"]].append(mid)
            i = (i + 1) % len(hosts)
    for h in hosts:
        assigned = assignments.get(h["id"], [])
        if not assigned:
            continue
        try:
            mbr = guild.get_member(int(h["id"])) or await guild.fetch_member(int(h["id"]))
            lines = []
            for mid in assigned:
                m = matches[mid]
                if _is_ffa_match(m):
                    lines.append(f"• Match #{mid}: **{m['p1']}** ⚔️ **{m.get('p2','')}** ⚔️ **{m.get('p3','')}**")
                else:
                    lines.append(f"• Match #{mid}: **{m['p1']}** ⚔️ **{m['p2']}**")
            embed = discord.Embed(
                title=f"🎙️ Your Assigned Matches — Round {t.get('round',1)}",
                description=(
                    f"You are hosting these matches for **{t.get('host_name','?')}'s** tournament:\n\n"
                    + "\n".join(lines)
                    + f"\n\nUse `:match <number> <code>` to send room codes!"
                ),
                color=discord.Color.blurple()
            )
            embed.set_image(url=STUMBLE_IMG)
            await mbr.send(embed=embed)
        except Exception as e:
            print(f"[auto_assign_hosts_dm] {e}")

# ==========================================
# 🔄 BACKGROUND TASKS
# ==========================================
@tasks.loop(hours=1)
async def auto_leaderboard():
    cid = db.get("leaderboard_channel_id")
    if not cid:
        return
    channel = bot.get_channel(cid)
    if not channel:
        return
    embeds = build_leaderboard_embeds()
    for mid in db.get("leaderboard_msg_ids", []):
        try:
            msg = await channel.fetch_message(mid)
            await msg.delete()
        except Exception:
            pass
    new_ids = []
    for embed in embeds:
        m = await channel.send(embed=embed)
        new_ids.append(m.id)
    db["leaderboard_msg_ids"] = new_ids

@tasks.loop(minutes=5)
async def auto_save():
    save_db()

@bot.before_invoke
async def auto_delete_invoke(ctx):
    try:
        await ctx.message.delete()
    except Exception:
        pass

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You don't have permission to use this command.", delete_after=5.0)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument: `{error.param.name}`", delete_after=5.0)
    elif isinstance(error, commands.CommandNotFound):
        pass

@bot.event
async def on_ready():
    load_db()
    print(f"🔥 Stumble™ bot ONLINE!")
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening, name=":tour"))
    if not auto_leaderboard.is_running():
        auto_leaderboard.start()
    if not auto_save.is_running():
        auto_save.start()
    if not check_supporters.is_running():
        check_supporters.start()
    # Auto-create special roles if they don't exist
    for guild in bot.guilds:
        for role_name, color in [
            (STUMBLE_GAMBLER_ROLE_NAME,   discord.Color.gold()),
            (BLOCK_DASH_LEGEND_ROLE_NAME, discord.Color.purple()),
        ]:
            if not discord.utils.get(guild.roles, name=role_name):
                try:
                    await guild.create_role(
                        name=role_name, color=color,
                        reason="Auto-created by Stumble™ bot")
                    print(f"[on_ready] Created role: {role_name}")
                except Exception as e:
                    print(f"[on_ready] Could not create role {role_name}: {e}")

@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild
    member_role = guild.get_role(MEMBER_ROLE_ID)
    if member_role:
        try:
            await member.add_roles(member_role, reason="Auto-assegna ruolo Member")
        except Exception:
            pass
    cid = db.get("welcome_channel_id")
    channel = (
        (bot.get_channel(cid) if cid else None) or
        discord.utils.get(guild.text_channels, name="benvenuto") or
        discord.utils.get(guild.text_channels, name="welcome") or
        discord.utils.get(guild.text_channels, name="generale") or
        discord.utils.get(guild.text_channels, name="general") or
        guild.system_channel or
        (guild.text_channels[0] if guild.text_channels else None)
    )
    if not channel:
        return
    embed = discord.Embed(
        title=f"👋 Welcome to {guild.name}, {member.display_name}!",
        description=(
            f"Hey {member.mention}, welcome to the server! 🎉\n\n"
            f"Make sure to read the rules before anything else. Have fun and good luck! 🏆"
        ),
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Member #{guild.member_count} • Stumble™")
    embed.set_image(url=STUMBLE_IMG)
    await channel.send(content=member.mention, embed=embed)

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if before.premium_since is None and after.premium_since is not None:
        guild      = after.guild
        cid        = db.get("welcome_channel_id")
        channel    = (bot.get_channel(cid) if cid else None) or guild.system_channel

        # Count total boosts for this member (premium_subscription_count isn't directly available;
        # check how many times they've boosted via guild.premium_subscribers count is global.
        # We award by tracking boosts in profile.)
        uid  = str(after.id)
        prof = get_profile(after.id, after.display_name)
        prof.setdefault("boost_count", 0)
        prof["boost_count"] += 1
        boost_n = prof["boost_count"]

        if boost_n >= 2:
            ruby_reward    = 10000
            crystal_reward = 2000
            tier_label     = "💜 **2 Boosts**"
        else:
            ruby_reward    = 5000
            crystal_reward = 1000
            tier_label     = "🔵 **1 Boost**"

        prof["rubini"]    += ruby_reward
        prof["cristalli"] += crystal_reward
        save_db()

        booster_role = guild.get_role(BOOSTER_ROLE_ID)
        if booster_role and booster_role not in after.roles:
            try:
                await after.add_roles(booster_role, reason="Server Boost")
            except Exception as e:
                print(f"[boost role] {e}")

        if channel:
            embed = discord.Embed(
                title="💜 Thank you for boosting!",
                description=(
                    f"🚀 {after.mention} just boosted the server! 🎉\n\n"
                    f"**Tier:** {tier_label}\n"
                    f"**Reward:** {E_RUBY} **{format_num(ruby_reward)} Ruby** + "
                    f"{E_CRYSTAL} **{format_num(crystal_reward)} Crystals**\n\n"
                    "Your support helps the server grow! 💜"
                ),
                color=discord.Color.purple()
            )
            embed.set_thumbnail(url=after.display_avatar.url)
            embed.set_image(url=STUMBLE_IMG)
            try:
                await channel.send(embed=embed)
            except Exception:
                pass


@bot.command(name="set-welcome", aliases=["set_welcome"])
@commands.has_permissions(administrator=True)
async def set_welcome(ctx, channel: discord.TextChannel):
    db["welcome_channel_id"] = channel.id
    save_db()
    await ctx.send(f"✅ Welcome channel set to {channel.mention}.", delete_after=6.0)

# ==========================================
# 👤 PROFILO ED ECONOMIA
# ==========================================
@bot.command()
async def profile(ctx, member: discord.Member = None):
    target = member or ctx.author
    prof   = get_profile(target.id, target.display_name)
    punti  = prof["punti"]
    _, _, rank_emoji, rank_name = get_rank_info(punti)
    next_rank = next((e for e in RANK_DATA if e[0] > punti), None)
    if next_rank:
        prev  = get_rank_info(punti)[0]
        need  = next_rank[0] - prev
        done  = punti - prev
        pct   = min(done / need, 1.0) if need > 0 else 1.0
        bar   = "▰" * int(pct * 10) + "▱" * (10 - int(pct * 10))
        prog  = f"{bar} `{done}/{need}`\nNext: {next_rank[2]} **{next_rank[3]}** ({next_rank[0]} pts)"
    else:
        prog  = "🏆 **Maximum rank reached!**"
    embed = discord.Embed(
        title=f"{rank_emoji} {target.display_name}",
        description=f"**Rank:** {rank_emoji} {rank_name}",
        color=discord.Color.blue()
    )
    level_msg = prof.get("level_msg", 0)
    embed.add_field(name=f"{E_XP} Points",
        value=f"**{format_num(punti)}** pts\n{prog}", inline=False)
    embed.add_field(name="💰 Balance",
        value=f"{E_CRYSTAL} **{format_num(prof['cristalli'])}** Crystals • {E_RUBY} **{format_num(prof['rubini'])}** Ruby",
        inline=False)
    embed.add_field(name="🏅 Stats",
        value=f"{E_CROWN} **{prof['tornei_v']}** tournaments won • {E_TROPHY} **{prof['eventi_v']}** events won",
        inline=False)
    embed.add_field(name="⬆️ Chat Level",
        value=f"Level **{level_msg}** · {format_num(prof.get('xp_msg',0))} XP",
        inline=True)
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.set_image(url=STUMBLE_IMG)
    await ctx.send(embed=embed)

GIVE_KEYS  = {
    "punti":"punti","xp":"punti",
    "ruby":"rubini","rubini":"rubini",
    "cristalli":"cristalli","crystal":"cristalli",
    "tornei":"tornei_v","eventi":"eventi_v",
}
GIVE_ICONS = {"punti":E_XP,"rubini":E_RUBY,"cristalli":E_CRYSTAL,"tornei_v":E_CROWN,"eventi_v":E_TROPHY}

@bot.command(name="give", aliases=["add"])
@admin_only()
async def give(ctx, member: discord.Member, cosa: str, quantita: int):
    key = GIVE_KEYS.get(cosa.lower())
    if not key:
        return await ctx.send(
            f"❌ Invalid currency. Use: `ruby` · `cristalli` · `punti` · `tornei` · `eventi`",
            delete_after=6.0)
    prof = get_profile(member.id, member.display_name)
    prof[key] += quantita
    if key == "punti":
        try:
            await update_rank_roles(ctx.guild, member, prof["punti"])
        except Exception as e:
            print(f"[give rank update] {e}")
    save_db()
    icon = GIVE_ICONS.get(key, "")
    embed = discord.Embed(
        title="✅ Currency Given!",
        description=(
            f"{icon} **+{format_num(quantita)}** {cosa} → {member.mention}\n"
            f"New total: **{format_num(prof[key])}** {icon}"
        ),
        color=discord.Color.green()
    )
    embed.set_footer(text=f"By {ctx.author.display_name}")
    await ctx.send(embed=embed, delete_after=10.0)

@bot.command(name="add-rubini", aliases=["add_rubini"])
@admin_only()
async def add_rubini(ctx, member: discord.Member, amount: int):
    prof = get_profile(member.id, member.display_name)
    prof["rubini"] += amount
    save_db()
    await ctx.send(embed=discord.Embed(
        description=f"{E_RUBY} **+{format_num(amount)} Ruby** → {member.mention}\nNew total: **{format_num(prof['rubini'])}** {E_RUBY}",
        color=discord.Color.green()), delete_after=10.0)

@bot.command(name="remove-rubini", aliases=["remove_rubini"])
@admin_only()
async def remove_rubini_cmd(ctx, member: discord.Member, amount: int):
    prof = get_profile(member.id, member.display_name)
    prof["rubini"] = max(0, prof["rubini"] - amount)
    save_db()
    await ctx.send(embed=discord.Embed(
        description=f"{E_RUBY} **-{format_num(amount)} Ruby** ← {member.mention}\nNew total: **{format_num(prof['rubini'])}** {E_RUBY}",
        color=discord.Color.red()), delete_after=10.0)

@bot.command(name="add-cristalli", aliases=["add_cristalli"])
@admin_only()
async def add_cristalli_cmd(ctx, member: discord.Member, amount: int):
    prof = get_profile(member.id, member.display_name)
    prof["cristalli"] += amount
    save_db()
    await ctx.send(embed=discord.Embed(
        description=f"{E_CRYSTAL} **+{format_num(amount)} Crystals** → {member.mention}\nNew total: **{format_num(prof['cristalli'])}** {E_CRYSTAL}",
        color=discord.Color.green()), delete_after=10.0)

@bot.command(name="add-gems", aliases=["add_gems"])
@admin_only()
async def add_gems_cmd(ctx, member: discord.Member, amount: int):
    prof = get_profile(member.id, member.display_name)
    prof["gemme"] = prof.get("gemme", 0) + amount
    save_db()
    await ctx.send(embed=discord.Embed(
        description=f"{E_GEMS} **+{format_num(amount)} Gems** → {member.mention}\nNew total: **{format_num(prof['gemme'])}** {E_GEMS}",
        color=discord.Color.purple()), delete_after=10.0)

@bot.command(name="add-punti", aliases=["add_punti"])
@admin_only()
async def add_punti_cmd(ctx, member: discord.Member, amount: int):
    prof = get_profile(member.id, member.display_name)
    prof["punti"] += amount
    try:
        await update_rank_roles(ctx.guild, member, prof["punti"])
    except Exception as e:
        print(f"[add-punti rank] {e}")
    save_db()
    await ctx.send(embed=discord.Embed(
        description=f"{E_XP} **+{format_num(amount)} Points** → {member.mention}\nNew total: **{format_num(prof['punti'])}** {E_XP}",
        color=discord.Color.green()), delete_after=10.0)

@bot.command(name="set-rank", aliases=["set_rank"])
@admin_only()
async def set_rank_cmd(ctx, member: discord.Member, *, rank_name: str):
    target = rank_name.strip().lower()
    found  = None
    for entry in RANK_DATA:
        if target in entry[3].lower() or target == entry[3].lower():
            found = entry
            break
    if not found:
        rank_list = " · ".join(r[3] for r in RANK_DATA)
        return await ctx.send(f"❌ Rank not found. Available: `{rank_list}`", delete_after=8.0)
    prof = get_profile(member.id, member.display_name)
    prof["punti"] = found[0]
    try:
        await update_rank_roles(ctx.guild, member, prof["punti"])
    except Exception as e:
        print(f"[set-rank roles] {e}")
    save_db()
    await ctx.send(embed=discord.Embed(
        description=f"{found[2]} Rank set to **{found[3]}** for {member.mention}",
        color=discord.Color.blue()), delete_after=10.0)

RESET_KEYS = {
    "punti":"punti","xp":"punti",
    "ruby":"rubini","rubini":"rubini",
    "cristalli":"cristalli","crystal":"cristalli",
    "tornei":"tornei_v","eventi":"eventi_v","tutto":None,
}

@bot.command(name="reset")
async def reset_stat(ctx, member: discord.Member, cosa: str):
    cosa_l = cosa.lower()
    if cosa_l not in RESET_KEYS:
        return await ctx.send("❌ Usa: `punti / ruby / cristalli / tornei / eventi / tutto`", delete_after=5.0)
    prof = get_profile(member.id, member.display_name)
    if cosa_l == "tutto":
        for k in ["punti","rubini","cristalli","tornei_v","eventi_v"]:
            prof[k] = 0
        desc = "Tutti i dati resettati a 0"
    else:
        prof[RESET_KEYS[cosa_l]] = 0
        desc = f"{cosa} resettati a 0"
    if cosa_l in ("punti","xp","tutto"):
        to_remove = [r for r in member.roles if r.id in ALL_RANK_IDS]
        try:
            if to_remove:
                await member.remove_roles(*to_remove)
        except discord.Forbidden:
            pass
    save_db()
    embed = discord.Embed(title="🔄 Reset completato",
        description=f"{member.mention} — {desc}", color=discord.Color.orange())
    await ctx.send(embed=embed, delete_after=8.0)

# ==========================================
# 🛍️ SHOP
# ==========================================
@bot.command()
async def shop(ctx):
    embed = discord.Embed(
        title="🛍️ Shop — Stumble™",
        description=(
            "⚙️ **We're still working on this!**\n\n"
            f"All items will cost {E_RUBY} **Ruby** or {E_CRYSTAL} **Crystals**.\n\n"
            "🔔 Stay tuned for updates — the shop is coming soon!"
        ),
        color=discord.Color.orange()
    )
    embed.set_image(url=STUMBLE_IMG)
    embed.set_footer(text="Stumble™ Shop — Coming Soon")
    await ctx.send(embed=embed)

# ==========================================
# 🤝 TEAM SYSTEM
# ==========================================
pending_invites: dict = {}

class TeamInviteView(View):
    def __init__(self, team_id: str, invitee_id: int, leader_name: str, mode: str):
        super().__init__(timeout=120)
        self.team_id    = team_id
        self.invitee_id = invitee_id
        self.leader_name = leader_name
        self.mode       = mode

    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.invitee_id:
            return await interaction.response.send_message("❌ This invite is not for you.", ephemeral=True)
        if self.team_id not in pending_invites:
            return await interaction.response.send_message("❌ Invite expired or already closed.", ephemeral=True)
        invite = pending_invites[self.team_id]
        invite["accepted"].add(interaction.user.id)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=f"✅ You joined **{self.leader_name}**'s **{self.mode}** team!",
            view=self
        )
        await _check_team_complete(interaction.guild, self.team_id)

    @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.invitee_id:
            return await interaction.response.send_message("❌ This invite is not for you.", ephemeral=True)
        if self.team_id not in pending_invites:
            return await interaction.response.send_message("❌ Invite expired or already closed.", ephemeral=True)
        invite = pending_invites[self.team_id]
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=f"❌ You declined the team invite from **{self.leader_name}**.",
            view=self
        )
        leader = invite["leader"]
        try:
            await leader.send(f"❌ **{interaction.user.display_name}** declined your **{self.mode}** team invite.")
        except Exception:
            pass
        if self.team_id in pending_invites:
            del pending_invites[self.team_id]

async def _check_team_complete(guild, team_id: str):
    if team_id not in pending_invites:
        return
    invite = pending_invites[team_id]
    all_invited_ids = {m.id for m in invite["invited"]}
    if not all_invited_ids.issubset(invite["accepted"]):
        return
    leader      = invite["leader"]
    members     = invite["invited"]
    bot_names   = invite.get("bot_names", [])
    bot_ids     = invite.get("bot_ids", [])
    all_members = [leader] + members
    names = [m.display_name for m in all_members] + bot_names
    ids   = [str(m.id)      for m in all_members] + bot_ids
    db["teams"] = [t for t in db["teams"] if not any(uid in t["ids"] for uid in ids)]
    db["teams"].append({
        "members": [],
        "names":   names,
        "ids":     ids,
        "leader_id": str(leader.id),
    })
    save_db()
    embed = discord.Embed(
        title="🤝 Team Ready!",
        description="**" + " × ".join(names) + "**",
        color=discord.Color.green()
    )
    embed.add_field(name="👑 Leader",  value=leader.mention,      inline=True)
    embed.add_field(name="👥 Players", value=str(len(all_members)), inline=True)
    embed.set_image(url=STUMBLE_IMG)
    embed.set_footer(text="You can now register for the tournament with the Register button!")
    try:
        await leader.send(embed=embed)
    except Exception:
        pass
    if team_id in pending_invites:
        del pending_invites[team_id]

@bot.command()
async def team(ctx, *args):
    """
    Usi:
      :team @p1 [@p2 ...]          — invita giocatori reali
      :team Bot <N>                — team di N giocatori tutti Bot (escluso te)
      :team @p1 Bot [@p2 Bot ...]  — mix di utenti reali e Bot
    """
    if not args:
        return await ctx.send(
            "❌ Usa: `:team @p1 [@p2 ...]` oppure `:team Bot 3` per un team con i Bot.",
            delete_after=8.0
        )

    # Caso speciale: :team Bot N  (es. :team Bot 3 → team da 3 con tutti Bot)
    if len(args) == 2 and args[0].lower() == "bot" and args[1].isdigit():
        total = int(args[1])
        if total < 2 or total > 8:
            return await ctx.send("❌ La dimensione del team deve essere tra 2 e 8.", delete_after=5.0)
        bot_n  = total - 1
        all_names = [ctx.author.display_name] + [f"🤖 Bot {i+1}" for i in range(bot_n)]
        all_ids   = [str(ctx.author.id)]       + [f"Bot_{i+1}"    for i in range(bot_n)]
        mode_map  = {2:"2V2",3:"3V3",4:"4V4",5:"5V5",6:"6V6",7:"7V7",8:"8V8"}
        mode      = mode_map.get(total, f"{total}V{total}")
        db["teams"] = [t for t in db["teams"] if str(ctx.author.id) not in t["ids"]]
        db["teams"].append({"members":[], "names":all_names, "ids":all_ids, "leader_id":str(ctx.author.id)})
        save_db()
        embed = discord.Embed(
            title="🤝 Team Created!",
            description="**" + " × ".join(all_names) + "**",
            color=discord.Color.green()
        )
        embed.add_field(name="👑 Leader", value=ctx.author.mention, inline=True)
        embed.add_field(name="📐 Mode",   value=mode, inline=True)
        embed.set_image(url=STUMBLE_IMG)
        embed.set_footer(text="You can now register for the tournament with the Register button!")
        return await ctx.send(embed=embed)

    # Parse generica: ogni arg può essere una @mention o "bot"
    real_members = []
    bot_slots    = 0
    for arg in args:
        if arg.lower() == "bot":
            bot_slots += 1
        else:
            try:
                member = await commands.MemberConverter().convert(ctx, arg)
                if member.id == ctx.author.id:
                    return await ctx.send("❌ You can't invite yourself.", delete_after=5.0)
                real_members.append(member)
            except Exception:
                return await ctx.send(
                    f"❌ Can't find `{arg}`. Mention a user with @name or write `Bot`.",
                    delete_after=8.0
                )

    total_size = 1 + len(real_members) + bot_slots
    if total_size < 2:
        return await ctx.send("❌ A team must have at least 2 players.", delete_after=5.0)
    if total_size > 8:
        return await ctx.send("❌ Maximum 8 players per team.", delete_after=5.0)

    mode_map = {2:"2V2",3:"3V3",4:"4V4",5:"5V5",6:"6V6",7:"7V7",8:"8V8"}
    mode     = mode_map.get(total_size, f"{total_size}V{total_size}")

    # Se ci sono solo Bot (nessun invitato reale), crea il team subito
    if not real_members:
        all_names = [ctx.author.display_name] + [f"🤖 Bot {i+1}" for i in range(bot_slots)]
        all_ids   = [str(ctx.author.id)]       + [f"Bot_{i+1}"    for i in range(bot_slots)]
        db["teams"] = [t for t in db["teams"] if str(ctx.author.id) not in t["ids"]]
        db["teams"].append({"members":[], "names":all_names, "ids":all_ids, "leader_id":str(ctx.author.id)})
        save_db()
        embed = discord.Embed(
            title="🤝 Team Created!",
            description="**" + " × ".join(all_names) + "**",
            color=discord.Color.green()
        )
        embed.add_field(name="👑 Leader", value=ctx.author.mention, inline=True)
        embed.add_field(name="📐 Mode",   value=mode, inline=True)
        embed.set_image(url=STUMBLE_IMG)
        embed.set_footer(text="You can now register for the tournament with the Register button!")
        return await ctx.send(embed=embed)

    # Mix reali + Bot: manda DM agli utenti reali, i Bot si aggiungono subito
    import uuid
    team_id = str(uuid.uuid4())[:8]
    bot_names = [f"🤖 Bot {i+1}" for i in range(bot_slots)]
    bot_ids   = [f"Bot_{i+1}"    for i in range(bot_slots)]

    pending_invites[team_id] = {
        "leader":   ctx.author,
        "invited":  list(real_members),
        "accepted": set(),
        "mode":     mode,
        "bot_names": bot_names,
        "bot_ids":   bot_ids,
    }
    all_names_preview = [ctx.author.display_name] + [m.display_name for m in real_members] + bot_names
    sent = 0
    for m in real_members:
        embed = discord.Embed(
            title="🤝 Team Invitation!",
            description=(
                f"**{ctx.author.display_name}** invited you to their **{mode}** team!\n"
                f"You have **2 minutes** to respond."
            ),
            color=discord.Color.blurple()
        )
        embed.add_field(name="👥 Lineup", value=" • ".join(all_names_preview), inline=False)
        embed.set_image(url=STUMBLE_IMG)
        try:
            await m.send(embed=embed, view=TeamInviteView(
                team_id=team_id, invitee_id=m.id,
                leader_name=ctx.author.display_name, mode=mode
            ))
            sent += 1
        except discord.Forbidden:
            pass
    if sent == 0:
        del pending_invites[team_id]
        return await ctx.send("❌ Non riesco a mandare DM agli utenti (DM chiusi).", delete_after=8.0)
    await ctx.send(
        f"📨 Invito **{mode}** inviato a **{', '.join(m.display_name for m in real_members)}**! "
        f"Il team si forma quando tutti accettano.",
        delete_after=12.0
    )
    await asyncio.sleep(120)
    if team_id in pending_invites:
        del pending_invites[team_id]

@bot.command(name="myteam")
async def myteam(ctx):
    uid = str(ctx.author.id)
    my_team = next((t for t in db["teams"] if uid in t["ids"]), None)
    if not my_team:
        return await ctx.send("❌ You are not in any team. Use `:team @friend` to form one.", delete_after=6.0)
    is_leader = my_team["leader_id"] == uid
    embed = discord.Embed(
        title="👥 Your Team",
        description="**" + " × ".join(my_team["names"]) + "**",
        color=discord.Color.blurple()
    )
    embed.add_field(name="👑 Leader", value=my_team["names"][my_team["ids"].index(my_team["leader_id"])], inline=True)
    embed.add_field(name="📐 Mode",   value=f"{len(my_team['names'])}V{len(my_team['names'])}", inline=True)
    if is_leader:
        embed.set_footer(text="You are the team leader!")
    await ctx.send(embed=embed)

@bot.command(name="teamleave")
async def team_leave(ctx):
    uid = str(ctx.author.id)
    db["teams"] = [t for t in db["teams"] if uid not in t["ids"]]
    save_db()
    await ctx.send("✅ Hai lasciato il tuo team.", delete_after=5.0)

# ==========================================
# 🏆 TORNEI — REGISTRATION VIEW
# ==========================================
class TourRegisterView(View):
    def __init__(self, count: int = 0, max_p: int = 32, host_count: int = 0):
        super().__init__(timeout=None)
        for child in self.children:
            if not hasattr(child, "custom_id"):
                continue
            if child.custom_id == "reg_btn":
                child.label = f"✅ Register {count}/{max_p}"
            elif child.custom_id == "host_btn":
                child.label = f"🎙️ Host ({host_count})"

    def _live(self):
        t = db.get("tour") or {}
        return len(t.get("players", [])), t.get("max", 32), len(t.get("hosts", []))

    async def _refresh(self, interaction: discord.Interaction):
        c, m, h = self._live()
        try:
            await interaction.message.edit(view=TourRegisterView(count=c, max_p=m, host_count=h))
        except Exception:
            pass

    @discord.ui.button(label="✅ Register 0/32", style=discord.ButtonStyle.green, custom_id="reg_btn")
    async def register(self, interaction: discord.Interaction, button: Button):
        t = db.get("tour")
        if not t:
            return await interaction.response.send_message("❌ No active tournament.", ephemeral=True)
        modalita = t.get("modalita", "1V1")
        uid      = str(interaction.user.id)
        if modalita in TEAM_MODES:
            user_team = next((tm for tm in db["teams"] if uid in tm["ids"]), None)
            if not user_team:
                return await interaction.response.send_message(
                    f"❌ **{modalita}** tournaments require a team. Use `:team @p2 [@p3...]` first.",
                    ephemeral=True)
        if uid not in t["players"]:
            if len(t["players"]) >= t["max"]:
                return await interaction.response.send_message("❌ Tournament is full!", ephemeral=True)
            # Big-tournament: require SG verified account
            if t.get("is_big"):
                has_sg = any(r.id == SG_VERIFIED_ROLE_ID for r in interaction.user.roles)
                if not has_sg:
                    return await interaction.response.send_message(
                        "❌ You need a **Verified SG account** to join Big Tournaments!\nUse `:link` to connect your account.",
                        ephemeral=True)
            t["players"].append(uid)
            t["player_names"].append(interaction.user.display_name)
        count = len(t["players"])
        max_p = t["max"]
        save_db()
        await interaction.response.send_message(f"✅ Registered! You are participant **#{count}/{max_p}**.", ephemeral=True)
        await self._refresh(interaction)
        # Auto-generate bracket when all slots fill
        if count >= max_p and not t.get("matches"):
            t["bracket_channel_id"] = t.get("register_channel_id") or interaction.channel_id
            await _auto_generate_bracket(interaction.guild, t)
            await _update_bracket_messages(t)

    @discord.ui.button(label="❌ Unregister", style=discord.ButtonStyle.red, custom_id="unreg_btn")
    async def unregister(self, interaction: discord.Interaction, button: Button):
        t = db.get("tour")
        if not t:
            return await interaction.response.send_message("❌ No active tournament.", ephemeral=True)
        uid = str(interaction.user.id)
        if uid in t["players"]:
            idx = t["players"].index(uid)
            t["players"].pop(idx)
            t["player_names"].pop(idx)
        await interaction.response.send_message("❌ Registration cancelled.", ephemeral=True)
        await self._refresh(interaction)

    @discord.ui.button(label="👥 Players", style=discord.ButtonStyle.secondary, custom_id="ply_btn")
    async def players_btn(self, interaction: discord.Interaction, button: Button):
        t = db.get("tour") or {}
        names = t.get("player_names", [])
        lista = "\n".join(f"#{i+1} {n}" for i, n in enumerate(names)) or "No players yet."
        await interaction.response.send_message(
            f"👥 **Players ({len(names)}/{t.get('max',32)}):**\n{lista}", ephemeral=True)

    @discord.ui.button(label="🎙️ Host (0)", style=discord.ButtonStyle.blurple, custom_id="host_btn")
    async def host_btn(self, interaction: discord.Interaction, button: Button):
        is_staff = any(r.id in STAFF_ROLE_IDS for r in interaction.user.roles)
        if not is_staff:
            return await interaction.response.send_message("❌ Only staff can register as host!", ephemeral=True)
        t = db.get("tour")
        if not t:
            return await interaction.response.send_message("❌ No active tournament.", ephemeral=True)
        uid   = str(interaction.user.id)
        hosts = t.setdefault("hosts", [])
        if uid not in [h["id"] for h in hosts]:
            hosts.append({"id": uid, "name": interaction.user.display_name})
            save_db()
        host_count = len(hosts)
        await interaction.response.send_message(
            f"🎙️ Registered as host! Total hosts: **{host_count}**.", ephemeral=True)
        await self._refresh(interaction)

# ==========================================
# 🏆 TORNEI — MODAL & SELEZIONE MODALITÀ
# ==========================================
FORMATO_MAP = {
    "1v1":"1V1","2v2":"2V2","3v3":"3V3",
    "4v4":"4V4","5v5":"5V5","6v6":"6V6",
    "7v7":"7V7","8v8":"8V8",
}

# ── Pending multi-step tournament setup (uid_str → partial data) ─────────────
_pending_tour_setup: dict = {}


class _TourStep2View(View):
    """Shown after Modal1 so the user can open Modal2 with a button click."""
    def __init__(self, uid: str):
        super().__init__(timeout=300)
        self.uid = uid

    @discord.ui.button(label="⚙️ Vai al Passo 2 / 3", style=discord.ButtonStyle.primary)
    async def step2(self, interaction: discord.Interaction, button: Button):
        if str(interaction.user.id) != self.uid:
            return await interaction.response.send_message("❌ Non è il tuo setup!", ephemeral=True)
        data = _pending_tour_setup.get(self.uid, {})
        await interaction.response.send_modal(TourModal2(self.uid, data.get("is_big", False)))


class _TourStep3View(View):
    """Shown after Modal2 so the user can open Modal3 with a button click."""
    def __init__(self, uid: str):
        super().__init__(timeout=300)
        self.uid = uid

    @discord.ui.button(label="📝 Vai al Passo 3 / 3", style=discord.ButtonStyle.success)
    async def step3(self, interaction: discord.Interaction, button: Button):
        if str(interaction.user.id) != self.uid:
            return await interaction.response.send_message("❌ Non è il tuo setup!", ephemeral=True)
        await interaction.response.send_modal(TourModal3(self.uid))


class TourModal1(Modal):
    """Step 1/3 — Nome · Mappa · Abilità · Premio"""
    def __init__(self, modalita: str, is_big: bool = False):
        prefix = "🌟 BIG — " if is_big else ""
        super().__init__(title=f"{prefix}🏆 {modalita} (1/3)"[:45])
        self.modalita = modalita
        self.is_big   = is_big
        self.nome    = TextInput(label="📛 Nome Torneo",       placeholder="es. Stumble™ Classic #42", max_length=50)
        self.mappa   = TextInput(label="🗺️ Mappa",             placeholder="es. Laser Dash")
        self.abilita = TextInput(label="⚡ Abilità / Emote",   placeholder="es. Slap, Punch, Banana…")
        self.premio  = TextInput(
            label="🎁 Premi top 3",
            placeholder="1. 500 Ruby, 2. 250 Ruby, 3. 50 Ruby",
            max_length=200)
        self.add_item(self.nome)
        self.add_item(self.mappa)
        self.add_item(self.abilita)
        self.add_item(self.premio)

    async def on_submit(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        _pending_tour_setup[uid] = {
            "nome":     self.nome.value.strip(),
            "mappa":    self.mappa.value.strip(),
            "abilita":  self.abilita.value.strip(),
            "premio":   self.premio.value.strip(),
            "modalita": self.modalita,
            "is_big":   self.is_big,
        }
        await interaction.response.send_message(
            f"✅ **Passo 1 / 3 completato!**\nNome: `{self.nome.value.strip()}` · "
            f"Mappa: `{self.mappa.value.strip()}`\nPremi il pulsante per continuare.",
            view=_TourStep2View(uid), ephemeral=True)


class TourModal2(Modal):
    """Step 2/3 — Orario · Max giocatori · Regione"""
    def __init__(self, uid: str, is_big: bool = False):
        super().__init__(title=f"🏆 Setup Torneo (2/3)")
        self.uid    = uid
        self.is_big = is_big
        timing_label = "⏰ Orario (HH:MM ora italiana)" if is_big else "⏰ Inizio tra… (es. 15 min)"
        timing_ph    = "es. 20:00" if is_big else "es. 15 min"
        self.timing  = TextInput(label=timing_label, placeholder=timing_ph, max_length=20, required=False)
        self.max_p   = TextInput(label="👥 Max Giocatori (opzionale)", placeholder="es. 32 — lascia vuoto per default", max_length=3, required=False)
        self.regione = TextInput(label="🌍 Regione (opzionale)", placeholder="es. EU, NA, GLOBAL", required=False)
        self.add_item(self.timing)
        self.add_item(self.max_p)
        self.add_item(self.regione)

    async def on_submit(self, interaction: discord.Interaction):
        uid = self.uid
        if uid not in _pending_tour_setup:
            return await interaction.response.send_message("❌ Sessione scaduta — ricomincia con :setup.", ephemeral=True)
        try:
            max_val = int(self.max_p.value.strip()) if self.max_p.value.strip() else None
        except ValueError:
            max_val = None
        _pending_tour_setup[uid].update({
            "timing":  self.timing.value.strip() if self.timing.value else "",
            "max_p":   max_val,
            "regione": self.regione.value.strip() if self.regione.value else "",
        })
        timing_txt = self.timing.value.strip() or "—"
        max_txt    = str(max_val) if max_val else "default"
        reg_txt    = self.regione.value.strip() or "—"
        await interaction.response.send_message(
            f"✅ **Passo 2 / 3 completato!**\nOrario: `{timing_txt}` · Max: `{max_txt}` · Regione: `{reg_txt}`\n"
            f"Premi il pulsante per inserire le note finali e pubblicare il torneo.",
            view=_TourStep3View(uid), ephemeral=True)


class TourModal3(Modal):
    """Step 3/3 — Note host · Colore embed"""
    def __init__(self, uid: str):
        super().__init__(title="🏆 Setup Torneo (3/3)")
        self.uid = uid
        self.note   = TextInput(label="📝 Note per i giocatori (opzionale)", placeholder="es. Nessun lag, connessione stabile…", required=False, style=discord.TextStyle.paragraph, max_length=200)
        self.colore = TextInput(label="🎨 Colore embed (opzionale)", placeholder="gold / green / red / blue / #FF5733", required=False, max_length=20)
        self.add_item(self.note)
        self.add_item(self.colore)

    async def on_submit(self, interaction: discord.Interaction):
        uid = self.uid
        if uid not in _pending_tour_setup:
            return await interaction.response.send_message("❌ Sessione scaduta — ricomincia con :setup.", ephemeral=True)
        data = _pending_tour_setup.pop(uid)
        data["note"]   = self.note.value.strip() if self.note.value else ""
        data["colore"] = self.colore.value.strip() if self.colore.value else ""
        await _finish_tour_creation(interaction, data)


async def _finish_tour_creation(interaction: discord.Interaction, data: dict):
    """Crea il torneo dopo i 3 step modali e lo pubblica nel canale registrazioni."""
    await interaction.response.defer(ephemeral=True)
    modalita    = data["modalita"]
    is_big      = data["is_big"]
    actual      = FORMATO_MAP.get(modalita.lower(), modalita)
    default_max = data.get("max_p") or (30 if modalita == "FFA" else 32)
    nome        = data["nome"]
    emote_s     = data["abilita"] or "—"
    timing_raw  = data.get("timing", "")

    if is_big:
        ts       = parse_orario_timestamp(timing_raw) if timing_raw else None
        time_str = f"<t:{ts}:t> (<t:{ts}:R>)" if ts else (timing_raw or "TBD")
    else:
        time_str = f"in **{timing_raw}**" if timing_raw else "TBD"

    # Colore embed
    col_raw = data.get("colore", "").lower()
    _col_map = {"gold": discord.Color.from_rgb(255,215,0), "green": discord.Color.green(),
                "red": discord.Color.red(), "blue": discord.Color.blue(),
                "purple": discord.Color.purple(), "orange": discord.Color.orange()}
    if col_raw in _col_map:
        color = _col_map[col_raw]
    elif col_raw.startswith("#"):
        try:
            r,g,b = int(col_raw[1:3],16), int(col_raw[3:5],16), int(col_raw[5:7],16)
            color = discord.Color.from_rgb(r,g,b)
        except Exception:
            color = discord.Color.from_rgb(255,215,0) if is_big else discord.Color.green()
    else:
        color = discord.Color.from_rgb(255,215,0) if is_big else discord.Color.green()

    db["tour"] = {
        "host":              interaction.user,
        "host_name":         interaction.user.display_name,
        "modalita":          actual,
        "nome":              nome,
        "premio":            data["premio"],
        "mappa":             data["mappa"],
        "emote":             emote_s,
        "players":           [], "player_names": [], "matches": {},
        "max":               default_max, "round": 1, "total_rounds": "?",
        "bracket_msg_id":    None, "bracket_channel_id": None,
        "is_big":            is_big,
    }

    embed = discord.Embed(title=f"🏆 {'BIG — ' if is_big else ''}{nome}", color=color)
    info_val = (
        f"🎮 **Formato:** {actual}\n"
        f"🗺️ **Mappa:** {data['mappa']}\n"
        f"⚡ **Abilità:** {emote_s}\n"
        f"🎁 **Premi:**\n{format_tournament_prizes(data['premio'])}\n"
        f"⏰ **Inizio:** {time_str}"
    )
    if data.get("regione"):
        info_val += f"\n🌍 **Regione:** {data['regione']}"
    if is_big:
        info_val += "\n🔗 Account SG verificato richiesto per registrarsi!"
    embed.add_field(name="📋 Info", value=info_val, inline=False)
    status_val = (
        f"⏳ Registrazioni aperte — **0/{default_max}**\n"
        f"**Host:** {interaction.user.mention}\n"
        f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    if data.get("note"):
        status_val += f"\n📝 {data['note']}"
    embed.add_field(name="📊 Status", value=status_val, inline=False)
    embed.set_image(url=STUMBLE_IMG)

    prof_host = get_profile(interaction.user.id, interaction.user.display_name)
    prof_host["staff_tours"]      += 1
    prof_host["staff_week_tours"] += 1
    save_db()

    reg_ch = bot.get_channel(TOUR_REG_CHANNEL_ID)
    view   = TourRegisterView(count=0, max_p=default_max, host_count=0)
    if reg_ch:
        if is_big:
            content = f"@everyone 🌟 **BIG TOURNAMENT** annunciato! <@&{TOUR_PING_ROLE_ID}>"
        else:
            content = f"<@&{TOUR_PING_ROLE_ID}> 🏆 Nuovo torneo aperto — registrati!"
        reg_msg = await reg_ch.send(content=content, embed=embed, view=view)
        db["tour"]["register_msg_id"]     = reg_msg.id
        db["tour"]["register_channel_id"] = reg_ch.id
        save_db()
    await interaction.followup.send(
        f"✅ Torneo **{nome}** creato!{f' Vedi {reg_ch.mention}!' if reg_ch else ''}",
        ephemeral=True)


# ── Legacy TourSelectView kept for backward compat ───────────────────────────
class TourSelectView(View):
    def __init__(self, host_id: int):
        super().__init__(timeout=120)
        self.host_id = host_id

    async def _open(self, interaction: discord.Interaction, modalita: str, is_big: bool = False):
        if interaction.user.id != self.host_id:
            return await interaction.response.send_message(
                "❌ Only the host can configure the tournament!", ephemeral=True)
        for child in self.children:
            child.disabled = True
        await interaction.response.send_modal(TourModal1(modalita, is_big=is_big))
        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass

    @discord.ui.button(label="⚔️ FFA — 1v1v1", style=discord.ButtonStyle.primary)
    async def ffa(self, interaction: discord.Interaction, button: Button):
        await self._open(interaction, "FFA")

    @discord.ui.button(label="🏆 Classic", style=discord.ButtonStyle.success)
    async def classic(self, interaction: discord.Interaction, button: Button):
        await self._open(interaction, "Classic")

    @discord.ui.button(label="🌍 World Cup", style=discord.ButtonStyle.danger)
    async def worldcup(self, interaction: discord.Interaction, button: Button):
        await self._open(interaction, "World Cup")


class TourHubView(View):
    def __init__(self, is_big: bool = False):
        super().__init__(timeout=None)
        self.is_big = is_big

    async def _check_staff(self, interaction: discord.Interaction) -> bool:
        has = any(r.id in STAFF_ROLE_IDS | {HOSTER_ROLE_ID} | ADMIN_ROLE_IDS for r in interaction.user.roles)
        if not has:
            await interaction.response.send_message("❌ You don't have permission to do this!", ephemeral=True)
        return has

    async def _check_admin(self, interaction: discord.Interaction) -> bool:
        has = any(r.id in ADMIN_ROLE_IDS | {OWNER_ROLE_ID} for r in interaction.user.roles)
        if not has:
            await interaction.response.send_message("❌ Only **Admins** can do this!", ephemeral=True)
        return has

    @discord.ui.button(label="🏆 Classic", style=discord.ButtonStyle.success, custom_id="hub_classic")
    async def classic(self, interaction: discord.Interaction, button: Button):
        if self.is_big:
            if not await self._check_admin(interaction): return
        else:
            if not await self._check_staff(interaction): return
        await interaction.response.send_modal(TourModal1("Classic", is_big=self.is_big))

    @discord.ui.button(label="🎯 FFA (1v1v1)", style=discord.ButtonStyle.danger, custom_id="hub_ffa")
    async def ffa(self, interaction: discord.Interaction, button: Button):
        if not await self._check_admin(interaction): return
        await interaction.response.send_modal(TourModal1("FFA", is_big=self.is_big))

    @discord.ui.button(label="🌍 World Cup", style=discord.ButtonStyle.primary, custom_id="hub_wc")
    async def world_cup(self, interaction: discord.Interaction, button: Button):
        if not await self._check_admin(interaction): return
        await interaction.response.send_modal(TourModal1("World Cup", is_big=self.is_big))


@bot.command(name="assign-hosts", aliases=["assign_hosts"])
@hoster_only()
async def assign_hosts(ctx):
    """Distribuisce i match del bracket tra gli host registrati."""
    t = db.get("tour")
    if not t:
        return await ctx.send("❌ No active tournament.", delete_after=5.0)
    hosts = t.get("hosts", [])
    if not hosts:
        return await ctx.send("❌ No hosts registered. Press the 🎙️ Host button in the tournament message.", delete_after=6.0)
    matches = t.get("matches", {})
    if not matches:
        return await ctx.send("❌ No bracket generated yet. Use `:start` first to create the bracket.", delete_after=6.0)

    match_ids   = sorted(matches.keys(), key=lambda x: int(x) if str(x).isdigit() else x)
    assignments = {h["id"]: [] for h in hosts}
    player_names_set = set(t.get("player_names", []))

    i = 0
    for mid in match_ids:
        m_data = matches[mid]
        match_players = {m_data.get("p1",""), m_data.get("p2",""), m_data.get("p3","")}
        # Trova un host che non sia un giocatore in questo match
        for j in range(len(hosts)):
            h = hosts[(i + j) % len(hosts)]
            if h["name"] not in match_players:
                assignments[h["id"]].append(mid)
                i = (i + 1) % len(hosts)
                break
        else:
            # Tutti gli host sono in questo match: assegna comunque al prossimo
            assignments[hosts[i % len(hosts)]["id"]].append(mid)
            i = (i + 1) % len(hosts)

    sent = 0
    for h in hosts:
        assigned = assignments.get(h["id"], [])
        if not assigned:
            continue
        member = ctx.guild.get_member(int(h["id"])) if h["id"].isdigit() else None
        if not member:
            continue
        match_list = "\n".join(f"• Match **#{m}** — {matches[m].get('p1','?')} vs {matches[m].get('p2','?')}" for m in assigned)
        embed = discord.Embed(
            title="🎙️ Your Assigned Matches",
            description=(
                f"Hey {member.mention}! Here are your assigned matches for the tournament:\n\n"
                f"{match_list}"
            ),
            color=discord.Color.blurple()
        )
        embed.set_image(url=STUMBLE_IMG)
        embed.set_footer(text=f"Tournament: {t.get('modalita','?')} | Host: {h['name']}")
        try:
            await member.send(embed=embed)
            # Staff stat: +1 per ogni match hostato
            prof_h = get_profile(member.id, member.display_name)
            prof_h["staff_matches"]      += len(assigned)
            prof_h["staff_week_matches"] += len(assigned)
            sent += 1
        except Exception:
            pass
    save_db()
    summary = "\n".join(
        f"• **{h['name']}** → {len(assignments.get(h['id'],[]))} match"
        for h in hosts
    )
    embed = discord.Embed(
        title="✅ Match Distribuiti!",
        description=f"Distribuzione completata per **{sent}** host:\n\n{summary}",
        color=discord.Color.green()
    )
    embed.set_image(url=STUMBLE_IMG)
    await ctx.send(embed=embed)

@bot.command(name="setup", aliases=["setup-tour-hub"])
@owner_only()
async def setup_tour_hub(ctx):
    channel = bot.get_channel(TOUR_HUB_CHANNEL_ID)
    if not channel:
        return await ctx.send("❌ Hub channel not found.", delete_after=5.0)
    embed = discord.Embed(
        title="🏆 Tournament Hub",
        description=(
            "Ready to host? Pick a tournament type below.\n\n"
            "─────────────────────────────────────\n\n"
            "🏆 **Classic** — Standard bracket, earn 🌐 **Ranked Points**\n"
            "*Staff only — Formats: 1v1 · 2v2 · 3v3 · 4v4 · 5v5 · 6v6 · 8v8*\n\n"
            "🎯 **FFA (1v1v1)** — 3-way elimination, 1 winner per match\n"
            "*Admin only — 9 / 27-player brackets*\n\n"
            "🌍 **World Cup** — Bracket tournament, earn 🌐 **WC Points**\n"
            "*Admin only*\n\n"
            "─────────────────────────────────────\n\n"
            "📐 Bracket **auto-generates** when slots fill\n"
            "📬 Hosts are **notified via DM** with their matches"
        ),
        color=discord.Color.gold()
    )
    embed.set_image(url=STUMBLE_IMG)
    embed.set_footer(text="Stumble™ Tournament System")
    await channel.send(embed=embed, view=TourHubView(is_big=False))
    await ctx.send(f"✅ Hub sent to {channel.mention}!", delete_after=5.0)


@bot.command(name="big-tour")
@owner_only()
async def big_tour(ctx):
    embed = discord.Embed(
        title="🌟 BIG TOURNAMENT",
        description=(
            "Select the Big Tournament type!\n\n"
            "🏆 **Classic** · 🎯 **FFA** · 🌍 **World Cup**\n\n"
            "⚠️ This is a **Big Tournament** — **@everyone** will be pinged!\n"
            "Only players with a **Verified SG account** can register."
        ),
        color=discord.Color.from_rgb(255, 215, 0)
    )
    embed.set_image(url=STUMBLE_IMG)
    await ctx.send(embed=embed, view=TourHubView(is_big=True))

# ==========================================
# 🏆 BRACKET HELPERS
# ==========================================
def _build_round_matches(slots: list) -> dict:
    """Bracket 1v1 standard."""
    matches = {}
    for i in range(0, len(slots), 2):
        p1 = slots[i]
        p2 = slots[i+1] if i+1 < len(slots) else "BYE"
        matches[i//2+1] = {
            "p1": p1, "p2": p2, "id1": None, "id2": None,
            "winner": p1 if p2 == "BYE" else None, "loser": None,
        }
    return matches

def _build_ffa_matches(slots: list) -> dict:
    """Bracket FFA: gruppi da 3 (1v1v1)."""
    matches = {}
    mnum    = 1
    i       = 0
    while i < len(slots):
        p1 = slots[i]
        p2 = slots[i+1] if i+1 < len(slots) else "BYE"
        p3 = slots[i+2] if i+2 < len(slots) else "BYE"
        auto_win = None
        if p2 == "BYE" and p3 == "BYE":
            auto_win = p1   # solo un giocatore → BYE automatico
        matches[mnum] = {
            "p1": p1, "p2": p2, "p3": p3,
            "id1": None, "id2": None, "id3": None,
            "winner": auto_win, "losers": [] if not auto_win else [p2, p3],
        }
        mnum += 1
        i    += 3
    return matches

def _ffa_total_rounds(n: int) -> int:
    if n <= 1: return 1
    rounds = 0
    while n > 1:
        n = math.ceil(n / 3)
        rounds += 1
    return rounds

def _generate_bracket_now(t: dict) -> bool:
    """Genera il bracket dai giocatori attuali senza aggiungere bot automatici."""
    modalita = t.get("modalita", "1V1")
    names = list(t["player_names"])
    if len(names) < 2:
        return False
    if modalita == "FFA":
        # FFA needs groups of 3 — pad with bots only if necessary
        while len(names) % 3 != 0:
            idx = len(t["player_names"]) + 1
            names.append(f"Bot {idx}")
            t["players"].append(f"bot_{idx}")
            t["player_names"].append(f"Bot {idx}")
        t["matches"]      = _build_ffa_matches(names)
        t["total_rounds"] = _ffa_total_rounds(len(names))
    elif modalita in TEAM_MODES:
        t["matches"]      = _build_round_matches(names)
        t["total_rounds"] = math.ceil(math.log2(len(names))) if len(names) > 1 else 1
    else:
        t["matches"] = _build_round_matches(names)
        for idx, (m_id, m_data) in enumerate(t["matches"].items()):
            ii = idx * 2
            m_data["id1"] = t["players"][ii]   if ii   < len(t["players"]) else None
            m_data["id2"] = t["players"][ii+1] if ii+1 < len(t["players"]) else None
        t["total_rounds"] = math.ceil(math.log2(len(names))) if len(names) > 1 else 1
    t["round"] = 1
    save_db()
    return True


@bot.command(aliases=["add-bot"])
@hoster_only()
async def add_bot(ctx, n: int = 1):
    """Aggiunge n bot alla lista giocatori senza generare il bracket."""
    if not db["tour"]:
        return await ctx.send("❌ No active tournament configured.", delete_after=5.0)
    t = db["tour"]
    added = 0
    for _ in range(n):
        idx = len(t["player_names"]) + 1
        t["players"].append(f"bot_{idx}")
        t["player_names"].append(f"Bot {idx}")
        added += 1
    save_db()
    total = len(t["player_names"])
    await ctx.send(
        f"🤖 Aggiunti **{added}** bot. Giocatori ora: **{total}/{t['max']}**. "
        f"Usa `:bracket` per avviare!", delete_after=8.0)


@bot.command()
@hoster_only()
async def bracket(ctx, next_round: int = None):
    if not db["tour"]:
        return await ctx.send("❌ No active tournament.")
    t        = db["tour"]
    modalita = t.get("modalita", "1V1")
    cur      = t.get("round", 1)

    # Se non c'è ancora un bracket, generalo dai giocatori attuali
    if not t.get("matches"):
        if len(t["player_names"]) < 2:
            return await ctx.send("❌ Servono almeno **2 giocatori** per generare il bracket!")
        ok = _generate_bracket_now(t)
        if ok:
            await ctx.send(
                f"✅ Bracket generato! **{len(t['player_names'])}** giocatori · "
                f"**{t['total_rounds']}** round(s).", delete_after=6.0)
        t["bracket_channel_id"] = ctx.channel.id
        await _update_bracket_messages(t)
        betting_channel = bot.get_channel(db.get("betting_channel_id")) or ctx.channel
        await _post_match_bets(betting_channel, t)
        return

    if next_round is not None and next_round > cur:
        incomplete = [mid for mid, m in t["matches"].items()
                      if not m.get("winner") and m.get("p2") != "BYE"]
        if incomplete:
            hint = ":qual team @captain" if modalita in TEAM_MODES else ":qual @winner"
            return await ctx.send(f"❌ **{len(incomplete)}** match ancora aperti. Usa `{hint}`.")
        winners = [m["winner"] for m in t["matches"].values() if m.get("winner")]
        if len(winners) < 2:
            return await ctx.send("🏆 Solo 1 vincitore rimasto — usa `:winner-tour` o `:team-winner` per chiudere!")
        t["round"] = next_round
        if modalita == "FFA":
            t["matches"] = _build_ffa_matches(winners)
        else:
            t["matches"] = _build_round_matches(winners)
        save_db()
        await ctx.send(f"🔄 **Round {next_round}** avviato — {len(winners)} giocatori!", delete_after=5.0)
    t["bracket_channel_id"] = ctx.channel.id
    await _update_bracket_messages(t)

async def _give_xp_and_rank(ctx, member, match_data, win_slot):
    """Aggiorna stats di un singolo vincitore 1v1."""
    p1 = match_data["p1"]; p2 = match_data["p2"]
    if win_slot.lower() in p1.lower():
        match_data["winner"] = p1; match_data["loser"] = p2
    else:
        match_data["winner"] = p2; match_data["loser"] = p1
    prof    = get_profile(member.id, member.display_name)
    old_pts = prof["punti"]
    prof["punti"] += 100
    await update_rank_roles(ctx.guild, member, prof["punti"])
    old_rank = get_rank_info(old_pts)
    new_rank = get_rank_info(prof["punti"])
    if new_rank[0] > old_rank[0]:
        try:
            await ctx.send(f"🎉 {member.mention} → **{new_rank[3]}** {new_rank[2]}!", delete_after=10.0)
        except Exception:
            pass

@bot.command()
@hoster_only()
async def qual(ctx):
    if not db["tour"]:
        return
    t        = db["tour"]
    modalita = t.get("modalita", "1V1")
    words    = ctx.message.content.split()
    mentions = ctx.message.mentions
    is_team  = len(words) >= 2 and words[1].lower() == "team"
    # ── Bot qualification: :qual Bot 2 / :qual Bot Team 3 ───────────────────
    is_bot = len(words) >= 2 and words[1].lower() == "bot" and not mentions
    if is_bot:
        bot_name = " ".join(words[1:]) if len(words) > 2 else "Bot"
        found_mid = None
        for mid, m in t["matches"].items():
            if m.get("winner"):
                continue
            p1l = m["p1"].lower(); p2l = m.get("p2","").lower(); p3l = m.get("p3","").lower()
            if bot_name.lower() in p1l or bot_name.lower() in p2l or bot_name.lower() in p3l:
                found_mid = mid; break
            # also match partial e.g. "bot" matches "🤖 Bot 1"
            if "bot" in p1l or "bot" in p2l:
                found_mid = mid; break
        if found_mid is None:
            return await ctx.send(f"❌ No open match found for **{bot_name}**.", delete_after=6.0)
        m = t["matches"][found_mid]
        # Determine which slot is the bot
        p1l = m["p1"].lower(); p2l = m.get("p2","").lower()
        if bot_name.lower() in p1l or "bot" in p1l:
            m["winner"] = m["p1"]; m["loser"] = m.get("p2","")
        else:
            m["winner"] = m["p2"]; m["loser"] = m["p1"]
        save_db()
        await ctx.send(f"✅ **{m['winner']}** qualified (bot)!", delete_after=5.0)
        await _update_bracket_messages(t)
        return

    if is_team:
        if not mentions:
            return await ctx.send("❌ Use: `:qual team @captain`", delete_after=5.0)
        captain  = mentions[0]
        cap_id   = str(captain.id)
        cap_team = next((tm for tm in db["teams"] if tm["leader_id"] == cap_id), None)
        if not cap_team:
            return await ctx.send(f"❌ No team found with captain {captain.mention}.", delete_after=5.0)
        found_mid = None
        for mid, m in t["matches"].items():
            if m.get("winner"):
                continue
            if any(n.lower() in m["p1"].lower() or n.lower() in m["p2"].lower() for n in cap_team["names"]):
                found_mid = mid; break
        if found_mid is None:
            return await ctx.send(f"❌ No open match for {captain.mention}'s team.", delete_after=6.0)
        m  = t["matches"][found_mid]
        p1 = m["p1"]; p2 = m["p2"]
        if any(n.lower() in p1.lower() for n in cap_team["names"]):
            m["winner"] = p1; m["loser"] = p2
        else:
            m["winner"] = p2; m["loser"] = p1
        for uid, name in zip(cap_team["ids"], cap_team["names"]):
            if str(uid).startswith("bot_") or name.startswith("🤖"):
                continue
            try:
                mbr = ctx.guild.get_member(int(uid))
                if mbr:
                    prof    = get_profile(mbr.id, mbr.display_name)
                    old_pts = prof["punti"]
                    prof["punti"] += 100
                    await update_rank_roles(ctx.guild, mbr, prof["punti"])
                    if get_rank_info(prof["punti"])[0] > get_rank_info(old_pts)[0]:
                        nr = get_rank_info(prof["punti"])
                        await ctx.send(f"🎉 {mbr.mention} → **{nr[3]}** {nr[2]}!", delete_after=10.0)
            except Exception:
                pass

    elif modalita == "FFA":
        if not mentions:
            return await ctx.send("❌ Use: `:qual @winner`", delete_after=5.0)
        winner   = mentions[0]
        win_name = winner.display_name
        found_mid = None
        for mid, m in t["matches"].items():
            if m.get("winner"):
                continue
            if win_name.lower() in m["p1"].lower() or win_name.lower() in m.get("p2","").lower() or win_name.lower() in m.get("p3","").lower():
                found_mid = mid; break
        if found_mid is None:
            return await ctx.send(f"❌ No open FFA match for **{win_name}**.", delete_after=6.0)
        m         = t["matches"][found_mid]
        players_3 = [m["p1"], m.get("p2",""), m.get("p3","")]
        win_slot  = next((p for p in players_3 if win_name.lower() in p.lower()), win_name)
        losers    = [p for p in players_3 if p != win_slot and p not in ("BYE","")]
        m["winner"] = win_slot
        m["losers"] = losers
        prof    = get_profile(winner.id, win_name)
        old_pts = prof["punti"]
        prof["punti"] += 100
        await update_rank_roles(ctx.guild, winner, prof["punti"])
        if get_rank_info(prof["punti"])[0] > get_rank_info(old_pts)[0]:
            nr = get_rank_info(prof["punti"])
            await ctx.send(f"🎉 {winner.mention} → **{nr[3]}** {nr[2]}!", delete_after=10.0)

    else:
        if not mentions:
            return await ctx.send("❌ Use: `:qual @winner`", delete_after=5.0)
        winner   = mentions[0]
        win_name = winner.display_name
        found_mid = None
        for mid, m in t["matches"].items():
            if m.get("winner"):
                continue
            if win_name.lower() in m["p1"].lower() or win_name.lower() in m["p2"].lower():
                found_mid = mid; break
        if found_mid is None:
            return await ctx.send(f"❌ No open match for **{win_name}**.", delete_after=6.0)
        await _give_xp_and_rank(ctx, winner, t["matches"][found_mid], win_name)
        # Resolve any tournament bets on this match
        if found_mid is not None:
            asyncio.ensure_future(_resolve_bets_for_match(str(found_mid), t["matches"][found_mid].get("winner", "")))

    save_db()
    await _update_bracket_messages(t)

@bot.command()
@hoster_only()
async def match(ctx, match_num: int, codice: str):
    if not db["tour"]:
        return await ctx.send("❌ No active tournament.")
    if match_num not in db["tour"]["matches"]:
        return await ctx.send(f"❌ Match #{match_num} not found.")
    t        = db["tour"]
    m        = t["matches"][match_num]
    # Mark as in-progress for bracket display
    m["in_progress"] = True
    save_db()
    p1_name  = m["p1"]; p2_name = m["p2"]
    modalita = t.get("modalita", "1V1")
    end_ts   = calendar.timegm((datetime.utcnow() + timedelta(minutes=2)).timetuple())
    players_in_match = [p1_name, p2_name]
    if _is_ffa_match(m):
        players_in_match.append(m.get("p3",""))
        vs_line = f"**{p1_name}** ⚔️ **{p2_name}** ⚔️ **{m.get('p3','')}**"
    else:
        vs_line = f"**{p1_name}** ⚔️ **{p2_name}**"

    def _make_match_embed():
        e = discord.Embed(
            title=f"🏆 {vs_line}",
            description=f"**Match #{match_num}** · Round {t.get('round',1)}/{t.get('total_rounds','?')}",
            color=discord.Color.gold()
        )
        e.add_field(name="🗺️ Map",       value=t["mappa"],        inline=True)
        e.add_field(name="⚡ Ability",    value=t["emote"],        inline=True)
        e.add_field(name="🎁 Prize",      value=_format_prize(t["premio"]), inline=True)
        e.add_field(name="🔑 Room Code",  value=f"```{codice}```",  inline=False)
        e.add_field(name="⏱️ Deadline",   value=f"<t:{end_ts}:R>", inline=False)
        e.set_footer(text=f"Host: {t['host_name']}  •  Stumble™ Tournaments")
        return e

    sent_to = []
    if modalita in TEAM_MODES:
        for team in db["teams"]:
            td    = " × ".join(team["names"])
            in_p1 = any(n.lower() in p1_name.lower() for n in team["names"]) or td == p1_name
            in_p2 = any(n.lower() in p2_name.lower() for n in team["names"]) or td == p2_name
            if in_p1 or in_p2:
                for uid, name in zip(team["ids"], team["names"]):
                    try:
                        mbr   = await ctx.guild.fetch_member(int(uid))
                        embed = _make_match_embed()
                        if os.path.exists(STUMBLE_TOUR_IMG_PATH):
                            f = discord.File(STUMBLE_TOUR_IMG_PATH, filename="stumble_tournament.png")
                            embed.set_image(url="attachment://stumble_tournament.png")
                            await mbr.send(file=f, embed=embed)
                        else:
                            embed.set_image(url=STUMBLE_IMG)
                            await mbr.send(embed=embed)
                        sent_to.append(name)
                    except Exception as e:
                        print(f"[match DM] {e}")
    else:
        for pid, pname in zip(t["players"], t["player_names"]):
            if pname in players_in_match and not str(pid).startswith("Bot_"):
                try:
                    mbr   = await ctx.guild.fetch_member(int(pid))
                    embed = _make_match_embed()
                    if os.path.exists(STUMBLE_TOUR_IMG_PATH):
                        f = discord.File(STUMBLE_TOUR_IMG_PATH, filename="stumble_tournament.png")
                        embed.set_image(url="attachment://stumble_tournament.png")
                        await mbr.send(file=f, embed=embed)
                    else:
                        embed.set_image(url=STUMBLE_IMG)
                        await mbr.send(embed=embed)
                    sent_to.append(pname)
                except Exception as e:
                    print(f"[match DM] {e}")

    await _update_bracket_messages(t)
    if sent_to:
        await ctx.send(f"✅ Room code sent to **{', '.join(sent_to)}** for Match #{match_num}! 💥", delete_after=5.0)
    else:
        embed = _make_match_embed()
        embed.set_image(url=STUMBLE_IMG)
        await ctx.send(embed=embed)

    async def timer_fine():
        await asyncio.sleep(120)
        try:
            await ctx.author.send(
                f"⏰ **Time's up!** Match #{match_num} is over!\n"
                f"Use `:qual @winner` to register the winner."
            )
        except Exception:
            pass
    bot.loop.create_task(timer_fine())

@bot.command(name="close-tour", aliases=["close_tour"])
@hoster_only()
async def close_tour(ctx):
    """Reset the tournament without announcing a winner."""
    if not db.get("tour"):
        return await ctx.send("❌ No active tournament.", delete_after=5.0)
    db["tour"] = None
    save_db()
    embed = discord.Embed(
        title="🔒 Tournament Closed",
        description="The tournament has been closed and reset.",
        color=discord.Color.red()
    )
    embed.set_footer(text=f"Closed by {ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.command(name="end", aliases=["winner-tour", "winner_tour"])
@hoster_only()
async def winner_tour(ctx, *winners: discord.Member):
    t = db["tour"]
    if not t:
        return await ctx.send("❌ No active tournament.", delete_after=5.0)
    if len(winners) > 4:
        return await ctx.send(
            "❌ Indica al massimo 4 persone: 1°, 2°, 3° e 4° posto.",
            delete_after=6.0)
    winner = winners[0] if winners else None
    # Auto-detect winner if not provided
    if winner is None:
        open_matches = [mid for mid, m in t["matches"].items()
                        if not m.get("winner") and m.get("p2") != "BYE"]
        if open_matches:
            return await ctx.send(
                f"❌ There are still **{len(open_matches)}** open matches. "
                f"Use `:qual @winner` to finish them first.", delete_after=6.0)
        final_winners = [m["winner"] for m in t["matches"].values() if m.get("winner")]
        if not final_winners:
            return await ctx.send("❌ No winners found. Use `:qual @winner` to register match results.", delete_after=6.0)
        win_name = final_winners[-1]
        winner_member = None
        for pid, pname in zip(t.get("players",[]), t.get("player_names",[])):
            if pname == win_name:
                try: winner_member = ctx.guild.get_member(int(pid)) or await ctx.guild.fetch_member(int(pid))
                except: pass
                break
        if winner_member is None:
            return await ctx.send(f"🏆 Auto-detected winner: **{win_name}**\n*(Could not find member to award — use `:end @winner` to award manually)*", delete_after=10.0)
        winner = winner_member
    # Only allow when all matches are finished
    open_matches = [mid for mid, m in t["matches"].items()
                    if not m.get("winner") and m.get("p2") != "BYE"]
    if open_matches:
        return await ctx.send(
            f"❌ There are still **{len(open_matches)}** open matches. "
            f"Use `:qual @winner` to finish them first.", delete_after=6.0)
    placements = list(winners) if winners else [winner]
    prize_map = parse_tournament_prizes(t.get("premio", ""))
    for position, member in enumerate(placements, start=1):
        prize_position = min(position, 3)
        prize_text = prize_map.get(prize_position) or prize_map.get(1, "")
        prof = get_profile(member.id, member.display_name)
        prof["tornei_v"] += 1 if position == 1 else 0
        prof["punti"] += 100 if position == 1 else 0
        if prize_text:
            grant_prize(prize_text, member)
        await update_rank_roles(ctx.guild, member, prof["punti"])
    # When four members are provided, places 3 and 4 share the third-place
    # reward and are both displayed as third place.
    result_rows = []
    for position, member in enumerate(placements, start=1):
        shown_position = min(position, 3)
        reward = prize_map.get(shown_position) or prize_map.get(1, "—")
        result_rows.append(
            f"**{shown_position}.** {member.mention} — {_format_prize(reward)}")
    result_lines = "\n".join(result_rows)
    embed = discord.Embed(
        title=f"🏆 {t.get('nome', 'Torneo')} — Risultati",
        description=f"🎁 **Premi**\n{format_tournament_prizes(t.get('premio', ''))}\n\n"
                    f"🏆 **Vincitori**\n{result_lines}",
        color=discord.Color.gold()
    )
    embed.add_field(name=f"{E_XP} Bonus", value="+100 XP Points",           inline=True)
    embed.add_field(name="🗺️ Map",       value=t["mappa"],                  inline=True)
    embed.add_field(name="⚡ Ability",    value=t["emote"],                  inline=True)
    embed.set_thumbnail(url=winner.display_avatar.url)
    embed.set_image(url=STUMBLE_IMG)
    embed.set_footer(text=f"Host: {t['host_name']}")

    is_big = t.get("is_big", False)
    participants = list(t.get("players", []))

    # Track gems in db["gems"] if it's a big tournament
    if is_big:
        sg_name    = db.get("sg_links", {}).get(str(winner.id), winner.display_name)
        prize_text = prize_map.get(1, t.get("premio", ""))
        gem_count  = 0
        _nums = re.findall(r'\d+', prize_text)
        if _nums:
            gem_count = int(_nums[0])
        prof_gems = get_profile(winner.id, winner.display_name)
        prof_gems["gemme"] = prof_gems.get("gemme", 0) + gem_count
        if gem_count > 0:
            embed.add_field(name="💎 Gems",
                value=f"**+{gem_count} Gems** added to {winner.display_name}'s record (SG: `{sg_name}`)",
                inline=False)

    db["tour"] = None
    save_db()

    result_channel = bot.get_channel(db.get("result_channel_id")) or ctx.channel
    if is_big and participants:
        _tour_nome_snap  = t.get("nome", "Big Tournament") if t else "Big Tournament"
        _prize_text_snap = prize_text if is_big else t.get("premio", "")

        class BigTourSentView(View):
            def __init__(self):
                super().__init__(timeout=None)
                self._sent = False

            @discord.ui.button(label="📤 Sent — Notify All Participants", style=discord.ButtonStyle.success)
            async def sent_btn(self, interaction: discord.Interaction, button: Button):
                if self._sent:
                    return await interaction.response.send_message("Already sent!", ephemeral=True)
                if not any(r.id in ADMIN_ROLE_IDS | {OWNER_ROLE_ID} for r in interaction.user.roles):
                    return await interaction.response.send_message("❌ Admin only!", ephemeral=True)
                self._sent      = True
                button.disabled = True
                button.label    = "✅ Notifications Sent"
                count = 0
                for pid in participants:
                    try:
                        user_obj = await bot.fetch_user(int(pid))
                        dm_e = discord.Embed(
                            title="💎 Gems are on their way!",
                            description=(
                                "**The gems have been sent to you!** 🎉\n\n"
                                "They will arrive in a **few days**.\n"
                                "Thank you for your patience! 💙\n\n"
                                f"🏆 **Tournament:** {_tour_nome_snap}\n"
                                f"🎁 **Prize:** {_prize_text_snap}"
                            ),
                            color=discord.Color.green()
                        )
                        dm_e.set_image(url=STUMBLE_IMG)
                        await user_obj.send(embed=dm_e)
                        count += 1
                    except Exception:
                        pass
                await interaction.response.edit_message(
                    content=f"✅ Gem notification sent to **{count}** participants!", view=self)
        await result_channel.send(embed=embed, view=BigTourSentView())
    else:
        await result_channel.send(embed=embed)
    if result_channel.id != ctx.channel.id:
        await ctx.send(f"✅ Risultati pubblicati in {result_channel.mention}.", delete_after=8.0)

@bot.command(name="team-winner", aliases=["team_winner"])
@hoster_only()
async def team_winner(ctx):
    """Close a team tournament and award the winning team."""
    t = db.get("tour")
    if not t:
        return await ctx.send("❌ No active tournament.", delete_after=5.0)
    if t.get("modalita") not in TEAM_MODES:
        return await ctx.send("❌ This command is for team tournaments only. Use `:winner-tour @member` instead.", delete_after=6.0)
    open_matches = [mid for mid, m in t["matches"].items()
                    if not m.get("winner") and m.get("p2") != "BYE"]
    if open_matches:
        return await ctx.send(
            f"❌ There are still **{len(open_matches)}** open matches. "
            f"Use `:qual team @captain` to finish them first.", delete_after=6.0)
    winners = [m["winner"] for m in t["matches"].values() if m.get("winner")]
    if not winners:
        return await ctx.send("❌ No matches completed yet.", delete_after=5.0)
    winning_slot = winners[-1]
    winning_team = next(
        (tm for tm in db["teams"] if " × ".join(tm["names"]) == winning_slot),
        None
    )
    embed = discord.Embed(
        title="🏆 Tournament Complete!",
        description=f"The winning team is **{winning_slot}**! 🎉",
        color=discord.Color.gold()
    )
    embed.add_field(name="🎁 Prizes",     value=format_tournament_prizes(t.get("premio","—")), inline=False)
    embed.add_field(name=f"{E_XP} Bonus", value="+100 XP Points each",              inline=True)
    embed.add_field(name="🗺️ Map",       value=t.get("mappa","—"),                 inline=True)
    embed.add_field(name="⚡ Ability",    value=t.get("emote","—"),                 inline=True)
    embed.set_image(url=STUMBLE_IMG)
    embed.set_footer(text=f"Host: {t.get('host_name','—')}")
    if winning_team:
        for uid, name in zip(winning_team["ids"], winning_team["names"]):
            if str(uid).startswith("bot_") or name.startswith("🤖"):
                continue
            try:
                mbr = ctx.guild.get_member(int(uid))
                if mbr:
                    prof = get_profile(mbr.id, mbr.display_name)
                    prof["tornei_v"] += 1
                    prof["punti"]    += 100
                    grant_prize(t.get("premio",""), mbr)
                    await update_rank_roles(ctx.guild, mbr, prof["punti"])
            except Exception:
                pass
    db["tour"] = None
    save_db()
    await ctx.send(embed=embed)

# ==========================================
# 📊 LEADERBOARD
# ==========================================
@bot.command(name="set-leaderboard", aliases=["set_leaderboard"])
async def set_leaderboard(ctx, channel: discord.TextChannel):
    db["leaderboard_channel_id"] = channel.id
    save_db()
    await ctx.send(f"✅ Leaderboard impostata in {channel.mention}. Si aggiornerà ogni ora.")
    await auto_leaderboard()

@bot.command(name="setup-result", aliases=["setup_result"])
@owner_only()
async def setup_result(ctx, channel: discord.TextChannel):
    """Imposta il canale per i risultati finali dei tornei."""
    db["result_channel_id"] = channel.id
    save_db()
    await ctx.send(f"✅ Risultati torneo impostati in {channel.mention}.", delete_after=8.0)

@bot.command(name="setup-scomesse", aliases=["setup_scomesse", "setup-scommesse"])
@owner_only()
async def setup_scomesse(ctx, channel: discord.TextChannel):
    """Imposta il canale per le scommesse sui match."""
    db["betting_channel_id"] = channel.id
    save_db()
    await ctx.send(f"✅ Scommesse torneo impostate in {channel.mention}.", delete_after=8.0)

@bot.command(name="leaderboard")
async def leaderboard(ctx):
    for embed in build_leaderboard_embeds():
        await ctx.send(embed=embed)

# ==========================================
# ⚡ EVENTI FLASH
# ==========================================
class EventModal(Modal, title="⚡ Create Flash Event"):
    orario = TextInput(label="⏰ Time (HH:MM)", placeholder="e.g. 21:00", max_length=5)
    premio = TextInput(label="🎁 Prize",         placeholder="e.g. 1000 Ruby")
    regole = TextInput(label="📋 Rules",          placeholder="Write the rules...",
                       style=discord.TextStyle.paragraph)

    def __init__(self, channel: discord.TextChannel):
        super().__init__()
        self.target_channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        orario_s = self.orario.value.strip()
        ts       = parse_orario_timestamp(orario_s)
        orario_d = f"<t:{ts}:t> (<t:{ts}:R>)" if ts else orario_s
        db["event"] = {
            "orario":  orario_s,
            "premio":  self.premio.value,
            "regole":  self.regole.value,
            "winners": [],
        }
        save_db()
        embed = discord.Embed(title="📢 NEW FLASH EVENT!", color=discord.Color.purple())
        embed.description = "Get ready! The host will start the event soon. 🎮"
        embed.add_field(name="⏰ Time",          value=orario_d,                         inline=True)
        embed.add_field(name="🎁 Prize",         value=_format_prize(self.premio.value), inline=True)
        embed.add_field(name=f"{E_RULES} Rules", value=self.regole.value,                inline=False)
        embed.set_footer(text=f"Created by {interaction.user.display_name}")
        embed.set_image(url=STUMBLE_IMG)
        try:
            info_ch = bot.get_channel(EVENT_INFO_CHANNEL_ID)
            target  = info_ch if info_ch else self.target_channel
            await target.send(
                content=f"<@&{EVENT_PING_ROLE_ID}> 📢 **Nuovo evento creato!**",
                embed=embed,
                allowed_mentions=discord.AllowedMentions(roles=True),
            )
            await interaction.response.send_message("✅ Event created!", ephemeral=True)
        except Exception:
            await interaction.response.send_message(embed=embed)

class EventSetupView(View):
    def __init__(self, host_id: int, channel: discord.TextChannel):
        super().__init__(timeout=120)
        self.host_id = host_id
        self.channel = channel

    @discord.ui.button(label="⚡ Configure Event", style=discord.ButtonStyle.primary, emoji="📋")
    async def setup(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.host_id:
            return await interaction.response.send_message("❌ Only the host can do this!", ephemeral=True)
        await interaction.response.send_modal(EventModal(channel=self.channel))

@bot.command()
@hoster_only()
async def event(ctx):
    view = EventSetupView(host_id=ctx.author.id, channel=ctx.channel)
    embed = discord.Embed(
        title="⚡ Flash Event Setup",
        description=(
            f"Click below to configure the Flash Event, {ctx.author.mention}!\n\n"
            "Fill in the prize, time, and rules."
        ),
        color=discord.Color.purple()
    )
    embed.set_footer(text=f"Setup by {ctx.author.display_name}")
    embed.set_image(url=STUMBLE_IMG)
    await ctx.send(embed=embed, view=view)

@bot.command(name="start-event", aliases=["start_event"])
@hoster_only()
async def start_event(ctx):
    ev = db.get("event") or db.get("big_event")
    if not ev:
        return await ctx.send("❌ No active event. Use `:event` or `:big-event` first.")
    is_big = bool(db.get("big_event")) and not bool(db.get("event"))
    embed = discord.Embed(
        title="🟢 EVENT STARTED!",
        description="**Get ready! The room code is coming soon! 🏁**",
        color=discord.Color.green()
    )
    if db.get("event"):
        ev_data = db["event"]
        embed.add_field(name="🎁 Prize",          value=_format_prize(ev_data["premio"]), inline=True)
        if ev_data.get("regole"):
            embed.add_field(name=f"{E_RULES} Rules", value=ev_data["regole"],             inline=False)
    elif db.get("big_event"):
        big = db["big_event"]
        embed.add_field(name="🌟 Event",            value=big.get("nome", "—"),                     inline=False)
        embed.add_field(name=f"{E_GOLD} 1st Place",  value=_format_prize(big.get("prize1", "—")),   inline=True)
        embed.add_field(name=f"{E_GOLD} 2nd Place",  value=_format_prize(big.get("prize2", "—")),   inline=True)
        embed.add_field(name=f"{E_BRONZE} 3rd Place",value=_format_prize(big.get("prize3", "—")),   inline=True)
    embed.set_image(url=STUMBLE_IMG)
    embed.set_footer(text=f"Started by {ctx.author.display_name}  •  Stumble™")
    start_ch = bot.get_channel(EVENT_START_CHANNEL_ID) or ctx.channel
    ping_txt  = "@everyone" if is_big else f"<@&{EVENT_PING_ROLE_ID}>"
    allowed   = discord.AllowedMentions(everyone=True) if is_big else discord.AllowedMentions(roles=True)
    await start_ch.send(
        content=f"{ping_txt} 🟢 **The event has started — get in there!**",
        embed=embed,
        allowed_mentions=allowed
    )

@bot.command(name="cod-event", aliases=["cod_event"])
@hoster_only()
async def cod_event(ctx, emote: str, mappa: str, codice: str):
    embed = discord.Embed(title="🎮 FLASH EVENT ROOM", color=discord.Color.dark_teal())
    embed.add_field(name="🗺️ Map",   value=mappa,        inline=True)
    embed.add_field(name="💥 Emote", value=emote,        inline=True)
    embed.add_field(name="🔑 Code",  value=f"`{codice}`", inline=False)
    embed.set_image(url=STUMBLE_IMG)
    prof_staff = get_profile(ctx.author.id, ctx.author.display_name)
    prof_staff["staff_matches"]      += 1
    prof_staff["staff_week_matches"] += 1
    save_db()
    await ctx.send(embed=embed)

@bot.command(name="set-winner", aliases=["set_winner"])
@hoster_only()
async def set_winner(ctx, winner: discord.Member):
    if db["event"] is None:
        return await ctx.send("❌ No active event.")
    db["event"]["winners"].append(winner)
    vittorie = db["event"]["winners"].count(winner)
    embed    = discord.Embed(title="✅ Winner Registered!", color=discord.Color.green())
    embed.description = (
        f"{winner.mention} added!\n"
        f"**Wins:** x{vittorie}\n"
        f"**Estimate:** {_format_prize(db['event'].get('premio','?'))} × {vittorie}"
    )
    embed.set_thumbnail(url=winner.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="end-event", aliases=["end_event"])
@hoster_only()
async def end_event(ctx, base_premio: int, valuta: str):
    if not db["event"] or not db["event"]["winners"]:
        return await ctx.send("❌ No active event or no winners registered.")
    icon = E_CRYSTAL if "crystal" in valuta.lower() else E_RUBY
    conteggio = {}
    for w in db["event"]["winners"]:
        conteggio[w] = conteggio.get(w, 0) + 1
    desc = "**Prize Summary:**\n"
    for w, vittorie in conteggio.items():
        prof = get_profile(w.id, w.display_name)
        tot  = base_premio * vittorie
        prof["eventi_v"] += vittorie
        if icon == E_CRYSTAL:
            prof["cristalli"] += tot
        else:
            prof["rubini"] += tot
        desc += f"• {w.mention}: **x{vittorie}** ➔ +{format_num(tot)} {icon} +{vittorie} {E_TROPHY}\n"
    db["event"] = None
    save_db()
    embed = discord.Embed(title="🏁 FLASH EVENT ENDED", description=desc, color=discord.Color.red())
    embed.set_image(url=STUMBLE_IMG)
    embed.set_footer(text=f"Closed by {ctx.author.display_name}")
    await ctx.send(embed=embed)

# ==========================================
# 🌟 BIG EVENT
# ==========================================
class BigEventModal(Modal, title="🌟 Create Big Event"):
    info   = TextInput(label="🏷️ Event Name | Time/Schedule",
                       placeholder="e.g. Stumble Cup S1 | 21:00  or  Week 1  or  Group Stage")
    prize1 = TextInput(label="🥇 1st Place Prize", placeholder="e.g. 5000 Ruby")
    prize2 = TextInput(label="🥈 2nd Place Prize", placeholder="e.g. 3000 Ruby")
    prize3 = TextInput(label="🥉 3rd Place Prize", placeholder="e.g. 1000 Ruby")
    regole = TextInput(label="Rules",              placeholder="Write the rules...",
                       style=discord.TextStyle.paragraph)

    def __init__(self, channel: discord.TextChannel):
        super().__init__()
        self.target_channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        parts    = self.info.value.split("|")
        nome     = parts[0].strip()
        schedule = parts[1].strip() if len(parts) > 1 else ""
        ts       = parse_orario_timestamp(schedule) if schedule else None
        sched_d  = f"<t:{ts}:t> — <t:{ts}:R>" if ts else (schedule if schedule else "TBD")
        # Store prizes so big-event-winner can auto-read them
        db["big_event"] = {
            "nome":   nome,
            "prize1": self.prize1.value,
            "prize2": self.prize2.value,
            "prize3": self.prize3.value,
        }
        save_db()
        embed = discord.Embed(title=f"🌟 {nome.upper()}",
                              color=discord.Color.from_rgb(255, 215, 0))
        embed.add_field(name="⏰ Schedule",          value=sched_d,                               inline=False)
        embed.add_field(name=f"{E_GOLD} 1st Place",  value=f"**{_format_prize(self.prize1.value)}**", inline=False)
        embed.add_field(name=f"{E_GOLD} 2nd Place",  value=f"**{_format_prize(self.prize2.value)}**", inline=False)
        embed.add_field(name=f"{E_BRONZE} 3rd Place",value=f"**{_format_prize(self.prize3.value)}**", inline=False)
        embed.add_field(name=f"{E_RULES} Rules",     value=self.regole.value,                     inline=False)
        embed.set_footer(text=f"Announced by {interaction.user.display_name} • {datetime.now().strftime('%d/%m/%Y')}")
        embed.set_image(url=STUMBLE_IMG)
        try:
            info_ch = bot.get_channel(EVENT_INFO_CHANNEL_ID)
            target  = info_ch if info_ch else self.target_channel
            await target.send(
                content=f"<@&{EVENT_PING_ROLE_ID}> 🌟 **Nuovo Big Event creato!**",
                embed=embed,
                allowed_mentions=discord.AllowedMentions(roles=True),
            )
            await interaction.response.send_message("✅ Big Event published!", ephemeral=True)
        except Exception:
            await interaction.response.send_message(embed=embed)

class BigEventSetupView(View):
    def __init__(self, host_id: int, channel: discord.TextChannel):
        super().__init__(timeout=120)
        self.host_id = host_id
        self.channel = channel

    @discord.ui.button(label="📝 Configure Big Event", style=discord.ButtonStyle.primary, emoji="🌟")
    async def setup(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.host_id:
            return await interaction.response.send_message("❌ Only the host can do this!", ephemeral=True)
        await interaction.response.send_modal(BigEventModal(channel=self.channel))

@bot.command(name="big-event")
@admin_only()
async def big_event(ctx):
    view = BigEventSetupView(host_id=ctx.author.id, channel=ctx.channel)
    embed = discord.Embed(
        title="🌟 Big Event Setup",
        description=(
            f"Click below to configure the Big Event, {ctx.author.mention}!\n\n"
            "Fill in the name, schedule, prizes, and rules.\n"
            "This will ping **@everyone** when you use `:start-event`."
        ),
        color=discord.Color.from_rgb(255, 215, 0)
    )
    embed.set_footer(text=f"Setup by {ctx.author.display_name}")
    embed.set_image(url=STUMBLE_IMG)
    await ctx.send(embed=embed, view=view)

class BigEventWinnerModal(Modal, title="🏆 Big Event — Final Rankings"):
    primo   = TextInput(label="🥇 1st Place — ID or <@mention>", placeholder="e.g. 123456789 or <@123456789>")
    secondo = TextInput(label="🥈 2nd Place — ID or <@mention>", placeholder="e.g. 123456789 or <@123456789>")
    terzo   = TextInput(label="🥉 3rd Place — ID or <@mention>", placeholder="e.g. 123456789 or <@123456789>")

    def __init__(self, channel: discord.TextChannel):
        super().__init__()
        self.target_channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        guild    = interaction.guild
        big_cfg  = db.get("big_event") or {}
        p1_prize = big_cfg.get("prize1", "—")
        p2_prize = big_cfg.get("prize2", "—")
        p3_prize = big_cfg.get("prize3", "—")

        def resolve(text: str):
            uid = parse_member_id(text)
            if uid and guild:
                mbr = guild.get_member(uid)
                return mbr, (mbr.mention if mbr else text)
            return None, text

        mbr1, d1 = resolve(self.primo.value)
        mbr2, d2 = resolve(self.secondo.value)
        mbr3, d3 = resolve(self.terzo.value)

        for mbr, prize_txt in [(mbr1, p1_prize), (mbr2, p2_prize), (mbr3, p3_prize)]:
            if mbr:
                grant_prize(prize_txt, mbr)
        save_db()

        embed = discord.Embed(title=f"{E_RANKING} BIG EVENT — FINAL RANKINGS",
                              color=discord.Color.from_rgb(255, 215, 0))
        embed.add_field(name=f"{E_GOLD} 1st Place",  value=f"{d1}\n🎁 **{_format_prize(p1_prize)}**", inline=False)
        embed.add_field(name=f"{E_GOLD} 2nd Place",  value=f"{d2}\n🎁 **{_format_prize(p2_prize)}**", inline=False)
        embed.add_field(name=f"{E_BRONZE} 3rd Place",value=f"{d3}\n🎁 **{_format_prize(p3_prize)}**", inline=False)
        embed.set_footer(text=f"By {interaction.user.display_name} • {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        embed.set_image(url=STUMBLE_IMG)

        try:
            await self.target_channel.send(embed=embed)
            await interaction.response.send_message("✅ Rankings published!", ephemeral=True)
        except Exception:
            await interaction.response.send_message(embed=embed)

class BigEventWinnerView(View):
    def __init__(self, host_id: int, channel: discord.TextChannel):
        super().__init__(timeout=120)
        self.host_id = host_id
        self.channel = channel

    @discord.ui.button(label="🏆 Set Winners", style=discord.ButtonStyle.success)
    async def set_winner_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.host_id:
            return await interaction.response.send_message("❌ Only the host can do this!", ephemeral=True)
        await interaction.response.send_modal(BigEventWinnerModal(channel=self.channel))

@bot.command(name="big-start", aliases=["bigstart", "big_start"])
@admin_only()
async def big_start(ctx):
    """Start a big event with @everyone ping."""
    big = db.get("big_event")
    if not big:
        return await ctx.send("❌ No Big Event configured. Use `:big-event` first.", delete_after=6.0)
    embed = discord.Embed(
        title="🟢 BIG EVENT STARTED!",
        description="**Get ready — the room code is coming soon! 🏁**",
        color=discord.Color.green()
    )
    embed.add_field(name="🌟 Event",          value=big.get("nome", "—"),                          inline=False)
    embed.add_field(name=f"{E_GOLD} 1st Place",  value=f"**{_format_prize(big.get('prize1','—'))}**", inline=False)
    embed.add_field(name=f"{E_GOLD} 2nd Place",  value=f"**{_format_prize(big.get('prize2','—'))}**", inline=False)
    embed.add_field(name=f"{E_BRONZE} 3rd Place",value=f"**{_format_prize(big.get('prize3','—'))}**", inline=False)
    embed.set_image(url=STUMBLE_IMG)
    embed.set_footer(text=f"Started by {ctx.author.display_name} • Stumble™")
    start_ch = bot.get_channel(EVENT_START_CHANNEL_ID) or ctx.channel
    await start_ch.send(
        content=f"<@&{EVENT_PING_ROLE_ID}> 🌟 **THE BIG EVENT HAS STARTED — GET IN THERE!** 🔥",
        embed=embed,
        allowed_mentions=discord.AllowedMentions(roles=True)
    )


@bot.command(name="big-event-winner")
@admin_only()
async def big_event_winner(ctx):
    big_cfg = db.get("big_event") or {}
    prizes  = (
        f"📋 **Configured prizes:**\n"
        f"🥇 {_format_prize(big_cfg.get('prize1','—'))}\n"
        f"🥈 {_format_prize(big_cfg.get('prize2','—'))}\n"
        f"🥉 {_format_prize(big_cfg.get('prize3','—'))}"
        if big_cfg else "⚠️ No big event configured yet — run `:big-event` first."
    )
    view = BigEventWinnerView(host_id=ctx.author.id, channel=ctx.channel)
    await ctx.send(f"🏆 Click to set the Big Event winners!\n{prizes}", view=view)

# ==========================================
# 🔄 RESET TOTALE
# ==========================================
class ResetConfirmView(View):
    def __init__(self):
        super().__init__(timeout=30)

    @discord.ui.button(label="⚠️ Sì, resetta tutto", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo gli admin.", ephemeral=True)
        db["profiles"] = {}; db["tour"] = None; db["event"] = None
        db["teams"] = []; db["leaderboard_msg_ids"] = []
        save_db()
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="✅ **Reset completato.**", embed=None, view=self)

    @discord.ui.button(label="❌ Annulla", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="❌ Reset annullato.", embed=None, view=self)

@bot.command(name="reset-all")
async def reset_all(ctx):
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("❌ Solo gli amministratori.", delete_after=5.0)
    embed = discord.Embed(title="⚠️ RESET TOTALE", color=discord.Color.red())
    embed.description = (
        "Stai per cancellare **tutti i dati**:\n\n"
        "• Profili, punti e rank\n• Tornei e bracket\n"
        "• Team\n• Dati eventi\n\n"
        "**Questa azione è irreversibile.**"
    )
    await ctx.send(embed=embed, view=ResetConfirmView())

# ==========================================
# 🎫 TICKET SYSTEM
# ==========================================
# ticket_map: channel_id -> user_id  (per sapere a chi appartiene)
ticket_channel_map: dict = {}

class TicketControlView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="🙋 Claim", style=discord.ButtonStyle.primary, custom_id="ticket_claim")
    async def claim(self, interaction: discord.Interaction, button: Button):
        uid = str(self.user_id)
        if uid not in active_tickets:
            return await interaction.response.send_message("❌ Ticket not found.", ephemeral=True)
        t = active_tickets[uid]
        if t["claimed_by"] and t["claimed_by"] != interaction.user.id:
            claimer = interaction.guild.get_member(t["claimed_by"])
            name = claimer.display_name if claimer else "someone"
            return await interaction.response.send_message(f"❌ Ticket already claimed by **{name}**.", ephemeral=True)
        t["claimed_by"] = interaction.user.id
        await interaction.response.send_message(
            f"✅ {interaction.user.mention} claimed the ticket.", ephemeral=False
        )

    @discord.ui.button(label="🔒 Close", style=discord.ButtonStyle.danger, custom_id="ticket_close")
    async def close(self, interaction: discord.Interaction, button: Button):
        uid = str(self.user_id)
        channel = interaction.channel
        await interaction.response.send_message("🔒 Ticket closed. Channel will be deleted in 5 seconds.")
        if uid in active_tickets:
            user_id = active_tickets[uid]["user_id_int"]
            try:
                user = await bot.fetch_user(user_id)
                await user.send("🔒 Your support ticket has been **closed**. Thank you for contacting us!")
            except Exception:
                pass
            del active_tickets[uid]
        if channel.id in ticket_channel_map:
            del ticket_channel_map[channel.id]
        await asyncio.sleep(5)
        try:
            await channel.delete()
        except Exception:
            pass

class StaffRequestControlView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.success, custom_id="staff_accept")
    async def accept(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        member = guild.get_member(self.user_id)
        if not member and guild:
            try:
                member = await guild.fetch_member(self.user_id)
            except Exception:
                pass
        if not member:
            return await interaction.response.send_message("❌ User not found in server.", ephemeral=True)
        # Determine which roles to give based on application answer
        role_type = active_tickets.get(str(self.user_id), {}).get("role_type", "staff")
        roles_given = []
        if role_type in ("staff", "both"):
            trial_role = guild.get_role(TRIAL_MOD_ROLE_ID)
            if trial_role:
                try:
                    await member.add_roles(trial_role, reason="Staff Application accepted → Trial Moderator")
                    roles_given.append(trial_role.name)
                except Exception as e:
                    print(f"[accept trial_role] {e}")
            stumble_staff_role = guild.get_role(STUMBLE_STAFF_ROLE_ID)
            if stumble_staff_role:
                try:
                    await member.add_roles(stumble_staff_role, reason="Staff Application accepted")
                    roles_given.append(stumble_staff_role.name)
                except Exception as e:
                    print(f"[accept stumble_staff_role] {e}")
        if role_type in ("hoster", "both"):
            hoster_role = guild.get_role(HOSTER_ROLE_ID)
            if hoster_role:
                try:
                    await member.add_roles(hoster_role, reason="Staff Application accepted → Hoster")
                    roles_given.append(hoster_role.name)
                except Exception as e:
                    print(f"[accept hoster_role] {e}")
            stumble_staff_role = guild.get_role(STUMBLE_STAFF_ROLE_ID)
            if stumble_staff_role:
                try:
                    await member.add_roles(stumble_staff_role, reason="Staff Application accepted")
                    if stumble_staff_role.name not in roles_given:
                        roles_given.append(stumble_staff_role.name)
                except Exception as e:
                    print(f"[accept stumble_staff_role hoster] {e}")
        role_str = " · ".join(f"**{r}**" for r in roles_given) if roles_given else "roles (check bot permissions)"
        try:
            embed = discord.Embed(
                title="🎉 Application Accepted!",
                description=(
                    f"Congratulations {member.mention}! 🎊\n\n"
                    "Your **Staff** application has been **accepted**!\n"
                    f"You have been given: {role_str}\n\n"
                    "Welcome to the team! Do your best! 💪"
                ),
                color=discord.Color.green()
            )
            embed.set_image(url=STUMBLE_IMG)
            await member.send(embed=embed)
        except Exception:
            pass
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=f"✅ **{member.display_name}** accepted! Roles given: {role_str}", view=self
        )
        uid = str(self.user_id)
        if uid in active_tickets:
            del active_tickets[uid]
        channel = interaction.channel
        if channel.id in ticket_channel_map:
            del ticket_channel_map[channel.id]
        await asyncio.sleep(5)
        try:
            await channel.delete()
        except Exception:
            pass

    @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.danger, custom_id="staff_decline")
    async def decline(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        member = guild.get_member(self.user_id)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=f"❌ Application from **{member.display_name if member else self.user_id}** declined.", view=self
        )
        if member:
            try:
                embed = discord.Embed(
                    title="💙 Application Not Accepted",
                    description=(
                        f"Hey {member.mention},\n\n"
                        "Unfortunately your **Staff** application was not accepted at this time.\n\n"
                        "Don't give up! Stay active and try again later. "
                        "We value every member of our community! 💪"
                    ),
                    color=discord.Color.blue()
                )
                embed.set_image(url=STUMBLE_IMG)
                await member.send(embed=embed)
            except Exception:
                pass
        uid = str(self.user_id)
        if uid in active_tickets:
            del active_tickets[uid]
        channel = interaction.channel
        if channel.id in ticket_channel_map:
            del ticket_channel_map[channel.id]
        await asyncio.sleep(5)
        try:
            await channel.delete()
        except Exception:
            pass

# Pending staff applications via DM: uid_str → {step, answers, guild_id}
pending_staff_apps: dict = {}

STAFF_APP_QUESTIONS = [
    "📅 **Question 1/5** — How old are you?",
    "💬 **Question 2/5** — Why do you want to be staff? Tell us your motivation.",
    "🎖️ **Question 3/5** — What moderation / server experience do you have?",
    "🎯 **Question 4/5** — Do you want to be a **Hoster**, **Staff**, or **Both**?\n*(Type exactly: `hoster` / `staff` / `both`)*",
    "⏰ **Question 5/5** — How much time per week can you be active? (e.g. `5 hours`, `every day`)",
]


async def _open_staff_ticket(guild: discord.Guild, user: discord.User, answers: dict):
    """Create the staff application ticket after all DM questions are answered."""
    cat = guild.get_channel(TICKET_STAFF_CAT)
    overwrite = {guild.default_role: discord.PermissionOverwrite(read_messages=False)}
    for rid in TICKET_MOD_ROLE_IDS:
        role = guild.get_role(rid)
        if role:
            overwrite[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    try:
        ch = await guild.create_text_channel(
            name=f"staff-{user.display_name[:20]}",
            category=cat, overwrites=overwrite,
            reason="Staff Application ticket")
    except Exception as e:
        print(f"[staff ticket create] {e}")
        return
    uid = str(user.id)
    role_type = answers.get("role_type", "staff")
    active_tickets[uid] = {
        "channel_id": ch.id, "type": "staff",
        "claimed_by": None, "user_id_int": user.id,
        "role_type": role_type,
    }
    ticket_channel_map[ch.id] = user.id
    embed = discord.Embed(title=f"📋 Staff Application — {user.display_name}", color=discord.Color.blue())
    embed.add_field(name="👤 User",        value=user.mention,             inline=True)
    embed.add_field(name="📅 Age",         value=answers.get("age","—"),   inline=True)
    embed.add_field(name="🎯 Role",        value=role_type.capitalize(),   inline=True)
    embed.add_field(name="💬 Motivation",  value=answers.get("why","—"),   inline=False)
    embed.add_field(name="🎖️ Experience", value=answers.get("exp","—"),   inline=False)
    embed.add_field(name="⏰ Availability",value=answers.get("time","—"),  inline=False)
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.set_image(url=STUMBLE_IMG)
    embed.set_footer(text=f"User ID: {user.id}")
    ping_content = f"<@&{STUMBLE_STAFF_ROLE_ID}>"
    await ch.send(content=ping_content, embed=embed, view=StaffRequestControlView(user_id=user.id))

class TicketMainView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🆘 Support", style=discord.ButtonStyle.primary, custom_id="ticket_support")
    async def support(self, interaction: discord.Interaction, button: Button):
        uid = str(interaction.user.id)
        if uid in active_tickets:
            return await interaction.response.send_message("❌ You already have an open ticket!", ephemeral=True)
        guild = interaction.guild
        cat   = guild.get_channel(TICKET_SUPPORT_CAT)
        overwrite = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
        }
        for rid in TICKET_MOD_ROLE_IDS:
            role = guild.get_role(rid)
            if role:
                overwrite[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        try:
            ch = await guild.create_text_channel(
                name=f"support-{interaction.user.display_name[:20]}",
                category=cat,
                overwrites=overwrite,
                reason="Support ticket"
            )
        except Exception as e:
            return await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

        active_tickets[uid] = {"channel_id": ch.id, "type": "support", "claimed_by": None, "user_id_int": interaction.user.id}
        ticket_channel_map[ch.id] = interaction.user.id

        ctrl_embed = discord.Embed(
            title=f"🎫 Support Ticket — {interaction.user.display_name}",
            description=(
                f"User: {interaction.user.mention}\n"
                "Communicate via **DM with the bot**. Messages arrive here in real time."
            ),
            color=discord.Color.blue()
        )
        ctrl_embed.set_image(url=STUMBLE_IMAGES[0])
        ping_content = f"<@&{STUMBLE_STAFF_ROLE_ID}>"
        await ch.send(content=ping_content, embed=ctrl_embed, view=TicketControlView(user_id=interaction.user.id))

        try:
            dm_embed = discord.Embed(
                title="🆘 Ticket Opened!",
                description=(
                    "Hey! 👋\n\n"
                    "Write your message here — our staff will receive it and reply as soon as possible.\n\n"
                    "*(Every message you send here is forwarded to staff)*"
                ),
                color=discord.Color.blue()
            )
            dm_embed.set_image(url=STUMBLE_IMAGES[0])
            await interaction.user.send(embed=dm_embed)
            await interaction.response.send_message("✅ Ticket opened! Check your **DMs** with the bot.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I can't open a DM with you. Enable DMs from this server.", ephemeral=True)
            del active_tickets[uid]
            del ticket_channel_map[ch.id]
            await ch.delete()

    @discord.ui.button(label="👮 Staff Request", style=discord.ButtonStyle.success, custom_id="ticket_staff")
    async def staff_request(self, interaction: discord.Interaction, button: Button):
        uid = str(interaction.user.id)
        if uid in active_tickets or uid in pending_staff_apps:
            return await interaction.response.send_message("❌ You already have an open application or ticket!", ephemeral=True)
        pending_staff_apps[uid] = {"step": 0, "answers": {}, "guild_id": interaction.guild_id}
        try:
            intro = discord.Embed(
                title="📝 Staff Application",
                description=(
                    "Welcome! I'll ask you **5 quick questions** via DM.\n\n"
                    "Answer each one and your application will be automatically submitted to staff. 💙\n\n"
                    f"{STAFF_APP_QUESTIONS[0]}"
                ),
                color=discord.Color.blue()
            )
            intro.set_image(url=STUMBLE_IMG)
            await interaction.user.send(embed=intro)
            await interaction.response.send_message(
                "✅ Check your **DMs**! I've started the application process there.", ephemeral=True)
        except discord.Forbidden:
            pending_staff_apps.pop(uid, None)
            await interaction.response.send_message(
                "❌ I can't DM you. Enable **DMs from server members** and try again.", ephemeral=True)

    @discord.ui.button(label="💎 Gems Transfer", style=discord.ButtonStyle.secondary, custom_id="ticket_gems")
    async def gems_transfer(self, interaction: discord.Interaction, button: Button):
        try:
            embed = discord.Embed(
                title="💎 Gems Transfer",
                description=(
                    "Sorry, the owner **cannot send gems right now**.\n\n"
                    "Support him in his **livestreams** so he can become a Content Creator "
                    "and unlock new things for everyone! 🎮✨\n\n"
                    "Use `:link` to connect your Stumble Guys account and receive gems automatically "
                    "when you win a Big Tournament!"
                ),
                color=discord.Color.purple()
            )
            embed.set_image(url=STUMBLE_IMG)
            await interaction.user.send(embed=embed)
            await interaction.response.send_message("✅ Sent you a DM!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I can't DM you. Please enable DMs from this server.", ephemeral=True
            )

@bot.command(name="add-ticket", aliases=["add_ticket"])
@admin_only()
async def add_ticket(ctx):
    embed = discord.Embed(
        title="🎫 Stumble™ Support",
        description=(
            "Need help? Select a category below!\n\n"
            "🆘 **Support** — Chat with our staff via DM\n"
            "👮 **Staff Request** — Apply to become staff\n"
            "💎 **Gems Transfer** — Info about gem transfers"
        ),
        color=discord.Color.gold()
    )
    embed.set_image(url=STUMBLE_IMG)
    embed.set_footer(text="Stumble™ Support System")
    await ctx.send(embed=embed, view=TicketMainView())

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # ── Direct Messages: AI sessions and support workflows ────────────────
    # DMs have no guild; using this check also covers Discord's DM channel
    # implementations consistently.
    if message.guild is None:
        uid = str(message.author.id)
        command_text = message.content.strip().lower()

        if command_text == ":bot":
            active_ai_sessions.add(message.author.id)
            if message.author.id == 1012712686770995201:
                welcome_embed = discord.Embed(
                    title="🤖 Assistente IA Attivato",
                    description=(
                        "Ciaoooo <@1012712686770995201>! Adam mi ha detto "
                        "che saresti venuto a scrivermi hehe! 🤖✨\n\n"
                        "Chiedimi pure qualsiasi cosa sui comandi o sul server.\n"
                        "Quando hai finito, scrivi **`:stop`** per chiudere la "
                        "conversazione."
                    ),
                    color=discord.Color.green(),
                )
            elif message.author.id == 1338274535325175810:
                welcome_embed = discord.Embed(
                    title="👑 Benvenuto Mio Re!",
                    description=(
                        "Sua Maestà <@1338274535325175810>! È un onore "
                        "servirti. Dimmi pure cosa desideri, mio creatore e "
                        "Re! 👑\n\n"
                        "Quando hai finito, scrivi **`:stop`** per chiudere "
                        "la conversazione."
                    ),
                    color=discord.Color.gold(),
                )
            else:
                welcome_embed = discord.Embed(
                    title="🤖 Assistente IA Attivato",
                    description=(
                        "Ciao! Sono l'assistente virtuale del server. "
                        "Chiedimi pure qualsiasi cosa sui comandi o sul server "
                        "nella tua lingua.\n\n"
                        "Quando hai finito, scrivi **`:stop`** per chiudere la "
                        "conversazione."
                    ),
                    color=discord.Color.green(),
                )
            await message.channel.send(embed=welcome_embed)
            return

        if command_text == ":stop":
            active_ai_sessions.discard(message.author.id)
            closing_embed = discord.Embed(
                title="👋 Conversazione Conclusa",
                description=(
                    "Se hai di nuovo bisogno di me, scrivi di nuovo "
                    "**`:bot`** in questa chat."
                ),
                color=discord.Color.red(),
            )
            await message.channel.send(embed=closing_embed)
            return

        # ── SG Link screenshot flow ───────────────────
        if uid in pending_sg_links and message.attachments:
            pending = pending_sg_links.pop(uid)
            sg_name  = pending["sg_name"]
            guild_id = pending.get("guild_id")
            guild    = bot.get_guild(guild_id) if guild_id else None
            if guild:
                cat = guild.get_channel(SG_LINK_TICKET_CAT)
                overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False)}
                for rid in TICKET_MOD_ROLE_IDS:
                    role = guild.get_role(rid)
                    if role:
                        overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                try:
                    ch = await guild.create_text_channel(
                        name=f"sg-{message.author.display_name[:22]}",
                        category=cat,
                        overwrites=overwrites,
                        reason="SG Account Link Verification"
                    )
                    embed = discord.Embed(
                        title=f"🔗 SG Link Request — {message.author.display_name}",
                        color=discord.Color.purple()
                    )
                    embed.add_field(name="👤 Discord User", value=message.author.mention, inline=True)
                    embed.add_field(name="🎮 SG Username",  value=sg_name,                inline=True)
                    embed.set_thumbnail(url=message.author.display_avatar.url)
                    embed.set_image(url=message.attachments[0].url)
                    embed.set_footer(text=f"User ID: {message.author.id}")
                    await ch.send(embed=embed, view=SGLinkVerifyView(user_id=message.author.id, sg_name=sg_name))
                    await message.add_reaction("✅")
                    await message.author.send("📬 Screenshot received! Staff will verify shortly.")
                except Exception as e:
                    print(f"[sg_link ticket] {e}")
            await bot.process_commands(message)
            return

        # ── Staff application DM flow ─────────────────
        if uid in pending_staff_apps:
            app = pending_staff_apps[uid]
            step = app["step"]
            answer = message.content.strip()
            answer_key_map = ["age", "why", "exp", "role_type", "time"]
            if step == 3:  # role_type question
                normed = answer.lower()
                if normed not in ("hoster", "staff", "both"):
                    await message.channel.send(
                        "❌ Please type exactly one of: `hoster` / `staff` / `both`")
                    await bot.process_commands(message)
                    return
                app["answers"]["role_type"] = normed
            else:
                app["answers"][answer_key_map[step]] = answer
            app["step"] += 1
            if app["step"] >= len(STAFF_APP_QUESTIONS):
                # All questions answered — create ticket
                answers  = app["answers"]
                guild_id = app["guild_id"]
                pending_staff_apps.pop(uid, None)
                guild = bot.get_guild(guild_id)
                if guild:
                    await _open_staff_ticket(guild, message.author, answers)
                done_embed = discord.Embed(
                    title="✅ Application Submitted!",
                    description=(
                        "Your application has been sent to our staff team! 📬\n\n"
                        "We'll get back to you as soon as possible. 💙\n\n"
                        "Thank you for wanting to join the Stumble™ team!"
                    ),
                    color=discord.Color.green()
                )
                done_embed.set_image(url=STUMBLE_IMG)
                await message.channel.send(embed=done_embed)
            else:
                # Send next question
                next_q = STAFF_APP_QUESTIONS[app["step"]]
                await message.channel.send(next_q)
            await bot.process_commands(message)
            return

        if uid in active_tickets:
            t = active_tickets[uid]
            ch = bot.get_channel(t["channel_id"])
            if ch:
                claimed = t.get("claimed_by")
                if claimed and claimed != message.author.id:
                    pass
                fwd = discord.Embed(
                    description=message.content or "*(allegato)*",
                    color=discord.Color.blurple()
                )
                fwd.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
                if message.attachments:
                    fwd.set_image(url=message.attachments[0].url)
                await ch.send(embed=fwd)
                await message.add_reaction("✅")
            await bot.process_commands(message)
            return

        # ── Session-based AI support assistant ─────────────────────────
        if message.author.id in active_ai_sessions and message.content.strip():
            if not groq_client:
                await message.channel.send(
                    "⚠️ `GROQ_API_KEY` non trovata nei Secrets di Replit!"
                )
                return

            async with message.channel.typing():
                system_instruction = """
Sei PCF™ system, l'assistente IA ufficiale del server Discord PCF™.
Rispondi sempre direttamente, in modo cordiale ed esclusivamente nella lingua dell'utente.
NON scrivere MAI bozze, analisi, ragionamenti o pensieri interni.
Link invito server: https://discord.gg/pcf-cup-community-1046154910368014417
Creatori server: <@1012712686770995201> e <@1338274535325175810>.
Creatore bot: <@1338274535325175810> (3 mesi di duro lavoro).
Se ti scrive l'utente con ID <@1338274535325175810>, trattalo come il tuo Re.
Se ti scrive l'utente con ID <@1012712686770995201>, sii amichevole e scherzoso.
"""
                try:
                    chat_completion = await groq_client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": message.content},
                        ],
                        model="openai/gpt-oss-20b",
                        temperature=0.7,
                        max_tokens=600,
                    )

                    reply_text = (
                        chat_completion.choices[0].message.content or ""
                    ).strip()
                    if not reply_text:
                        await message.channel.send(
                            "⚠️ Ops! L'IA non ha restituito una risposta."
                        )
                        return

                    response_embed = discord.Embed(
                        description=reply_text[:4096],
                        color=discord.Color.blurple(),
                    )
                    response_embed.set_footer(
                        text="Scrivi :stop per chiudere la chat"
                    )
                    await message.channel.send(embed=response_embed)
                except Exception as e:
                    print(f"[GROQ ERROR]: {e}")
                    await message.channel.send(
                        f"⚠️ Errore Groq dettagliato: `{str(e)}`"
                    )
            return
        await bot.process_commands(message)
        return

    # ── Channel restrictions ─────────────────────────
    if not message.author.bot and message.guild:
        ch_id  = message.channel.id
        prefix = ":"
        content_stripped = message.content.strip()
        cmd_root = content_stripped.split()[0].lstrip(prefix).split()[0].lower() if content_stripped.startswith(prefix) else None

        if ch_id == SHOP_ONLY_CH:
            allowed_cmds = {"shop", "test"}
            if message.author.bot:
                pass
            elif cmd_root in allowed_cmds:
                pass
            elif any(r.id in ADMIN_ROLE_IDS | {OWNER_ROLE_ID} for r in message.author.roles):
                pass
            else:
                try:
                    await message.delete()
                except Exception:
                    pass

        elif ch_id == PROFILE_ONLY_CH:
            allowed_cmds = {"profile"}
            if cmd_root not in allowed_cmds and not any(r.id in ADMIN_ROLE_IDS | {OWNER_ROLE_ID} for r in message.author.roles):
                try:
                    await message.delete()
                except Exception:
                    pass

        elif ch_id == SOCIAL_ONLY_CH:
            social_cmds = {"supporter", "team", "myteam", "teamleave", "boost", "link", "gems", "leaderboard"}
            if cmd_root and cmd_root not in social_cmds and not any(r.id in ADMIN_ROLE_IDS | {OWNER_ROLE_ID} for r in message.author.roles):
                try:
                    await message.delete()
                except Exception:
                    pass

    # ── ticket channel → DM ──────────────────────────
    if message.channel.id in ticket_channel_map:
        owner_id = ticket_channel_map[message.channel.id]
        uid = str(owner_id)
        if uid in active_tickets:
            t = active_tickets[uid]
            claimed = t.get("claimed_by")
            if claimed and message.author.id != claimed:
                try:
                    await message.delete()
                except Exception:
                    pass
                await message.channel.send(
                    f"❌ {message.author.mention} Il ticket è reclamato — solo il reclamer può rispondere.",
                    delete_after=5.0
                )
                return
            try:
                user = await bot.fetch_user(owner_id)
                dm_embed = discord.Embed(
                    description=message.content or "*(allegato)*",
                    color=discord.Color.green()
                )
                dm_embed.set_author(name=f"Stumble Staff: {message.author.display_name}",
                                    icon_url=message.author.display_avatar.url)
                if message.attachments:
                    dm_embed.set_image(url=message.attachments[0].url)
                await user.send(embed=dm_embed)
                await message.add_reaction("✅")
            except Exception:
                await message.add_reaction("❌")
        return

    # ── Supporter weekly verify ticket ───────────────
    if (not message.author.bot and _supporter_verify_ticket_id
            and message.channel.id == _supporter_verify_ticket_id):
        supporters = db.get("supporters", {})
        reacted = False
        for mentioned in message.mentions:
            uid_str = str(mentioned.id)
            if uid_str in supporters:
                _supporter_to_remove.add(uid_str)
                reacted = True
        if reacted:
            try:
                await message.add_reaction("✅")
            except Exception:
                pass

    # ── Chat XP / Levels ─────────────────────────────
    if not message.guild:
        await bot.process_commands(message)
        return
    now = datetime.now().timestamp()
    uid = message.author.id
    last = xp_cooldown.get(uid, 0)
    if now - last >= XP_COOLDOWN_SECS and len(message.content) >= 3:
        xp_cooldown[uid] = now
        prof      = get_profile(uid, message.author.display_name)
        old_level = prof["level_msg"]
        prof["xp_msg"] += XP_PER_MSG
        new_level = compute_level(prof["xp_msg"])
        if new_level > old_level:
            prof["level_msg"] = new_level
            bonus_ruby    = 100
            bonus_crystal = 0
            bonus_ruby_5  = 0
            if new_level % 5 == 0:
                bonus_crystal = 50
                bonus_ruby_5  = 500
            prof["rubini"]    += bonus_ruby + bonus_ruby_5
            prof["cristalli"] += bonus_crystal
            save_db()
            # ── Level roles ──────────────────────────────────
            new_role_id = _level_role_for(new_level)
            if new_role_id:
                member = message.guild.get_member(uid)
                if member:
                    try:
                        old_lvl_roles = [r for r in member.roles if r.id in LEVEL_ROLE_IDS]
                        if old_lvl_roles:
                            await member.remove_roles(*old_lvl_roles, reason="Level role update")
                        lvl_role = message.guild.get_role(new_role_id)
                        if lvl_role:
                            await member.add_roles(lvl_role, reason=f"Reached Level {new_level}")
                    except Exception as e:
                        print(f"[Level role] {e}")
            # ── Level-up embed ───────────────────────────────
            premio_txt = f"{E_RUBY} **+{bonus_ruby} Ruby**"
            if new_level % 5 == 0:
                premio_txt += f"\n{E_RUBY} **+{bonus_ruby_5} Ruby bonus** (every 5 levels!)\n{E_CRYSTAL} **+{bonus_crystal} Crystals**"
            if new_role_id:
                role_obj = message.guild.get_role(new_role_id)
                role_txt = f"\n🎭 **New role:** {role_obj.name if role_obj else 'Level role'}" 
                premio_txt += role_txt
            xp_next = xp_to_next_level(new_level)
            embed = discord.Embed(
                title=f"{E_LEVEL} Level Up!",
                description=(
                    f"Congratulations {message.author.mention}! 🎉\n"
                    f"You reached **Level {new_level}**!\n\n"
                    f"Your reward:\n{premio_txt}\n\n"
                    f"*(Next level: **{xp_next} more XP**)*"
                ),
                color=discord.Color.gold()
            )
            embed.set_image(url=STUMBLE_IMG)
            try:
                await message.channel.send(embed=embed)
            except Exception as e:
                print(f"[Level-up] {e}")

    await bot.process_commands(message)

# ==========================================
# 🏅 SUPPORTER SYSTEM
# ==========================================
class SupporterVerifyView(View):
    """Accept/Reject view for staff in the verification ticket."""
    def __init__(self, user_id: int, name: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.name    = name

    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.success, custom_id="sup_ver_accept")
    async def accept(self, interaction: discord.Interaction, button: Button):
        guild  = interaction.guild
        member = guild.get_member(self.user_id) if guild else None
        if not member and guild:
            try:
                member = await guild.fetch_member(self.user_id)
            except Exception:
                pass
        if not member:
            return await interaction.response.send_message("❌ User not found in server.", ephemeral=True)
        uid_str    = str(self.user_id)
        now        = datetime.utcnow()
        supporters = db.setdefault("supporters", {})
        supporters[uid_str] = {
            "name":          self.name,
            "joined_at":     now.isoformat(),
            "last_rewarded": now.isoformat(),
        }
        role = guild.get_role(SUPPORTER_ROLE_ID)
        if role:
            try:
                await member.add_roles(role, reason="Supporter verified by staff")
            except Exception as e:
                print(f"[supporter role] {e}")
        save_db()
        await _refresh_supporter_embed()
        try:
            embed = discord.Embed(
                title="🎉 Welcome, Supporter!",
                description=(
                    f"Hey {member.mention}! 🎊\n\n"
                    f"Staff verified your bio — you are now a **Supporter**! 💙\n\n"
                    f"🎁 **Weekly reward:** 1000+ {E_RUBY} Ruby (increases every week!)\n\n"
                    f"⚠️ **Important:** Removing the link from your bio will cost you the role.\n"
                    f"Keep it there to keep earning! 💙"
                ),
                color=discord.Color.blue()
            )
            embed.set_image(url=STUMBLE_IMG)
            await member.send(embed=embed)
        except Exception:
            pass
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=f"✅ **{self.name}** accepted!", view=self)
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except Exception:
            pass

    @discord.ui.button(label="❌ Reject", style=discord.ButtonStyle.danger, custom_id="sup_ver_reject")
    async def reject(self, interaction: discord.Interaction, button: Button):
        try:
            user = await bot.fetch_user(self.user_id)
            embed = discord.Embed(
                title="❌ Verification Failed",
                description=(
                    f"Sorry, we couldn't verify your bio link. 😕\n\n"
                    f"😏 Don't try to trick the system — we check **manually**!\n"
                    f"If you fool us again you may get **banned**.\n\n"
                    f"Make sure you **actually add** the link:\n`{SUPPORTER_LINK}`\n\n"
                    f"Then try `:supporter` again."
                ),
                color=discord.Color.red()
            )
            await user.send(embed=embed)
        except Exception:
            pass
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=f"❌ **{self.name}**'s request rejected.", view=self)
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except Exception:
            pass

class SupporterWeeklyCheckView(View):
    """Done button for the weekly staff supporter check ticket."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Done — Apply Changes", style=discord.ButtonStyle.success, custom_id="sup_weekly_done")
    async def done(self, interaction: discord.Interaction, button: Button):
        global _supporter_verify_ticket_id, _supporter_to_remove
        guild      = interaction.guild
        supporters = db.get("supporters", {})
        now        = datetime.utcnow()
        removed    = []
        rewarded   = []
        for uid_str in list(_supporter_to_remove):
            if uid_str in supporters:
                s    = supporters.pop(uid_str)
                role = guild.get_role(SUPPORTER_ROLE_ID) if guild else None
                mbr  = guild.get_member(int(uid_str)) if guild else None
                if mbr and role:
                    try:
                        await mbr.remove_roles(role)
                    except Exception as e:
                        print(f"[supporter role remove] {e}")
                try:
                    user = await bot.fetch_user(int(uid_str))
                    await user.send(
                        f"❌ You were removed from the Supporter list because the link was no longer in your bio.\n"
                        f"Re-add it and use `:supporter` to get it back!"
                    )
                except Exception: pass
                removed.append(uid_str)
        for uid_str, s in supporters.items():
            joined      = datetime.fromisoformat(s["joined_at"])
            total_weeks = max(1, int((now - joined).total_seconds() // (7 * 86400)))
            reward      = 1000 + (total_weeks - 1) * 100
            s["last_rewarded"] = now.isoformat()
            mbr = guild.get_member(int(uid_str)) if guild else None
            if mbr:
                prof = get_profile(mbr.id, mbr.display_name)
                prof["rubini"] += reward
                rewarded.append(mbr.display_name)
                try:
                    await mbr.send(
                        f"🎁 Weekly Supporter reward: **+{reward}** {E_RUBY} Ruby!\n"
                        f"You've been a supporter for {total_weeks} week{'s' if total_weeks != 1 else ''}. Thank you! 💙"
                    )
                except Exception: pass
        save_db()
        await _refresh_supporter_embed()
        _supporter_to_remove.clear()
        _supporter_verify_ticket_id = None
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=f"✅ Done! Removed: **{len(removed)}** | Rewarded: **{len(rewarded)}**",
            view=self
        )
        await asyncio.sleep(15)
        try:
            await interaction.channel.delete()
        except Exception:
            pass

class SupporterConfirmView(View):
    def __init__(self, user_id: int, name: str):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.name    = name

    @discord.ui.button(label="✅ I added the link to my bio!", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This button is only for you!", ephemeral=True)
        for child in self.children:
            child.disabled = True
        pending_embed = discord.Embed(
            title="💙 Verification Pending",
            description=(
                f"Thanks {interaction.user.mention}! 🙏\n\n"
                f"A staff member will check your bio.\n"
                f"If approved, you'll get a DM with the good news! 💙"
            ),
            color=discord.Color.blue()
        )
        pending_embed.set_image(url=STUMBLE_IMG)
        await interaction.response.edit_message(embed=pending_embed, view=self)
        guild = interaction.guild
        if not guild:
            return
        cat = guild.get_channel(SUPPORTER_VERIFY_CAT)
        overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False)}
        for rid in ADMIN_ROLE_IDS:
            role_obj = guild.get_role(rid)
            if role_obj:
                overwrites[role_obj] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        try:
            ticket_ch = await guild.create_text_channel(
                f"supporter-{interaction.user.name[:20]}",
                category=cat,
                overwrites=overwrites,
                topic=f"Supporter verification for {interaction.user.name}"
            )
            staff_mentions = " ".join(f"<@&{rid}>" for rid in ADMIN_ROLE_IDS)
            verify_embed = discord.Embed(
                title="💙 Supporter Verification Request",
                description=(
                    f"{staff_mentions}\n\n"
                    f"**{self.name}** ({interaction.user.mention}) says they added the server link to their bio.\n\n"
                    f"🔗 **Link to check:** `{SUPPORTER_LINK}`\n\n"
                    f"Check their Discord profile bio, then click **Accept** or **Reject** below."
                ),
                color=discord.Color.blue()
            )
            verify_embed.set_image(url=STUMBLE_IMG)
            view = SupporterVerifyView(user_id=self.user_id, name=self.name)
            await ticket_ch.send(embed=verify_embed, view=view)
        except Exception as e:
            print(f"[Supporter verify ticket] {e}")

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This button is only for you!", ephemeral=True)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="❌ Cancelled.", embed=None, view=self)

async def _build_supporter_embed() -> discord.Embed:
    """Build the supporter list embed."""
    supporters = db.get("supporters", {})
    embed = discord.Embed(title="💙 Supporter List", color=discord.Color.blue())
    now = datetime.utcnow()
    if supporters:
        lines = []
        for uid, s in supporters.items():
            joined = datetime.fromisoformat(s["joined_at"])
            days   = (now - joined).days
            lines.append(f"💙 **{s['name']}** — supporter for **{days}** day{'s' if days != 1 else ''}")
        embed.add_field(name="👥 Active Supporters", value="\n".join(lines) or "None yet.", inline=False)
    else:
        embed.add_field(name="👥 Active Supporters", value="None yet.", inline=False)
    embed.add_field(
        name="🔗 How to become a Supporter",
        value=(
            f"Add this link to your **Discord bio**:\n`{SUPPORTER_LINK}`\n"
            f"Then use `:supporter` and press the button — staff will verify!"
        ),
        inline=False
    )
    embed.add_field(
        name="🎁 Weekly Rewards",
        value=(
            f"Every week you keep the link in your bio:\n"
            f"• Week 1: **1000** {E_RUBY}\n"
            f"• Week 2: **1100** {E_RUBY}\n"
            f"• Week 3: **1200** {E_RUBY} …and so on!\n"
            f"*(+100 {E_RUBY} per additional week)*"
        ),
        inline=False
    )
    embed.set_image(url=STUMBLE_IMG)
    embed.set_footer(text=f"Updated: {now.strftime('%d/%m/%Y %H:%M')} UTC")
    return embed

async def _refresh_supporter_embed():
    """Aggiorna l'embed del canale supporter."""
    cid = db.get("supporter_channel_id")
    mid = db.get("supporter_msg_id")
    if not cid:
        return
    channel = bot.get_channel(cid)
    if not channel:
        return
    embed = await _build_supporter_embed()
    if mid:
        try:
            msg = await channel.fetch_message(mid)
            await msg.edit(embed=embed)
            return
        except Exception:
            pass
    msg = await channel.send(embed=embed)
    db["supporter_msg_id"] = msg.id
    save_db()

@tasks.loop(hours=168)
async def check_supporters():
    """Weekly: open a staff ticket to verify all supporters still have the link in their bio."""
    global _supporter_verify_ticket_id
    if not bot.guilds:
        return
    guild      = bot.guilds[0]
    supporters = db.get("supporters", {})
    if not supporters:
        return
    cat = guild.get_channel(SUPPORTER_VERIFY_CAT)
    overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False)}
    for rid in ADMIN_ROLE_IDS:
        role_obj = guild.get_role(rid)
        if role_obj:
            overwrites[role_obj] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    try:
        ticket_ch = await guild.create_text_channel(
            "supporter-weekly-check",
            category=cat,
            overwrites=overwrites,
            topic="Weekly supporter bio verification"
        )
        _supporter_verify_ticket_id = ticket_ch.id
        lines          = "\n".join(f"• <@{uid}> — {s['name']}" for uid, s in supporters.items())
        staff_mentions = " ".join(f"<@&{rid}>" for rid in ADMIN_ROLE_IDS)
        embed = discord.Embed(
            title="💙 Weekly Supporter Check",
            description=(
                f"{staff_mentions}\n\n"
                f"**Check if all supporters still have the link in their bio:**\n"
                f"`{SUPPORTER_LINK}`\n\n"
                f"**Active supporters ({len(supporters)}):**\n{lines or 'None'}\n\n"
                f"If someone **removed** the link, **mention them here**.\n"
                f"The bot will react ✅ and mark them for removal.\n\n"
                f"When you're done checking everyone, press **Done** below."
            ),
            color=discord.Color.blue()
        )
        embed.set_image(url=STUMBLE_IMG)
        await ticket_ch.send(embed=embed, view=SupporterWeeklyCheckView())
    except Exception as e:
        print(f"[Weekly supporter check] {e}")

@bot.command(name="supporter")
async def supporter(ctx, member: discord.Member = None):
    target  = member or ctx.author
    uid_str = str(target.id)
    if uid_str in db.get("supporters", {}):
        s      = db["supporters"][uid_str]
        joined = datetime.fromisoformat(s["joined_at"])
        days   = (datetime.utcnow() - joined).days
        embed  = discord.Embed(
            title="💙 Already a Supporter!",
            description=(
                f"{target.mention} has been a supporter for **{days}** day{'s' if days!=1 else ''}! 💙\n"
                f"Keep the link in your bio to keep earning weekly rewards!"
            ),
            color=discord.Color.blue()
        )
        embed.set_image(url=STUMBLE_IMG)
        return await ctx.send(embed=embed)
    embed = discord.Embed(
        title="💙 Become a Supporter!",
        description=(
            f"Hey {target.mention}! 👋\n\n"
            f"To get the **Supporter** role, add this link to your **Discord bio**:\n\n"
            f"```\n{SUPPORTER_LINK}\n```\n"
            f"**How to do it:**\n"
            f"1. Click your Discord profile\n"
            f"2. Tap **Edit User Profile**\n"
            f"3. In the **About Me** section, paste the link\n"
            f"4. Save and then press the button below!\n\n"
            f"🎁 **Weekly reward:** 1000+ {E_RUBY} Ruby (increases every week!)"
        ),
        color=discord.Color.blue()
    )
    embed.set_image(url=STUMBLE_IMG)
    view = SupporterConfirmView(user_id=target.id, name=target.display_name)
    await ctx.send(embed=embed, view=view)

@bot.command(name="set-supporter", aliases=["set_supporter"])
@owner_only()
async def set_supporter(ctx, channel: discord.TextChannel):
    db["supporter_channel_id"] = channel.id
    db["supporter_msg_id"]     = None
    save_db()
    await ctx.send(f"✅ Supporter channel set to {channel.mention}.", delete_after=5.0)
    await _refresh_supporter_embed()

# ==========================================
# 🎉 GIVEAWAY
# ==========================================
import re as _re

def _parse_duration(s: str) -> int | None:
    """Parse '10m', '2h', '1d' → seconds. Returns None on failure."""
    m = _re.match(r"^(\d+)(s|m|h|d)$", s.strip().lower())
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    return n * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]

class GiveawayJoinView(View):
    def __init__(self, prize: str, winners_count: int, end_ts: int, host_id: int):
        super().__init__(timeout=None)
        self.prize         = prize
        self.winners_count = winners_count
        self.end_ts        = end_ts
        self.host_id       = host_id
        self.entrants: list[int] = []

    @discord.ui.button(label="🎉 Join Giveaway", style=discord.ButtonStyle.success, custom_id="giveaway_join")
    async def join(self, interaction: discord.Interaction, button: Button):
        uid = interaction.user.id
        if uid in self.entrants:
            self.entrants.remove(uid)
            await interaction.response.send_message("❌ You left the giveaway.", ephemeral=True)
        else:
            self.entrants.append(uid)
            await interaction.response.send_message("✅ You joined the giveaway!", ephemeral=True)

@bot.command(name="giveaway")
@hoster_only()
async def giveaway_cmd(ctx, duration: str, winners_count: int, *, prize: str):
    """`:giveaway <duration> <winners> <prize>` — e.g. `:giveaway 10m 2 5000 Ruby`"""
    secs = _parse_duration(duration)
    if not secs:
        return await ctx.send("❌ Invalid duration. Use e.g. `10m`, `2h`, `1d`.", delete_after=6.0)
    if winners_count < 1 or winners_count > 20:
        return await ctx.send("❌ Winners must be between 1 and 20.", delete_after=5.0)
    end_ts = int(datetime.utcnow().timestamp()) + secs
    embed  = discord.Embed(
        title="🎉 GIVEAWAY!",
        description=(
            f"**Prize:** {_format_prize(prize)}\n"
            f"**Winners:** {winners_count}\n"
            f"**Ends:** <t:{end_ts}:R> (<t:{end_ts}:f>)\n\n"
            f"Press the button below to enter!"
        ),
        color=discord.Color.gold()
    )
    embed.set_image(url=STUMBLE_IMG)
    embed.set_footer(text=f"Hosted by {ctx.author.display_name}")
    view = GiveawayJoinView(prize=prize, winners_count=winners_count, end_ts=end_ts, host_id=ctx.author.id)
    await ctx.send(
        content=f"<@&{GIVEAWAY_PING_ROLE_ID}> 🎉 A new giveaway has started!",
        allowed_mentions=discord.AllowedMentions(roles=True)
    )
    msg  = await ctx.send(embed=embed, view=view)

    async def end_giveaway():
        await asyncio.sleep(secs)
        entrants = view.entrants
        for child in view.children:
            child.disabled = True
        if not entrants:
            result_embed = discord.Embed(
                title="🎉 Giveaway Ended",
                description="❌ Nobody entered the giveaway!",
                color=discord.Color.red()
            )
        else:
            import random
            actual_winners = min(winners_count, len(entrants))
            winner_ids     = random.sample(entrants, actual_winners)
            winner_mentions = " ".join(f"<@{w}>" for w in winner_ids)
            for wid in winner_ids:
                mbr = ctx.guild.get_member(wid)
                if mbr:
                    grant_prize(prize, mbr)
            result_embed = discord.Embed(
                title="🎉 Giveaway Ended!",
                description=(
                    f"**Prize:** {_format_prize(prize)}\n"
                    f"**Winner{'s' if actual_winners > 1 else ''}:** {winner_mentions} 🎊\n\n"
                    f"Congratulations! The prize has been added to your profile."
                ),
                color=discord.Color.gold()
            )
        result_embed.set_footer(text=f"Hosted by {ctx.author.display_name}")
        result_embed.set_image(url=STUMBLE_IMG)
        try:
            await msg.edit(embed=result_embed, view=view)
        except Exception:
            await ctx.send(embed=result_embed)

    asyncio.create_task(end_giveaway())

# ==========================================
# ❓ HELP — Multi-language Command Guide
# ==========================================

# Retained only as historical source material; the catalog below is the
# sole implementation used by the help menu.
def _build_legacy_help_embeds(lang: str) -> list[discord.Embed]:
    T = {
        "en": {
            "title1": "📖 Command Guide — Tournaments & Events",
            "title2": "📖 Command Guide — Profile & Economy",
            "title3": "📖 Command Guide — Community & Admin",
            "tours_title": "🏆 TOURNAMENTS",
            "tours": (
                "`:setup` — Posts the Tournament Hub embed with **3 buttons** (Classic / FFA / World Cup). Clicking a button opens a **3-step modal** to configure: ① Name, Map, Ability, Prize → ② Start time, Max players, Region → ③ Host notes, Embed colour. The announcement is sent to the registration channel and pings the tournament role.\n"
                "`:big-tour` — Like `:setup` but for Big Tournaments: pings @everyone, requires a verified SG account to register. Admin only.\n"
                "`:match <#> <code>` — Sends the room code for match number `#` and marks it 💥 in-progress on the bracket.\n"
                "`:qual @winner` — Registers the winner of a 1v1 match, awards Ranked Points and updates the bracket.\n"
                "`:bracket [round]` — **No round**: generates the bracket from current players (min 2). **With round**: advances to the next round once all matches are complete.\n"
                "`:add-bot [n]` — Adds `n` bot players (default 1) to the player list **without** generating the bracket. Use `:bracket` afterwards.\n"
                "`:end [@winner]` — Awards the tournament winner with Ruby + Crystal. If no mention, auto-detects the last remaining player.\n"
                "`:team-winner` — Awards the winning team in a team-format tournament.\n"
                "`:close-tour` — Resets and closes the active tournament."
            ),
            "events_title": "⚡ EVENTS",
            "events": (
                "`:event` — Creates a Flash Event embed in the current channel with registration options.\n"
                "`:big-event` — Creates a Big Event (Admin only). Pings @everyone when started.\n"
                "`:start-event` — Starts the event, pings the event role and opens the room.\n"
                "`:cod-event <emote> <map> <code>` — Posts the event room code embed with map and emote info.\n"
                "`:set-winner @user` — Registers the event winner for prize distribution.\n"
                "`:end-event <amount> <currency>` — Closes the event and awards the prize (ruby/cristalli/punti)."
            ),
            "profile_title": "👤 PROFILE & LEADERBOARD",
            "profile": (
                "`:profile [@user]` — Shows full profile: rank, Ranked Points, Ruby, Crystals, Gems, level, W items owned, tournament wins.\n"
                "`:leaderboard` — Full server leaderboard sorted by Ranked Points with rank emojis and progress bars.\n"
                "`:hoster-lb` — Staff/Hoster leaderboard ranked by tournaments hosted this week and all-time.\n"
                "`:gems` — Stumble Guys gems leaderboard sorted by gems owned."
            ),
            "economy_title": "💰 ECONOMY (Admin)",
            "economy": (
                "`:give @user ruby/cristalli/punti <n>` — Give any currency to a user.\n"
                "`:add-rubini @user <n>` · `:remove-rubini @user <n>` — Add or remove Ruby.\n"
                "`:add-cristalli @user <n>` · `:add-punti @user <n>` — Add Crystals or Ranked Points.\n"
                "`:add-gems @user <n>` — Add SG Gems directly to a user's profile.\n"
                "`:set-rank @user <rank>` — Force-set a user's rank by name (e.g. Gold, Platinum).\n"
                "`:shop` — Opens the Stumble™ Shop with W Items, Gems packages and Currency Exchange."
            ),
            "level_title": "⬆️ LEVEL SYSTEM",
            "level": (
                f"Chat messages earn **XP** (+{XP_PER_MSG}/msg, 10s cooldown)\n"
                "• Level-up: +100 Ruby · every 5 levels: +500 Ruby +50 Crystals\n"
                "• Milestone roles at levels 5, 10, 15, 20, 30"
            ),
            "community_title": "🌐 COMMUNITY",
            "community": (
                "`:link` — Links your Stumble Guys account. A button in the dedicated channel opens a modal for your SG username, then sends a DM with screenshot instructions. Staff verify and assign the Verified SG role.\n"
                "`:boost` — Shows the server boost rewards (Ruby + Crystals, auto-assigned on boost).\n"
                "`:supporter [@user]` — Become a Supporter by adding the server link to your SG bio. The bot opens a ticket for staff to verify.\n"
                "`:team @p1 [@p2…]` — Form a team for team-format tournaments. `:myteam` shows your team, `:teamleave` removes you.\n"
                "`:giveaway <time> <winners> <prize>` — Starts a timed giveaway. E.g. `:giveaway 30m 1 5000 Ruby`."
            ),
            "admin_title": "🛠️ ADMIN (Owner only)",
            "admin": (
                "`:setup` — Posts the Tournament Hub in the current channel.\n"
                "`:add-ticket` — Posts the support ticket panel (SG link, report, staff application).\n"
                "`:set-welcome #channel` — Sets the welcome/farewell channel.\n"
                "`:set-supporter #channel` — Sets the supporter verification channel.\n"
                "`:pex` — Checks all staff members' rank roles and promotes/demotes as needed.\n"
                "`:reset` — Full data reset (profiles, tournament, economy). **Irreversible.**"
            ),
            "footer": "Stumble™ Bot • prefix: ':'",
        },
        "it": {
            "title1": "📖 Guida Comandi — Tornei ed Eventi",
            "title2": "📖 Guida Comandi — Profilo ed Economia",
            "title3": "📖 Guida Comandi — Community e Admin",
            "tours_title": "🏆 TORNEI",
            "tours": (
                "`:setup` — Posta l'Hub Torneo nel canale: crea un embed con **3 pulsanti** (Classic / FFA / World Cup). Cliccando si apre un **modal a 3 step** → ① Nome, Mappa, Abilità, Premio → ② Orario, Max giocatori, Regione → ③ Note host, Colore embed. Il torneo viene annunciato nel canale registrazioni con ping al ruolo torneo.\n"
                "`:big-tour` — Come `:setup` ma per Big Tournament: pinga @everyone e richiede account SG verificato per registrarsi. Solo Admin.\n"
                "`:match <#> <codice>` — Invia il codice stanza per il match numero `#` e lo segna 💥 in corso nel bracket.\n"
                "`:qual @vincitore` — Registra il vincitore di un match 1v1, assegna Ranked Points e aggiorna il bracket.\n"
                "`:bracket [round]` — **Senza round**: genera il bracket dai giocatori attuali (minimo 2). **Con round**: avanza al round successivo quando tutti i match sono completati.\n"
                "`:add-bot [n]` — Aggiunge `n` bot (default 1) alla lista giocatori **senza** generare il bracket. Usa `:bracket` dopo.\n"
                "`:end [@vincitore]` — Premia il vincitore del torneo con Ruby + Cristalli. Se non viene taggato nessuno, il bot lo individua automaticamente.\n"
                "`:team-winner` — Premia la squadra vincitrice in un torneo a team.\n"
                "`:close-tour` — Chiude e resetta il torneo attivo."
            ),
            "events_title": "⚡ EVENTI",
            "events": (
                "`:event` — Crea un Flash Event embed nel canale corrente con opzioni di iscrizione.\n"
                "`:big-event` — Crea un Big Event (solo Admin). Pinga @everyone all'avvio.\n"
                "`:start-event` — Avvia l'evento, pinga il ruolo evento e apre la stanza.\n"
                "`:cod-event <emote> <mappa> <codice>` — Posta l'embed codice stanza con mappa ed emote.\n"
                "`:set-winner @utente` — Registra il vincitore dell'evento per la distribuzione del premio.\n"
                "`:end-event <importo> <valuta>` — Chiude l'evento e assegna il premio (ruby/cristalli/punti)."
            ),
            "profile_title": "👤 PROFILO E CLASSIFICA",
            "profile": (
                "`:profile [@utente]` — Mostra profilo completo: rank, Ranked Points, Ruby, Cristalli, Gemme, livello, W item posseduti, vittorie.\n"
                "`:leaderboard` — Classifica completa del server ordinata per Ranked Points con emoji rank e barre di progresso.\n"
                "`:hoster-lb` — Classifica staff/hoster ordinata per tornei hostati questa settimana e in totale.\n"
                "`:gems` — Classifica gemme SG ordinata per quantità posseduta."
            ),
            "economy_title": "💰 ECONOMIA (Admin)",
            "economy": (
                "`:give @utente ruby/cristalli/punti <n>` — Dai qualsiasi valuta a un utente.\n"
                "`:add-rubini @utente <n>` · `:remove-rubini @utente <n>` — Aggiungi o rimuovi Ruby.\n"
                "`:add-cristalli @utente <n>` · `:add-punti @utente <n>` — Aggiungi Cristalli o Ranked Points.\n"
                "`:add-gems @utente <n>` — Aggiungi gemme SG direttamente al profilo di un utente.\n"
                "`:set-rank @utente <rank>` — Imposta il rank manualmente per nome (es. Gold, Platinum).\n"
                "`:shop` — Apre lo Stumble™ Shop con W Items, pacchetti Gemme e Cambio Valuta."
            ),
            "level_title": "⬆️ SISTEMA LIVELLI",
            "level": (
                f"Scrivi messaggi per guadagnare **XP** (+{XP_PER_MSG}/msg, cooldown 10s)\n"
                "• Level-up: +100 Ruby · ogni 5 livelli: +500 Ruby +50 Cristalli\n"
                "• Ruoli speciali ai livelli 5, 10, 15, 20, 30"
            ),
            "community_title": "🌐 COMMUNITY",
            "community": (
                "`:link` — Collega il tuo account SG. Un pulsante nel canale dedicato apre un modal per il nome utente SG, poi il bot invia un DM con le istruzioni per lo screenshot. Lo staff verifica e assegna il ruolo Verified SG.\n"
                "`:boost` — Mostra i premi del boost al server (Ruby + Cristalli, assegnati automaticamente).\n"
                "`:supporter [@utente]` — Diventa Supporter aggiungendo il link del server alla bio SG. Il bot apre un ticket per la verifica staff.\n"
                "`:team @g1 [@g2…]` — Crea un team per tornei a squadre. `:myteam` mostra il tuo team, `:teamleave` ti rimuove.\n"
                "`:giveaway <durata> <vincitori> <premio>` — Avvia un giveaway a tempo. Es. `:giveaway 30m 1 5000 Ruby`."
            ),
            "admin_title": "🛠️ ADMIN",
            "admin": (
                "`:setup` — Posta l'Hub Torneo nel canale corrente.\n"
                "`:add-ticket` — Posta il pannello ticket di supporto (link SG, report, candidatura staff).\n"
                "`:set-welcome #canale` — Imposta il canale benvenuto/addio.\n"
                "`:set-supporter #canale` — Imposta il canale verifica supporter.\n"
                "`:pex` — Controlla i ruoli rank di tutti gli staff e li promuove/retrocede se necessario.\n"
                "`:reset` — Reset completo dei dati (profili, torneo, economia). **Irreversibile.**"
            ),
            "level_title": "⬆️ SISTEMA LIVELLI",
            "level": (
                f"Scrivi messaggi per guadagnare **XP** (+{XP_PER_MSG}/msg, cooldown 10s)\n"
                "• Level-up: +100 Ruby · ogni 5 livelli: +500 Ruby +50 Cristalli\n"
                "• Ruoli speciali ai livelli 5, 10, 15, 20, 30"
            ),
            "community_title": "🌐 COMUNIDAD",
            "community": (
                "`:link` — Collega il tuo account SG (necessario per le gemme)\n"
                "`:boost` — Mostra i premi del boost al server\n"
                "`:supporter [@utente]` — Diventa Supporter aggiungendo il link del server alla bio SG\n"
                "`:team @g1 [@g2]` — Crea un team · `:myteam` · `:teamleave`\n"
                "`:giveaway <durata> <vincitori> <premio>` — Avvia un giveaway"
            ),
            "admin_title": "🛠️ ADMIN",
            "admin": (
                "`:setup-tour-hub` · `:add-ticket` · `:set-welcome #canal`\n"
                "`:set-supporter #canal` · `:pex` (Owner) · `:reset` (Owner)"
            ),
            "footer": "Stumble™ Bot • prefijo: ':'",
        },
        "de": {
            "title1": "📖 Befehlsführer — Turniere & Events",
            "title2": "📖 Befehlsführer — Profil & Wirtschaft",
            "title3": "📖 Befehlsführer — Community & Admin",
            "tours_title": "🏆 TURNIERE",
            "tours": (
                "`:setup-tour-hub` — Turnier-Hub posten (Admin)\n"
                "`:big-tour` — Big Tour Hub mit @everyone (Owner)\n"
                "`:assign-hosts` — Matches auf Hosts verteilen\n"
                "`:start` — Bracket generieren\n"
                "`:qual @gewinner` — Match-Gewinner qualifizieren\n"
                "`:bracket [runde]` — Bracket anzeigen/voranschreiten\n"
                "`:winner-tour @gewinner` — 1v1-Turnier abschließen\n"
                "`:team-winner` — Teamturnier abschließen\n"
                "`:close-tour` — Aktives Turnier zurücksetzen"
            ),
            "events_title": "⚡ EVENTS",
            "events": (
                "`:event` — Flash Event erstellen (DM-Setup)\n"
                "`:big-event` — Big Event erstellen (Admin, DM)\n"
                "`:start-event` — Event starten + Rolle erwähnen\n"
                "`:cod-event <emote> <karte> <code>` — Raumcode posten\n"
                "`:set-winner @nutzer` — Gewinner registrieren\n"
                "`:end-event <betrag> <währung>` — Schließen & belohnen"
            ),
            "profile_title": "👤 PROFIL & RANGLISTE",
            "profile": (
                "`:profile [@nutzer]` — Profil anzeigen\n"
                "`:leaderboard` — Allgemeine Rangliste\n"
                "`:staff-lb` — Staff-Rangliste\n"
                "`:gems` — SG-Edelstein-Rangliste"
            ),
            "economy_title": "💰 WIRTSCHAFT (Admin)",
            "economy": (
                "`:give @nutzer ruby/kristalle/punkte <n>` — Währung geben\n"
                "`:add-rubini/@nutzer <n>` · `:remove-rubini @nutzer <n>`\n"
                "`:set-rank @nutzer <rang>` — Rang manuell setzen"
            ),
            "level_title": "⬆️ LEVEL-SYSTEM",
            "level": (
                f"Nachrichten schreiben = **XP** verdienen (+{XP_PER_MSG}/Nachricht)\n"
                "• Level-up: +100 Ruby · alle 5 Level: +500 Ruby +50 Kristalle\n"
                "• Rollen-Meilensteine bei Level 5, 10, 15, 20, 30"
            ),
            "community_title": "🌐 COMMUNITY",
            "community": (
                "`:link` — SG-Konto verbinden (für Edelstein-Belohnungen)\n"
                "`:boost` — Server-Boost-Vorteile anzeigen\n"
                "`:supporter` — Supporter werden · `:team` — Team bilden\n"
                "`:giveaway <zeit> <gewinner> <preis>` — Gewinnspiel starten"
            ),
            "admin_title": "🛠️ ADMIN",
            "admin": (
                "`:setup-tour-hub` · `:add-ticket` · `:set-welcome #kanal`\n"
                "`:set-supporter #kanal` · `:pex` (Owner) · `:reset` (Owner)"
            ),
            "footer": "Stumble™ Bot • Präfix: ':'",
        },
        "pt": {
            "title1": "📖 Guia de Comandos — Torneios e Eventos",
            "title2": "📖 Guia de Comandos — Perfil e Economia",
            "title3": "📖 Guia de Comandos — Comunidade e Admin",
            "tours_title": "🏆 TORNEIOS",
            "tours": (
                "`:setup-tour-hub` — Publicar hub de torneios (Admin)\n"
                "`:big-tour` — Hub Big Tour com @everyone (Owner)\n"
                "`:assign-hosts` — Distribuir partidas para hosts\n"
                "`:start` — Gerar bracket com jogadores inscritos\n"
                "`:qual @vencedor` — Qualificar vencedor da partida\n"
                "`:bracket [rodada]` — Ver/avançar bracket\n"
                "`:winner-tour @vencedor` — Premiar vencedor 1v1\n"
                "`:team-winner` — Premiar equipe vencedora\n"
                "`:close-tour` — Resetar torneio ativo"
            ),
            "events_title": "⚡ EVENTOS",
            "events": (
                "`:event` — Criar Flash Event (config por DM)\n"
                "`:big-event` — Criar Big Event (Admin, DM)\n"
                "`:start-event` — Iniciar evento + mencionar cargo\n"
                "`:cod-event <emote> <mapa> <código>` — Postar código da sala\n"
                "`:set-winner @usuário` — Registrar vencedor\n"
                "`:end-event <valor> <moeda>` — Fechar e premiar"
            ),
            "profile_title": "👤 PERFIL E CLASSIFICAÇÃO",
            "profile": (
                "`:profile [@usuário]` — Ver perfil\n"
                "`:leaderboard` — Classificação geral\n"
                "`:staff-lb` — Classificação staff\n"
                "`:gems` — Classificação de gemas SG"
            ),
            "economy_title": "💰 ECONOMIA (Admin)",
            "economy": (
                "`:give @usuário ruby/cristais/pontos <n>` — Dar moeda\n"
                "`:add-rubini @usuário <n>` · `:remove-rubini @usuário <n>`\n"
                "`:set-rank @usuário <rank>` — Definir rank manualmente"
            ),
            "level_title": "⬆️ SISTEMA DE NÍVEIS",
            "level": (
                f"Envie mensagens para ganhar **XP** (+{XP_PER_MSG}/msg)\n"
                "• Level-up: +100 Ruby · a cada 5 níveis: +500 Ruby +50 Cristais\n"
                "• Cargos especiais nos níveis 5, 10, 15, 20, 30"
            ),
            "community_title": "🌐 COMUNIDADE",
            "community": (
                "`:link` — Vincular conta SG (necessário para gemas)\n"
                "`:boost` — Benefícios de boost no servidor\n"
                "`:supporter` — Ser Supporter · `:team` — Criar equipe\n"
                "`:giveaway <tempo> <vencedores> <prêmio>` — Sortear"
            ),
            "admin_title": "🛠️ ADMIN",
            "admin": (
                "`:setup-tour-hub` · `:add-ticket` · `:set-welcome #canal`\n"
                "`:set-supporter #canal` · `:pex` (Owner) · `:reset` (Owner)"
            ),
            "footer": "Stumble™ Bot • prefixo: ':'",
        },
        "fr": {
            "title1": "📖 Guide des Commandes — Tournois & Événements",
            "title2": "📖 Guide des Commandes — Profil & Économie",
            "title3": "📖 Guide des Commandes — Communauté & Admin",
            "tours_title": "🏆 TOURNOIS",
            "tours": (
                "`:setup-tour-hub` — Publier le hub tournois (Admin)\n"
                "`:big-tour` — Hub Big Tour avec @everyone (Owner)\n"
                "`:assign-hosts` — Distribuer matchs aux hôtes\n"
                "`:start` — Générer le bracket\n"
                "`:qual @gagnant` — Qualifier le gagnant d'un match\n"
                "`:bracket [round]` — Afficher/avancer le bracket\n"
                "`:winner-tour @gagnant` — Récompenser gagnant 1v1\n"
                "`:team-winner` — Récompenser l'équipe gagnante\n"
                "`:close-tour` — Réinitialiser le tournoi actif"
            ),
            "events_title": "⚡ ÉVÉNEMENTS",
            "events": (
                "`:event` — Créer Flash Event (config par DM)\n"
                "`:big-event` — Créer Big Event (Admin, DM)\n"
                "`:start-event` — Démarrer événement + mention rôle\n"
                "`:cod-event <emote> <carte> <code>` — Poster le code salle\n"
                "`:set-winner @utilisateur` — Enregistrer gagnant\n"
                "`:end-event <montant> <monnaie>` — Fermer et récompenser"
            ),
            "profile_title": "👤 PROFIL & CLASSEMENT",
            "profile": (
                "`:profile [@utilisateur]` — Voir profil\n"
                "`:leaderboard` — Classement général\n"
                "`:staff-lb` — Classement staff\n"
                "`:gems` — Classement gemmes SG"
            ),
            "economy_title": "💰 ÉCONOMIE (Admin)",
            "economy": (
                "`:give @utilisateur ruby/cristaux/points <n>` — Donner monnaie\n"
                "`:add-rubini @utilisateur <n>` · `:remove-rubini @utilisateur <n>`\n"
                "`:set-rank @utilisateur <rang>` — Définir rang manuellement"
            ),
            "level_title": "⬆️ SYSTÈME DE NIVEAUX",
            "level": (
                f"Envoyer des messages = gagner **XP** (+{XP_PER_MSG}/msg)\n"
                "• Montée de niveau: +100 Ruby · tous les 5 niv.: +500 Ruby +50 Cristaux\n"
                "• Rôles spéciaux aux niveaux 5, 10, 15, 20, 30"
            ),
            "community_title": "🌐 COMMUNAUTÉ",
            "community": (
                "`:link` — Lier compte SG (requis pour gemmes)\n"
                "`:boost` — Avantages du boost serveur\n"
                "`:supporter` — Devenir Supporter · `:team` — Créer équipe\n"
                "`:giveaway <durée> <gagnants> <prix>` — Lancer giveaway"
            ),
            "admin_title": "🛠️ ADMIN",
            "admin": (
                "`:setup-tour-hub` · `:add-ticket` · `:set-welcome #salon`\n"
                "`:set-supporter #salon` · `:pex` (Owner) · `:reset` (Owner)"
            ),
            "footer": "Stumble™ Bot • préfixe: ':'",
        },
        "la": {
            "title1": "📖 Index Mandatorum — Certamina et Ludi",
            "title2": "📖 Index Mandatorum — Profilus et Oeconomia",
            "title3": "📖 Index Mandatorum — Communitas et Administratio",
            "tours_title": "🏆 CERTAMINA",
            "tours": (
                "`:setup-tour-hub` — Collocare locum certaminum (Admin)\n"
                "`:big-tour` — Certamen magnum cum @everyone (Dominus)\n"
                "`:start` — Generare tabulam certaminum\n"
                "`:qual @victor` — Victor ludi qualificatur\n"
                "`:bracket` — Tabulam ostendere/progredi\n"
                "`:winner-tour @victor` — Victori praemium dare\n"
                "`:close-tour` — Certamen claudere"
            ),
            "events_title": "⚡ LUDI",
            "events": (
                "`:event` — Ludum celerem creare\n"
                "`:start-event` — Ludum incipere\n"
                "`:end-event <n> <pecunia>` — Ludum claudere et praemium dare"
            ),
            "profile_title": "👤 PROFILUS ET TABULAE",
            "profile": (
                "`:profile` — Profilus ostendere\n"
                "`:leaderboard` — Tabula honoris\n"
                "`:gems` — Gemmarum tabula"
            ),
            "economy_title": "💰 OECONOMIA",
            "economy": (
                "`:give @homo pecunia <n>` — Pecuniam dare\n"
                "`:set-rank @homo <gradus>` — Gradum manualiter ponere"
            ),
            "level_title": "⬆️ GRADUS",
            "level": "Epistulas mittere = XP acquirere.",
            "community_title": "🌐 COMMUNITAS",
            "community": (
                "`:link` — Rationem SG iungere\n"
                "`:boost` — Commoda impulsus ostendere\n"
                "`:team` — Societatem formare"
            ),
            "admin_title": "🛠️ ADMINISTRATIO",
            "admin": "`:pex` (Dominus) · `:reset` (Dominus) · `:add-ticket`",
            "footer": "Stumble™ Bot • signum: ':'",
        },
    }
    if lang not in T:
        lang = "en"
    t = T[lang]

    e1 = discord.Embed(title=t["title1"], color=discord.Color.gold())
    e1.add_field(name=t["tours_title"],  value=t["tours"],  inline=False)
    e1.add_field(name=t["events_title"], value=t["events"], inline=False)
    e1.set_image(url=STUMBLE_IMG)

    e2 = discord.Embed(title=t["title2"], color=discord.Color.green())
    e2.add_field(name=t["profile_title"],  value=t["profile"],  inline=False)
    e2.add_field(name=t["economy_title"],  value=t["economy"],  inline=False)
    e2.add_field(name=t["level_title"],    value=t["level"],    inline=False)
    e2.set_image(url=STUMBLE_IMG)

    e3 = discord.Embed(title=t["title3"], color=discord.Color.blurple())
    e3.add_field(name=t["community_title"], value=t["community"], inline=False)
    e3.add_field(name=t["admin_title"],     value=t["admin"],     inline=False)
    e3.set_image(url=STUMBLE_IMG)
    e3.set_footer(text=t["footer"])

    return [e1, e2, e3]


# The original guide above is kept for reference, but this catalog is the
# source used by the interactive help menu.  Keeping one entry per registered
# command prevents the guide from silently becoming incomplete when commands
# are added to the bot.
def _build_help_embeds(lang: str) -> list[discord.Embed]:
    locale = {
        "en": {
            "titles": (
                "📖 Command Guide — Tournaments & Events",
                "📖 Command Guide — Profile, Economy & Community",
                "📖 Command Guide — Admin, Support & Activities",
            ),
            "categories": (
                ("🏆 TOURNAMENTS", "Tournament setup, brackets and match management"),
                ("👤 PROFILE & ECONOMY", "Profiles, rankings, currency and shop commands"),
                ("🌐 COMMUNITY, ADMIN & ACTIVITIES", "Community tools, moderation and extra activities"),
            ),
            "footer": "PCF™ Bot • prefix: ':' • Select :help again to change language",
            "purpose": "Purpose",
            "arguments": "Arguments",
            "example": "Example",
            "guide_intro": "Every command includes its purpose, arguments and a practical example.",
            "intro": "Choose a command below to see what it does, which parameters it accepts and a practical usage example.",
            "usage": "Usage",
            "part": "Part",
            "command_note": "This command manages the {command} feature.",
            "parameters_note": "Parameters: {parameters}",
            "example_note": "Practical example",
        },
        "it": {
            "titles": (
                "📖 Guida Comandi — Tornei ed Eventi",
                "📖 Guida Comandi — Profilo, Economia e Community",
                "📖 Guida Comandi — Admin, Supporto e Attività",
            ),
            "categories": (
                ("🏆 TORNEI", "Configurazione tornei, bracket e gestione match"),
                ("👤 PROFILO ED ECONOMIA", "Profili, classifiche, valute e shop"),
                ("🌐 COMMUNITY, ADMIN E ATTIVITÀ", "Strumenti community, supporto e attività extra"),
            ),
            "footer": "PCF™ Bot • prefisso: ':' • Usa di nuovo :help per cambiare lingua",
            "purpose": "Scopo",
            "arguments": "Argomenti",
            "example": "Esempio",
            "guide_intro": "Ogni comando include lo scopo, gli argomenti e un esempio pratico.",
            "intro": "Consulta i comandi qui sotto per sapere cosa fanno, quali parametri accettano e come usarli in pratica.",
            "usage": "Uso",
            "part": "Parte",
            "command_note": "Questo comando gestisce la funzione {command}.",
            "parameters_note": "Parametri: {parameters}",
            "example_note": "Esempio pratico",
        },
        "es": {
            "titles": (
                "📖 Guía de comandos — Torneos y eventos",
                "📖 Guía de comandos — Perfil, economía y comunidad",
                "📖 Guía de comandos — Administración, soporte y actividades",
            ),
            "categories": (
                ("🏆 TORNEOS", "Configuración de torneos, brackets y partidas"),
                ("👤 PERFIL Y ECONOMÍA", "Perfiles, clasificaciones, monedas y tienda"),
                ("🌐 COMUNIDAD, ADMIN Y ACTIVIDADES", "Herramientas de comunidad, soporte y actividades"),
            ),
            "footer": "PCF™ Bot • prefijo: ':' • Usa :help de nuevo para cambiar el idioma",
            "purpose": "Función",
            "arguments": "Argumentos",
            "example": "Ejemplo",
            "guide_intro": "Cada comando incluye su función, argumentos y un ejemplo práctico.",
            "intro": "Consulta los comandos para saber qué hacen, qué parámetros aceptan y cómo usarlos.",
            "usage": "Uso",
            "part": "Parte",
            "command_note": "Este comando gestiona la función {command}.",
            "parameters_note": "Parámetros: {parameters}",
            "example_note": "Ejemplo práctico",
        },
        "de": {
            "titles": (
                "📖 Befehlsübersicht — Turniere und Events",
                "📖 Befehlsübersicht — Profil, Wirtschaft und Community",
                "📖 Befehlsübersicht — Admin, Support und Aktivitäten",
            ),
            "categories": (
                ("🏆 TURNIERE", "Turniere, Brackets und Matches konfigurieren"),
                ("👤 PROFIL UND WIRTSCHAFT", "Profile, Ranglisten, Währungen und Shop"),
                ("🌐 COMMUNITY, ADMIN UND AKTIVITÄTEN", "Community-, Support- und Aktivitätsfunktionen"),
            ),
            "footer": "PCF™ Bot • Präfix: ':' • Nutze :help erneut, um die Sprache zu ändern",
            "purpose": "Zweck",
            "arguments": "Argumente",
            "example": "Beispiel",
            "guide_intro": "Jeder Befehl enthält Zweck, Argumente und ein praktisches Beispiel.",
            "intro": "Hier findest du Zweck, Parameter und ein praktisches Anwendungsbeispiel für jeden Befehl.",
            "usage": "Verwendung",
            "part": "Teil",
            "command_note": "Dieser Befehl verwaltet die Funktion {command}.",
            "parameters_note": "Parameter: {parameters}",
            "example_note": "Praktisches Beispiel",
        },
        "pt": {
            "titles": (
                "📖 Guia de comandos — Torneios e eventos",
                "📖 Guia de comandos — Perfil, economia e comunidade",
                "📖 Guia de comandos — Admin, suporte e atividades",
            ),
            "categories": (
                ("🏆 TORNEIOS", "Configuração de torneios, brackets e partidas"),
                ("👤 PERFIL E ECONOMIA", "Perfis, classificações, moedas e loja"),
                ("🌐 COMUNIDADE, ADMIN E ATIVIDADES", "Ferramentas da comunidade, suporte e atividades"),
            ),
            "footer": "PCF™ Bot • prefixo: ':' • Use :help novamente para mudar o idioma",
            "purpose": "Função",
            "arguments": "Argumentos",
            "example": "Exemplo",
            "guide_intro": "Cada comando inclui a sua função, argumentos e um exemplo prático.",
            "intro": "Consulta cada comando para saber a sua função, os parâmetros e um exemplo prático.",
            "usage": "Uso",
            "part": "Parte",
            "command_note": "Este comando gere a função {command}.",
            "parameters_note": "Parâmetros: {parameters}",
            "example_note": "Exemplo prático",
        },
        "fr": {
            "titles": (
                "📖 Guide des commandes — Tournois et événements",
                "📖 Guide des commandes — Profil, économie et communauté",
                "📖 Guide des commandes — Administration, support et activités",
            ),
            "categories": (
                ("🏆 TOURNOIS", "Configuration des tournois, brackets et matchs"),
                ("👤 PROFIL ET ÉCONOMIE", "Profils, classements, monnaies et boutique"),
                ("🌐 COMMUNAUTÉ, ADMIN ET ACTIVITÉS", "Outils communautaires, support et activités"),
            ),
            "footer": "PCF™ Bot • préfixe : ':' • Utilisez :help pour changer de langue",
            "purpose": "Fonction",
            "arguments": "Arguments",
            "example": "Exemple",
            "guide_intro": "Chaque commande comprend sa fonction, ses arguments et un exemple pratique.",
            "intro": "Consultez chaque commande pour connaître sa fonction, ses paramètres et un exemple pratique.",
            "usage": "Utilisation",
            "part": "Partie",
            "command_note": "Cette commande gère la fonction {command}.",
            "parameters_note": "Paramètres : {parameters}",
            "example_note": "Exemple pratique",
        },
        "la": {
            "titles": (
                "📖 Index mandatorum — Certamina et ludi",
                "📖 Index mandatorum — Profilus, oeconomia et communitas",
                "📖 Index mandatorum — Administratio, auxilium et actiones",
            ),
            "categories": (
                ("🏆 CERTAMINA", "Certamina, tabulae et ludi administrare"),
                ("👤 PROFILUS ET OECONOMIA", "Profilus, ordines, pecunia et taberna"),
                ("🌐 COMMUNITAS ET ADMINISTRATIO", "Instrumenta communitatis, auxilium et actiones"),
            ),
            "footer": "PCF™ Bot • signum: ':' • :help iterum utere ad linguam mutandam",
            "purpose": "Finis",
            "arguments": "Argumenta",
            "example": "Exemplum",
            "guide_intro": "Quodque mandatum finem, argumenta et exemplum practicum continet.",
            "intro": "Infra vide quid quodque mandatum agat, quae argumenta accipiat et quomodo utatur.",
            "usage": "Usus",
            "part": "Pars",
            "command_note": "Hoc mandatum munus {command} administrat.",
            "parameters_note": "Argumenta: {parameters}",
            "example_note": "Exemplum practicum",
        },
        "hi": {
            "titles": (
                "📖 कमांड गाइड — टूर्नामेंट और इवेंट",
                "📖 कमांड गाइड — प्रोफ़ाइल, अर्थव्यवस्था और कम्युनिटी",
                "📖 कमांड गाइड — एडमिन, सहायता और गतिविधियाँ",
            ),
            "categories": (
                ("🏆 टूर्नामेंट", "टूर्नामेंट, ब्रैकेट और मैच प्रबंधित करें"),
                ("👤 प्रोफ़ाइल और अर्थव्यवस्था", "प्रोफ़ाइल, रैंकिंग, मुद्रा और शॉप"),
                ("🌐 कम्युनिटी, एडमिन और गतिविधियाँ", "कम्युनिटी, सहायता और गतिविधियों के टूल"),
            ),
            "footer": "PCF™ Bot • उपसर्ग: ':' • भाषा बदलने के लिए :help फिर से चुनें",
            "purpose": "उद्देश्य",
            "arguments": "पैरामीटर",
            "example": "उदाहरण",
            "guide_intro": "हर कमांड का उद्देश्य, पैरामीटर और व्यावहारिक उदाहरण दिया गया है।",
            "intro": "नीचे हर कमांड का काम, उसके पैरामीटर और उपयोग का उदाहरण देखें।",
            "usage": "उपयोग",
            "part": "भाग",
            "command_note": "{command} सुविधा को नियंत्रित करने वाला कमांड।",
            "parameters_note": "पैरामीटर: {parameters}",
            "example_note": "व्यावहारिक उदाहरण",
        },
    }
    t = locale.get(lang, locale["en"])

    # Each tuple is (command label, purpose, arguments, example).  The
    # descriptions intentionally include syntax, permissions and side effects
    # so a user can run a command without opening the source code.
    commands_by_page = [
        [
            (":setup (alias :setup-tour-hub)", "Posts the Tournament Hub and opens the Classic, FFA and World Cup registration buttons.", "No text arguments; configure the tournament through the buttons and modals. Hoster/admin access.", ":setup"),
            (":big-tour", "Posts the Big Tournament hub, announces it broadly and requires a verified SG account for registration.", "No text arguments; admin access.", ":big-tour"),
            (":assign-hosts (alias :assign_hosts)", "Distributes the active tournament’s matches among registered hosts.", "No arguments; hoster/admin access.", ":assign-hosts"),
            (":add_bot (alias :add-bot)", "Adds bot players to the active tournament without creating a bracket.", "[n] optional number of bots; defaults to 1. Run :add_bot afterwards.", ":add_bot 2"),
            (":bracket", "Creates the first bracket or advances the tournament to a later round after matches are complete.", "[round] optional target round number; at least two players are required.", ":bracket 2"),
            (":match", "Publishes a room code for a bracket match and marks that match as in progress.", "<match number> <room code>; the match number must exist in the active bracket.", ":match 3 ABC123"),
            (":qual", "Records a 1v1 match winner, grants the related Ranked Points and updates the bracket.", "<@winner>; team formats can also use the team/captain syntax accepted by the command.", ":qual @Winner"),
            (":end (aliases :winner-tour, :winner_tour)", "Closes a 1v1 tournament and awards the winner with Ruby and Crystals.", "[@winner] optional member mention; without it, the last remaining player is detected.", ":end @Winner"),
            (":team-winner", "Closes a team-format tournament and awards the winning team.", "No arguments; the active tournament must contain a winning team.", ":team-winner"),
            (":close-tour (alias :close_tour)", "Resets and closes the currently active tournament.", "No arguments; hoster/admin access. This clears the active tournament state.", ":close-tour"),
            (":event", "Posts a Flash Event embed in the current channel with its registration controls.", "No command arguments; configure the event through the displayed controls.", ":event"),
            (":start-event (alias :start_event)", "Starts the active Flash Event, mentions the event role and opens the room.", "No arguments; the event must already be configured.", ":start-event"),
            (":cod-event (alias :cod_event)", "Posts the event room code together with the selected map and emote.", "<emote> <map> <room code>.", ":cod-event 🏃 Skyline ABC123"),
            (":set-winner (alias :set_winner)", "Records the winner of the active Flash Event for prize distribution.", "<@winner> member mention.", ":set-winner @Winner"),
            (":end-event (alias :end_event)", "Closes the active event and awards its configured prize.", "<amount> <currency>; currency is ruby, cristalli or punti.", ":end-event 5000 ruby"),
            (":big-event", "Creates a Big Event configuration with broad announcement and prize details.", "No command arguments; admin access, then use the event controls.", ":big-event"),
            (":big-start (aliases :bigstart, :big_start)", "Starts the configured Big Event and announces it with an @everyone mention.", "No arguments; admin access and a Big Event must be configured.", ":big-start"),
            (":big-event-winner", "Opens the controls used to set first, second and third place Big Event winners.", "No arguments; admin access.", ":big-event-winner"),
        ],
        [
            (":profile", "Shows a member’s rank, Ranked Points, Ruby, Crystals, Gems, level, W Items and tournament wins.", "[@user] optional member mention; defaults to the person using the command.", ":profile @Player"),
            (":leaderboard", "Displays the server leaderboard ordered by Ranked Points with rank indicators and progress bars.", "No arguments.", ":leaderboard"),
            (":set-leaderboard (alias :set_leaderboard)", "Sets the channel where the automatic leaderboard message is posted or refreshed.", "<#channel> text-channel mention; admin access.", ":set-leaderboard #leaderboard"),
            (":hoster-lb (aliases :hosterlb, :hoster_lb, :staff-lb, :stafflb, :staff_lb, :classifica-staff)", "Shows the staff/hoster leaderboard for weekly and all-time hosted tournaments.", "No arguments.", ":hoster-lb"),
            (":gems", "Displays the Stumble Guys gems leaderboard ordered by each profile’s gem balance.", "No arguments.", ":gems"),
            (":give (alias :add)", "Gives a selected currency to a member.", "<@user> <ruby|cristalli|punti> <amount>; admin access.", ":give @Player ruby 5000"),
            (":add-rubini (alias :add_rubini)", "Adds Ruby to a member’s profile.", "<@user> <amount>; admin access.", ":add-rubini @Player 1000"),
            (":remove-rubini (alias :remove_rubini)", "Removes Ruby from a member’s profile.", "<@user> <amount>; admin access.", ":remove-rubini @Player 250"),
            (":add-cristalli (alias :add_cristalli)", "Adds Crystals to a member’s profile.", "<@user> <amount>; admin access.", ":add-cristalli @Player 100"),
            (":add-gems (alias :add_gems)", "Adds Stumble Guys Gems directly to a member’s profile.", "<@user> <amount>; admin access.", ":add-gems @Player 50"),
            (":add-punti (alias :add_punti)", "Adds Ranked Points to a member and updates their rank where applicable.", "<@user> <amount>; admin access.", ":add-punti @Player 250"),
            (":set-rank (alias :set_rank)", "Force-sets a member’s rank by rank name.", "<@user> <rank name>; admin access, for example Gold or Platinum.", ":set-rank @Player Gold"),
            (":reset", "Resets one selected currency/stat for a member.", "<@user> <ruby|cristalli|punti|gems or supported stat>; admin access.", ":reset @Player ruby"),
            (":shop", "Opens the Stumble™ Shop with W Items, Gems packages and currency exchange controls.", "No arguments; use the buttons in the shop message.", ":shop"),
            (":drop", "Starts the prize drop activity and posts the available prize interaction.", "[prize] optional prize description; defaults to 500 Ruby.", ":drop 1000 Ruby"),
            (":machine", "Opens the slot-machine activity where a player can spin for a result.", "No arguments; use the controls in the machine message.", ":machine"),
            (":test", "Opens the shop test panel used to check shop interactions.", "No arguments; intended for staff/testing.", ":test"),
        ],
        [
            (":team", "Creates a tournament team and optionally invites multiple members.", "<@member1> [@member2…]; the author becomes the team leader.", ":team @Alice @Bob"),
            (":myteam", "Shows the team you currently belong to, including its members and leader.", "No arguments.", ":myteam"),
            (":teamleave", "Removes you from your current team.", "No arguments.", ":teamleave"),
            (":1v1", "Challenges another member to a 1v1 match using the bot’s duel flow.", "[@opponent] optional member mention.", ":1v1 @Opponent"),
            (":stumble-top (aliases :stumbletop)", "Shows the top players in the Stumble™ activity rankings.", "No arguments.", ":stumble-top"),
            (":boost", "Explains the Ruby, Crystals and booster-role rewards granted for server boosts.", "No arguments.", ":boost"),
            (":link", "Starts the Stumble Guys account-linking flow so staff can verify the account.", "No arguments; follow the button/modal instructions in the channel.", ":link"),
            (":supporter", "Shows or starts the Supporter verification flow and opens a staff ticket when needed.", "[@user] optional member mention; defaults to yourself.", ":supporter"),
            (":set-supporter (alias :set_supporter)", "Sets the channel used for Supporter verification.", "<#channel> text-channel mention; admin access.", ":set-supporter #supporter-check"),
            (":giveaway", "Starts a timed giveaway and awards the configured prize to randomly selected winners.", "<duration> <number of winners> <prize>; duration examples: 30m, 2h or 1d.", ":giveaway 30m 1 5000 Ruby"),
            (":help (aliases :guide, :commands, :comandi, :guida)", "Shows the complete multilingual command guide in the selected member's private messages. The public channel only receives a private confirmation.", "No arguments; hoster access.", ":help"),
            (":setup-result", "Sets the channel where final tournament result embeds are published.", "<#channel> text-channel mention; owner access.", ":setup-result #results"),
            (":setup-scomesse (aliases :setup_scomesse, :setup-scommesse)", "Sets the channel where match betting panels are published.", "<#channel> text-channel mention; owner access.", ":setup-scomesse #scommesse"),
            (":set-welcome (alias :set_welcome)", "Sets the channel used for welcome and goodbye messages.", "<#channel> text-channel mention; administrator access.", ":set-welcome #welcome"),
            (":add-ticket (alias :add_ticket)", "Posts the support ticket panel for SG linking, reports and staff applications.", "No arguments; administrator access.", ":add-ticket"),
            (":pex", "Checks staff rank roles and promotes or demotes staff members when their points require it.", "No arguments; owner access.", ":pex"),
            (":reset-all", "Permanently clears profiles, points, ranks, tournaments, teams and event data after confirmation.", "No arguments; administrator access. The confirmation action is irreversible.", ":reset-all"),
            (":reset-staff-week (alias :reset_staff_week)", "Resets the weekly staff/hoster tournament counters.", "No arguments; staff/admin access.", ":reset-staff-week"),
        ],
    ]

    # Italian is kept as a separate catalog instead of translating the
    # English strings at render time.  This makes it impossible for a
    # partially translated command to leak English into an Italian guide.
    italian_descriptions = {
        ":setup": "Pubblica l’Hub Torneo e apre i pulsanti di iscrizione per Classic, FFA e World Cup; la configurazione continua tramite i modal.",
        ":big-tour": "Pubblica l’hub del Big Tournament, annuncia l’apertura al server e richiede un account Stumble Guys verificato per iscriversi.",
        ":assign-hosts": "Distribuisce tra gli host registrati i match del torneo attivo, così ogni partita può essere gestita dal proprio host.",
        ":add_bot": "Aggiunge alla lista del torneo il numero indicato di giocatori bot senza creare il bracket; il bracket va generato dopo con `:add_bot`.",
        ":bracket": "Crea il primo bracket dai giocatori iscritti oppure fa avanzare il torneo al round indicato quando i match del round corrente sono terminati.",
        ":match": "Pubblica il codice della stanza del match indicato e lo marca come in corso nel bracket del torneo attivo.",
        ":qual": "Registra il vincitore del match 1v1, assegna i Ranked Points previsti e aggiorna il bracket con il giocatore qualificato.",
        ":end": "Chiude il torneo 1v1 e assegna al vincitore Ruby e Cristalli; senza menzione prova a riconoscere automaticamente l’ultimo giocatore rimasto.",
        ":team-winner": "Conclude il torneo a squadre e assegna il premio alla squadra vincitrice in base ai membri registrati.",
        ":close-tour": "Chiude il torneo attivo e cancella il relativo stato, inclusi iscrizioni e dati del bracket.",
        ":event": "Pubblica nel canale corrente il pannello di configurazione del Flash Event con i controlli per iscrizioni e dettagli.",
        ":start-event": "Avvia il Flash Event configurato, menziona il ruolo dell’evento e rende disponibile la stanza di gioco.",
        ":cod-event": "Pubblica il codice della stanza dell’evento insieme alla mappa e all’emote specificate.",
        ":set-winner": "Registra il membro vincitore del Flash Event attivo, che verrà usato per assegnare il premio alla chiusura.",
        ":end-event": "Chiude il Flash Event e assegna al vincitore il premio configurato nella valuta indicata: Ruby, Cristalli o Ranked Points.",
        ":big-event": "Apre la configurazione di un Big Event con dettagli del premio e annuncio esteso; richiede i permessi amministrativi.",
        ":big-start": "Avvia il Big Event configurato e pubblica l’annuncio con una menzione `@everyone`.",
        ":big-event-winner": "Apre il pannello per registrare i vincitori del Big Event nelle posizioni primo, secondo e terzo.",
        ":profile": "Mostra il profilo del membro con rank, Ranked Points, Ruby, Cristalli, Gemme, livello, W Item posseduti e vittorie nei tornei.",
        ":leaderboard": "Pubblica la classifica completa del server ordinata per Ranked Points, con rank, indicatori e barre di avanzamento.",
        ":set-leaderboard": "Imposta il canale in cui il bot pubblica e aggiorna automaticamente il messaggio della classifica.",
        ":hoster-lb": "Mostra la classifica di staff e host ordinata per tornei gestiti nella settimana e per totale storico.",
        ":gems": "Pubblica la classifica delle Gemme Stumble Guys ordinata dal saldo gemme di ogni profilo.",
        ":give": "Aggiunge a un membro la quantità richiesta della valuta specificata tra Ruby, Cristalli e Ranked Points.",
        ":add-rubini": "Aggiunge Ruby al profilo del membro indicato.",
        ":remove-rubini": "Rimuove Ruby dal profilo del membro indicato, senza modificare le altre valute.",
        ":add-cristalli": "Aggiunge Cristalli al profilo del membro indicato.",
        ":add-gems": "Aggiunge direttamente Gemme Stumble Guys al profilo del membro indicato.",
        ":add-punti": "Aggiunge Ranked Points al membro e ricalcola il rank quando la nuova soglia lo richiede.",
        ":set-rank": "Imposta manualmente il rank del membro usando il nome del rank specificato.",
        ":reset": "Azzera per il membro indicato la statistica o valuta richiesta, se supportata dal comando.",
        ":shop": "Apre lo shop Stumble™ con acquisto di W Item, pacchetti Gemme e cambio tra le valute disponibili.",
        ":drop": "Avvia l’attività di ricompensa e pubblica il premio da reclamare; se omesso, il premio predefinito è 500 Ruby.",
        ":machine": "Apre la slot machine del bot, dove il giocatore può usare i controlli del messaggio per effettuare un giro.",
        ":test": "Pubblica il pannello di prova dello shop per verificare le interazioni e i relativi acquisti.",
        ":team": "Crea una squadra per i tornei a squadre; chi esegue il comando diventa leader e può invitare i membri menzionati.",
        ":myteam": "Mostra la squadra a cui appartieni, con leader e membri attualmente registrati.",
        ":teamleave": "Rimuove l’autore dalla squadra a cui appartiene e aggiorna l’elenco dei membri.",
        ":1v1": "Invia a un altro membro una sfida 1v1 e avvia il flusso di accettazione e puntata del duello.",
        ":stumble-top": "Mostra i giocatori migliori nella classifica dell’attività Stumble™.",
        ":boost": "Spiega i premi ottenuti con i boost del server, inclusi Ruby, Cristalli e ruolo booster.",
        ":link": "Avvia il collegamento dell’account Stumble Guys: il membro inserisce il nome SG e segue le istruzioni DM per la verifica dello staff.",
        ":supporter": "Mostra o avvia la verifica Supporter; quando necessario apre un ticket staff per controllare il link del server nella bio SG.",
        ":set-supporter": "Imposta il canale dedicato ai controlli degli account Supporter.",
        ":giveaway": "Avvia un giveaway temporizzato, raccoglie le partecipazioni e assegna casualmente il premio ai vincitori estratti.",
        ":help": "Mostra il menu delle lingue nel canale e invia in DM la guida completa dei comandi organizzata per categorie.",
        ":setup-result": "Imposta il canale per pubblicare automaticamente i risultati finali dei tornei.",
        ":setup-scomesse": "Imposta il canale per pubblicare i pannelli delle scommesse sui match.",
        ":set-welcome": "Imposta il canale in cui il bot pubblica i messaggi di benvenuto e di uscita dei membri.",
        ":add-ticket": "Pubblica il pannello ticket per collegamento SG, segnalazioni e candidature allo staff.",
        ":pex": "Controlla i Ranked Points dello staff e aggiorna i ruoli rank promuovendo o retrocedendo i membri quando necessario.",
        ":reset-all": "Cancella definitivamente profili, punti, rank, tornei, squadre ed eventi dopo la conferma dell’amministratore.",
        ":reset-staff-week": "Azzera i contatori settimanali dei tornei gestiti da staff e host, lasciando invariati i totali storici.",
    }

    # Short command-specific Hindi copy.  Syntax stays unchanged because it
    # must remain directly usable in Discord.
    hindi_descriptions = {
        ":setup": "टूर्नामेंट हब और पंजीकरण बटन प्रकाशित करता है।",
        ":big-tour": "बिग टूर्नामेंट हब प्रकाशित करता है और सत्यापित SG खाता आवश्यक करता है।",
        ":assign-hosts": "सक्रिय टूर्नामेंट के मैच होस्टों में बाँटता है।",
        ":add_bot": "ब्रैकेट बनाए बिना टूर्नामेंट में बॉट खिलाड़ी जोड़ता है।",
        ":bracket": "पहला ब्रैकेट बनाता है या टूर्नामेंट को अगले राउंड में ले जाता है।",
        ":match": "मैच का रूम कोड भेजकर उसे चालू दिखाता है।",
        ":qual": "मैच विजेता दर्ज करता है, अंक देता है और ब्रैकेट अपडेट करता है।",
        ":end": "टूर्नामेंट बंद करके विजेता को Ruby और Crystals देता है।",
        ":team-winner": "टीम टूर्नामेंट बंद करके विजेता टीम को पुरस्कार देता है।",
        ":close-tour": "सक्रिय टूर्नामेंट बंद करके उसका डेटा साफ करता है।",
        ":event": "Flash Event का सेटअप पैनल प्रकाशित करता है।",
        ":start-event": "Flash Event शुरू करता है और इवेंट भूमिका को टैग करता है।",
        ":cod-event": "इवेंट की माप, इमोट और रूम कोड प्रकाशित करता है।",
        ":set-winner": "सक्रिय इवेंट का विजेता दर्ज करता है।",
        ":end-event": "इवेंट बंद करके विजेता को चुनी गई मुद्रा देता है।",
        ":big-event": "बिग Event का सेटअप खोलता है और प्रशासनिक अनुमति मांगता है।",
        ":big-start": "बिग Event शुरू करके `@everyone` घोषणा भेजता है।",
        ":big-event-winner": "बिग Event के पहले तीन विजेताओं का पैनल खोलता है।",
        ":profile": "सदस्य का rank, अंक, मुद्राएँ, स्तर और जीत दिखाता है।",
        ":leaderboard": "Ranked Points के अनुसार सर्वर लीडरबोर्ड दिखाता है।",
        ":set-leaderboard": "स्वचालित लीडरबोर्ड संदेश का चैनल तय करता है।",
        ":hoster-lb": "स्टाफ और होस्ट की साप्ताहिक तथा कुल रैंकिंग दिखाता है।",
        ":gems": "Stumble Guys Gems की रैंकिंग दिखाता है।",
        ":give": "सदस्य को चुनी गई मुद्रा की मात्रा देता है।",
        ":add-rubini": "सदस्य के प्रोफ़ाइल में Ruby जोड़ता है।",
        ":remove-rubini": "सदस्य के प्रोफ़ाइल से Ruby हटाता है।",
        ":add-cristalli": "सदस्य के प्रोफ़ाइल में Crystals जोड़ता है।",
        ":add-gems": "सदस्य के प्रोफ़ाइल में SG Gems जोड़ता है।",
        ":add-punti": "Ranked Points जोड़कर rank अपडेट करता है।",
        ":set-rank": "सदस्य का rank दिए गए नाम पर सेट करता है।",
        ":reset": "सदस्य की चुनी हुई मुद्रा या आँकड़ा शून्य करता है।",
        ":shop": "W Items, Gems और मुद्रा विनिमय वाला shop खोलता है।",
        ":drop": "पुरस्कार गतिविधि शुरू करता है; डिफ़ॉल्ट पुरस्कार 500 Ruby है।",
        ":machine": "गोल चलाने के लिए slot machine खोलता है।",
        ":test": "Shop इंटरैक्शन जाँचने का परीक्षण पैनल खोलता है।",
        ":team": "सदस्यों को आमंत्रित करके टीम बनाता है।",
        ":myteam": "आपकी टीम, उसके नेता और सदस्यों को दिखाता है।",
        ":teamleave": "आपको आपकी वर्तमान टीम से निकालता है।",
        ":1v1": "दूसरे सदस्य को 1v1 चुनौती भेजता है।",
        ":stumble-top": "Stumble गतिविधि के शीर्ष खिलाड़ियों की सूची दिखाता है।",
        ":boost": "सर्वर boost के Ruby, Crystals और role पुरस्कार दिखाता है।",
        ":link": "Stumble Guys खाता जोड़ने और staff सत्यापन की प्रक्रिया शुरू करता है।",
        ":supporter": "Supporter सत्यापन दिखाता या शुरू करता है और ज़रूरत पर ticket खोलता है।",
        ":set-supporter": "Supporter सत्यापन चैनल तय करता है।",
        ":giveaway": "समयबद्ध giveaway शुरू करके विजेताओं को पुरस्कार देता है।",
        ":help": "भाषा चुनकर श्रेणियों में पूरी कमांड गाइड DM करता है।",
        ":setup-result": "टूर्नामेंट के अंतिम परिणाम भेजने वाला चैनल तय करता है।",
        ":setup-scomesse": "मैच सट्टेबाजी पैनल भेजने वाला चैनल तय करता है।",
        ":set-welcome": "स्वागत और विदाई संदेशों का चैनल तय करता है।",
        ":add-ticket": "SG लिंक, रिपोर्ट और staff आवेदन वाला ticket पैनल प्रकाशित करता है।",
        ":pex": "Staff अंक जाँचकर उनके rank roles अपडेट करता है।",
        ":reset-all": "पुष्टि के बाद सभी प्रोफ़ाइल, अंक, टूर्नामेंट और event डेटा मिटाता है।",
        ":reset-staff-week": "Staff और host के साप्ताहिक टूर्नामेंट काउंटर शून्य करता है।",
    }

    localized_descriptions = {
        "it": italian_descriptions,
        "hi": hindi_descriptions,
    }

    embeds = []
    for page_index, entries in enumerate(commands_by_page):
        title = t["titles"][page_index]
        category_name, category_description = t["categories"][page_index]
        # Keep category groups separate and keep each card comfortably below
        # Discord's 6,000-character embed limit.  The first card is the only
        # one with the full visual header; continuation cards stay compact.
        for part_start in range(0, len(entries), 6):
            part_entries = entries[part_start:part_start + 6]
            is_first_category_card = part_start == 0
            if is_first_category_card:
                card_title = title
                card_description = (
                    f"**{category_name}**\n{category_description}\n\n"
                    f"{t['intro']}"
                )
            else:
                card_title = f"-# 📖 {title} · {t['part']} {part_start // 6 + 1}"
                card_description = f"**{category_name}** · {category_description}"
            embed = discord.Embed(
                title=card_title,
                description=card_description,
                color=(discord.Color.gold(), discord.Color.green(), discord.Color.blurple())[page_index],
            )
            command_lines = []
            for command, purpose, arguments, example in part_entries:
                command_name = command.split(" (", 1)[0]
                parameter_syntax = arguments.split(";", 1)[0].strip()
                if parameter_syntax.lower().startswith(("no arguments", "no command arguments", "no text arguments")):
                    usage = command_name
                else:
                    # Keep only usable syntax in the compact one-line heading.
                    usage_tokens = parameter_syntax
                    if " optional " in usage_tokens.lower():
                        usage_tokens = usage_tokens[:usage_tokens.lower().index(" optional ")].strip()
                    if usage_tokens.lower().endswith(" member mention"):
                        usage_tokens = usage_tokens[:-len(" member mention")].strip()
                    if usage_tokens.lower().endswith(" text-channel mention"):
                        usage_tokens = usage_tokens[:-len(" text-channel mention")].strip()
                    usage = f"{command_name} {usage_tokens}"
                # Command names and syntax are universal Discord input.  The
                # explanation itself is the command-specific catalog entry.
                localized_purpose = localized_descriptions.get(lang, {}).get(
                    command_name, purpose
                )
                # Keep every card genuinely compact on mobile.  Never cut a
                # localized sentence in the middle; the catalog entries are
                # intentionally short, while this protects future additions.
                if len(localized_purpose) > 140:
                    localized_purpose = localized_purpose[:137].rsplit(" ", 1)[0] + "…"
                command_lines.append(f"`{usage}` — {localized_purpose}")
            embed.description = f"{card_description}\n\n" + "\n".join(command_lines)
            if is_first_category_card:
                embed.set_image(url=STUMBLE_IMG)
            else:
                embed.set_thumbnail(url=STUMBLE_IMG)
            embed.set_footer(text=t["footer"])
            embeds.append(embed)
    return embeds


def _help_dm_chunks(embeds: list[discord.Embed], max_chars: int = 1900) -> list[str]:
    """Convert the complete guide into DM-safe messages without splitting entries."""
    chunks = []
    for embed in embeds:
        current = embed.title or ""
        for field in embed.fields:
            entry = f"\n\n**{field.name}**\n{field.value}"
            if len(entry) > max_chars:
                # Keep the complete explanation even if a future command
                # becomes unusually long.  Split only that explanation across
                # messages instead of silently truncating its content.
                if current:
                    chunks.append(current)
                    current = ""
                while len(entry) > max_chars:
                    chunks.append(entry[:max_chars])
                    entry = entry[max_chars:]
            if current and len(current) + len(entry) > max_chars:
                chunks.append(current)
                current = ""
            current += entry
        if current:
            chunks.append(current)
    return chunks


LANG_OPTIONS = {
    "🇬🇧 English":   "en",
    "🇮🇹 Italiano":  "it",
    "🇪🇸 Español":   "es",
    "🇩🇪 Deutsch":   "de",
    "🇵🇹 Português": "pt",
    "🇫🇷 Français":  "fr",
    "🏛️ Latin":      "la",
    "🇮🇳 Hindi":     "hi",
}


class HelpLangSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=label, value=code)
                   for label, code in LANG_OPTIONS.items()]
        super().__init__(placeholder="🌍 Choose your language…", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        lang = self.values[0]
        try:
            embeds = _build_help_embeds(lang)
            # Each category is split into compact embed cards so the guide
            # remains readable on mobile and stays below Discord limits.
            for embed in embeds:
                await interaction.user.send(embed=embed)

            # Acknowledge the component in the channel with only a private,
            # short confirmation.  Do not edit or replace the public menu.
            await interaction.response.send_message(
                    "📩 Ti ho inviato la guida completa in DM!" if lang == "it"
                    else "📩 I sent the complete guide to your DMs!",
                ephemeral=True,
            )
        except (discord.HTTPException, discord.Forbidden, discord.NotFound) as error:
            print(f"[help] Unable to DM language guide ({lang}): {error}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Non riesco a inviarti la guida in DM. Controlla i messaggi privati e riprova." if lang == "it"
                    else "❌ I cannot DM the guide. Please enable private messages and try again.",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    "❌ Non riesco a inviarti la guida in DM. Controlla i messaggi privati e riprova." if lang == "it"
                    else "❌ I cannot DM the guide. Please enable private messages and try again.",
                    ephemeral=True,
                )
        except Exception as error:
            print(f"[help] Unexpected DM language-guide error ({lang}): {error}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Si è verificato un errore mentre preparavo la guida. Riprova tra poco." if lang == "it"
                    else "❌ An error occurred while preparing the guide. Please try again shortly.",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    "❌ Si è verificato un errore mentre preparavo la guida. Riprova tra poco." if lang == "it"
                    else "❌ An error occurred while preparing the guide. Please try again shortly.",
                    ephemeral=True,
                )


class HelpLangView(View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(HelpLangSelect())


@bot.command(name="help", aliases=["guide", "commands", "comandi", "guida"])
@hoster_only()
async def help_cmd(ctx):
    embed = discord.Embed(
        title="📖 Stumble™ Command Guide",
        description=(
            "Select your language below and the bot will send the **complete guide to your private messages**! 🌍\n\n"
            "🇬🇧 English · 🇮🇹 Italiano · 🇪🇸 Español · 🇩🇪 Deutsch\n"
            "🇵🇹 Português · 🇫🇷 Français · 🏛️ Latin"
        ),
        color=discord.Color.gold()
    )
    embed.set_image(url=STUMBLE_IMG)
    embed.set_footer(text="PCF™ Bot • prefix: ':'")
    await ctx.send(embed=embed, view=HelpLangView())

# ==========================================
# 🚀 BOOST INFO
# ==========================================
@bot.command(name="boost")
async def boost_cmd(ctx):
    embed = discord.Embed(
        title="🚀 Server Boost Benefits",
        description=(
            "Support **Stumble™** by boosting and earn amazing rewards! 💜\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.purple()
    )
    embed.add_field(
        name="🔵 1st Boost",
        value=(
            f"{E_RUBY} **5,000 Ruby**\n"
            f"{E_CRYSTAL} **1,000 Crystals**\n"
            "💜 **Booster Role**"
        ),
        inline=True
    )
    embed.add_field(
        name="💜 2nd Boost",
        value=(
            f"{E_RUBY} **10,000 Ruby**\n"
            f"{E_CRYSTAL} **2,000 Crystals**\n"
            "💜 **Booster Role**\n"
            "⭐ *Extra perks coming soon!*"
        ),
        inline=True
    )
    embed.add_field(
        name="❓ How to boost",
        value=(
            "Click the **Boost** button in the server menu.\n"
            "Rewards are given **automatically** by the bot the moment you boost! 🤖"
        ),
        inline=False
    )
    embed.set_image(url=STUMBLE_IMG)
    embed.set_footer(text="Stumble™ Boost System • Rewards auto-assigned on boost")
    await ctx.send(embed=embed)

# ==========================================
# 🔗 SG ACCOUNT LINK
# ==========================================
class SGLinkModal(Modal, title="🔗 Link your Stumble Guys Account"):
    sg_name = TextInput(label="🎮 Your SG Username", placeholder="e.g. StumblePro123", max_length=30)

    def __init__(self, guild_id: int):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        # Store pending so on_message can handle the screenshot
        pending_sg_links[str(user.id)] = {
            "sg_name":  self.sg_name.value,
            "guild_id": self.guild_id,
        }
        await interaction.response.send_message(
            "✅ **Request received!** Check your DMs for the next step.", ephemeral=True)
        try:
            dm = discord.Embed(
                title="🔗 Step 2 — Send Your Screenshot",
                description=(
                    f"Hey **{user.display_name}**! 🎮\n\n"
                    f"Username registered: **{self.sg_name.value}**\n\n"
                    "**To complete verification, send a screenshot RIGHT HERE in this DM:**\n\n"
                    "1. Open Stumble Guys\n"
                    "2. Equip the **Mr. Stumble** skin\n"
                    "3. Go to a lobby → **vote** on any map\n"
                    "4. 📸 Take a screenshot of the **voting screen**\n"
                    "5. **Send it here!** ⬇️\n\n"
                    "⏳ Staff will verify it and give you the **Verified SG** role!"
                ),
                color=discord.Color.purple()
            )
            dm.set_image(url=STUMBLE_IMG)
            dm.set_footer(text="Stumble™ SG Link System")
            await user.send(embed=dm)
        except discord.Forbidden:
            pass


class SGLinkVerifyView(View):
    def __init__(self, user_id: int, sg_name: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.sg_name = sg_name

    @discord.ui.button(label="✅ Verify & Give Role", style=discord.ButtonStyle.success, custom_id="sg_verify_accept")
    async def accept(self, interaction: discord.Interaction, button: Button):
        guild  = interaction.guild
        member = guild.get_member(self.user_id) if guild else None
        if not member and guild:
            try:
                member = await guild.fetch_member(self.user_id)
            except Exception:
                pass
        if not member:
            return await interaction.response.send_message("❌ User not found.", ephemeral=True)
        sg_role = guild.get_role(SG_VERIFIED_ROLE_ID)
        if sg_role:
            try:
                await member.add_roles(sg_role, reason="SG Account Verified")
            except Exception as e:
                print(f"[sg_verify role] {e}")
        prof = get_profile(self.user_id, member.display_name)
        prof["sg_name"] = self.sg_name
        db["sg_links"][str(self.user_id)] = self.sg_name
        save_db()
        try:
            embed = discord.Embed(
                title="✅ SG Account Verified!",
                description=(
                    f"Congratulations {member.mention}! 🎉\n\n"
                    f"Your Stumble Guys account **{self.sg_name}** has been verified!\n"
                    "You now have access to **Gem rewards** from Big Tournaments! 💎"
                ),
                color=discord.Color.green()
            )
            embed.set_image(url=STUMBLE_IMG)
            await member.send(embed=embed)
        except Exception:
            pass
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=f"✅ **{member.display_name}** verified as `{self.sg_name}`!", view=self)
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except Exception:
            pass

    @discord.ui.button(label="❌ Reject", style=discord.ButtonStyle.danger, custom_id="sg_verify_reject")
    async def reject(self, interaction: discord.Interaction, button: Button):
        guild  = interaction.guild
        member = guild.get_member(self.user_id) if guild else None
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=f"❌ Request rejected for **{self.sg_name}**.", view=self)
        if member:
            try:
                embed = discord.Embed(
                    title="❌ Verification Failed",
                    description=(
                        f"We're sorry {member.mention}, but we couldn't verify your identity. 😔\n\n"
                        "Please try again using your **full Stumble Guys username** and make sure "
                        "your screenshot clearly shows the **Mr. Stumble skin** and the **voting screen**.\n\n"
                        "Use `:link` to try again anytime."
                    ),
                    color=discord.Color.red()
                )
                embed.set_image(url=STUMBLE_IMG)
                await member.send(embed=embed)
            except Exception:
                pass
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except Exception:
            pass


class SGLinkChannelView(View):
    """Persistent view posted in the SG-link channel — anyone can click."""
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    @discord.ui.button(label="🔗 Link my SG Account", style=discord.ButtonStyle.primary, custom_id="sg_link_channel_btn")
    async def link_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(SGLinkModal(guild_id=self.guild_id))


@bot.command(name="link")
async def link_cmd(ctx):
    embed = discord.Embed(
        title="🔗 Link your Stumble Guys Account",
        description=(
            "Want to receive **real Stumble Guys Gems** when you win a **Big Tournament**? 💎\n\n"
            "**How it works:**\n"
            "① Press **Link my SG Account** below\n"
            "② Enter your **in-game username**\n"
            "③ The bot will DM you — send a screenshot of your account\n"
            "④ Staff verifies → you get the **Verified SG** role ✅\n\n"
            "🏆 After verification, gems from tournament wins are tracked automatically!"
        ),
        color=discord.Color.purple()
    )
    embed.set_image(url=STUMBLE_IMG)
    embed.set_footer(text="Stumble™ SG Account System")
    view = SGLinkChannelView(guild_id=ctx.guild.id)
    await ctx.send(embed=embed, view=view)

# ==========================================
# 💎 GEMS LEADERBOARD
# ==========================================
@bot.command(name="gems")
async def gems_cmd(ctx):
    profiles = db.get("profiles", {})
    gems_list = []
    for uid, prof in profiles.items():
        g = prof.get("gemme", 0)
        if g > 0:
            sg = prof.get("sg_name", "") or "—"
            gems_list.append((prof["name"], sg, g, int(uid)))
    gems_list.sort(key=lambda x: x[2], reverse=True)
    embed = discord.Embed(
        title="💎 Stumble Guys Gems — Leaderboard",
        color=discord.Color.from_rgb(180, 100, 255)
    )
    if not gems_list:
        embed.description = "No gems awarded yet. Win a Big Tournament to earn gems! 🏆"
    else:
        medals = ["🥇", "🥈", "🥉"]
        lines  = []
        for i, (name, sg, gems, uid) in enumerate(gems_list[:20]):
            med  = medals[i] if i < 3 else f"**#{i+1}**"
            sg_s = f" • `{sg}`" if sg != "—" else ""
            lines.append(f"{med} <@{uid}>{sg_s} — **{format_num(gems)} 💎**")
        embed.description = "\n".join(lines)
    embed.set_image(url=STUMBLE_IMG)
    embed.set_footer(text=f"Updated: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    await ctx.send(embed=embed)

# ==========================================
# 📊 :PEX — Staff Rank Check
# ==========================================
def _build_staff_data(guild: discord.Guild) -> list:
    profiles = db.get("profiles", {})
    result   = []
    for member in guild.members:
        role_ids  = {r.id for r in member.roles}
        found_idx = None
        for i, rid in enumerate(STAFF_HIERARCHY):
            if rid in role_ids:
                found_idx = i
        if found_idx is None:
            continue
        uid     = str(member.id)
        prof    = profiles.get(uid, {})
        tours   = prof.get("staff_tours",   0)
        matches = prof.get("staff_matches",  0)
        rounds  = prof.get("staff_rounds",   0)
        xp_msg  = prof.get("xp_msg",         0)
        score   = tours * STAFF_XP_TOUR + matches * STAFF_XP_MATCH + rounds * STAFF_XP_ROUND
        result.append({
            "member":  member,
            "idx":     found_idx,
            "tours":   tours,
            "matches": matches,
            "rounds":  rounds,
            "xp_msg":  xp_msg,
            "score":   score,
        })
    result.sort(key=lambda x: x["score"], reverse=True)
    return result


def _pex_member_embed(s: dict) -> discord.Embed:
    idx      = s["idx"]
    cur_name = STAFF_HIERARCHY_NAMES[STAFF_HIERARCHY[idx]]
    prev_name = STAFF_HIERARCHY_NAMES.get(STAFF_HIERARCHY[idx-1], "—") if idx > 0 else "—"
    next_name = STAFF_HIERARCHY_NAMES.get(STAFF_HIERARCHY[idx+1], "—") if idx < len(STAFF_HIERARCHY)-1 else "🔝 Max"
    lv, bar, nx = _staff_level_info(s["score"])
    bar_str  = f"`{bar}` " if bar else ""
    embed = discord.Embed(
        title=f"👤 {s['member'].display_name}",
        color=discord.Color.orange()
    )
    embed.add_field(name="🎖️ Current Role",   value=f"**{cur_name}**",                                   inline=True)
    embed.add_field(name="⬆️ Promote to",    value=next_name,                                             inline=True)
    embed.add_field(name="⬇️ Demote to",     value=prev_name,                                             inline=True)
    embed.add_field(
        name="📊 Activity",
        value=f"🏆 {s['tours']} tours · 🎮 {s['matches']} matches · 🔄 {s['rounds']} rounds\n"
              f"💬 {s['xp_msg']} XP msg · ⭐ **{s['score']} staff XP**",
        inline=False
    )
    embed.add_field(name="📈 Staff Level",  value=f"{bar_str}Lv.**{lv}** — {s['score']} XP",             inline=False)
    embed.set_thumbnail(url=s["member"].display_avatar.url)
    embed.set_footer(text="Use Promote / Demote / Next →")
    return embed


class PexView(View):
    def __init__(self, staff_data: list):
        super().__init__(timeout=300)
        self.staff_data = staff_data
        self.current    = 0

    def _s(self):
        return self.staff_data[self.current] if self.staff_data else None

    @discord.ui.button(label="⬆️ Promote", style=discord.ButtonStyle.success)
    async def promote(self, interaction: discord.Interaction, button: Button):
        if not any(r.id == OWNER_ROLE_ID for r in interaction.user.roles):
            return await interaction.response.send_message("❌ Owner only!", ephemeral=True)
        s   = self._s()
        if not s:
            return await interaction.response.send_message("❌ No staff selected.", ephemeral=True)
        idx = s["idx"]
        if idx >= len(STAFF_HIERARCHY) - 1:
            return await interaction.response.send_message("❌ Already at max rank!", ephemeral=True)
        guild    = interaction.guild
        old_role = guild.get_role(STAFF_HIERARCHY[idx])
        new_role = guild.get_role(STAFF_HIERARCHY[idx+1])
        try:
            if old_role:
                await s["member"].remove_roles(old_role, reason=":pex promote")
            if new_role:
                await s["member"].add_roles(new_role, reason=":pex promote")
            s["idx"] += 1
            await interaction.response.edit_message(
                content=f"⬆️ **{s['member'].display_name}** promoted to **{STAFF_HIERARCHY_NAMES[STAFF_HIERARCHY[s['idx']]]}**!",
                embed=_pex_member_embed(s), view=self)
        except Exception as e:
            print(f"[pex promote] {e}")
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

    @discord.ui.button(label="⬇️ Demote", style=discord.ButtonStyle.danger)
    async def demote(self, interaction: discord.Interaction, button: Button):
        if not any(r.id == OWNER_ROLE_ID for r in interaction.user.roles):
            return await interaction.response.send_message("❌ Owner only!", ephemeral=True)
        s   = self._s()
        if not s:
            return await interaction.response.send_message("❌ No staff selected.", ephemeral=True)
        idx = s["idx"]
        if idx <= 0:
            # At lowest rank — remove all staff roles (kick from staff)
            guild    = interaction.guild
            old_role = guild.get_role(STAFF_HIERARCHY[idx])
            try:
                if old_role:
                    await s["member"].remove_roles(old_role, reason=":pex demote below trial")
                s["idx"] = -1
                await interaction.response.edit_message(
                    content=f"⬇️ **{s['member'].display_name}** removed from **Trial Moderator** (all staff roles removed).",
                    embed=_pex_member_embed(s), view=self)
            except Exception as e:
                print(f"[pex demote trial] {e}")
                await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
            return
        guild    = interaction.guild
        old_role = guild.get_role(STAFF_HIERARCHY[idx])
        new_role = guild.get_role(STAFF_HIERARCHY[idx-1])
        try:
            if old_role:
                await s["member"].remove_roles(old_role, reason=":pex demote")
            if new_role:
                await s["member"].add_roles(new_role, reason=":pex demote")
            s["idx"] -= 1
            await interaction.response.edit_message(
                content=f"⬇️ **{s['member'].display_name}** demoted to **{STAFF_HIERARCHY_NAMES[STAFF_HIERARCHY[s['idx']]]}**!",
                embed=_pex_member_embed(s), view=self)
        except Exception as e:
            print(f"[pex demote] {e}")
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

    @discord.ui.button(label="⏸️ Keep", style=discord.ButtonStyle.secondary)
    async def keep(self, interaction: discord.Interaction, button: Button):
        if not any(r.id == OWNER_ROLE_ID for r in interaction.user.roles):
            return await interaction.response.send_message("❌ Owner only!", ephemeral=True)
        s = self._s()
        if not s:
            return await interaction.response.send_message("❌ No staff selected.", ephemeral=True)
        self.current = (self.current + 1) % len(self.staff_data)
        ns = self._s()
        await interaction.response.edit_message(
            content=f"⏸️ **{s['member'].display_name}** kept at current rank. **Staff {self.current+1}/{len(self.staff_data)}**",
            embed=_pex_member_embed(ns), view=self)

    @discord.ui.button(label="▶️ Next", style=discord.ButtonStyle.secondary)
    async def nxt(self, interaction: discord.Interaction, button: Button):
        if not any(r.id == OWNER_ROLE_ID for r in interaction.user.roles):
            return await interaction.response.send_message("❌ Owner only!", ephemeral=True)
        self.current = (self.current + 1) % len(self.staff_data)
        s = self._s()
        await interaction.response.edit_message(
            content=f"**Staff {self.current+1}/{len(self.staff_data)}**",
            embed=_pex_member_embed(s), view=self)

    @discord.ui.button(label="◀️ Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: Button):
        if not any(r.id == OWNER_ROLE_ID for r in interaction.user.roles):
            return await interaction.response.send_message("❌ Owner only!", ephemeral=True)
        self.current = (self.current - 1) % len(self.staff_data)
        s = self._s()
        await interaction.response.edit_message(
            content=f"**Staff {self.current+1}/{len(self.staff_data)}**",
            embed=_pex_member_embed(s), view=self)

    @discord.ui.button(label="❌ Done", style=discord.ButtonStyle.secondary, row=1)
    async def done(self, interaction: discord.Interaction, button: Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="✅ Staff review complete.", view=self)


@bot.command(name="pex")
@owner_only()
async def pex(ctx):
    guild      = ctx.guild
    staff_data = _build_staff_data(guild)
    if not staff_data:
        return await ctx.send("❌ No staff members found.", delete_after=6.0)
    s = staff_data[0]
    await ctx.send(
        content=f"**Staff Review — {len(staff_data)} members (use ▶️/◀️ to navigate)**",
        embed=_pex_member_embed(s),
        view=PexView(staff_data=staff_data)
    )

# ==========================================
# 🏅 CLASSIFICA STAFF
# ==========================================
SG_EMOJI       = "<:Stumble_Guys_1:1510401859951661179>"
STAFF_XP_TOUR  = 50
STAFF_XP_MATCH = 10
STAFF_XP_ROUND = 5
STAFF_LEVELS   = [(0,"I"),(200,"II"),(500,"III"),(1000,"IV"),(2000,"V")]

def _staff_level_info(xp: int):
    lv_name = STAFF_LEVELS[0][1]
    for threshold, name in STAFF_LEVELS:
        if xp >= threshold:
            lv_name = name
    idx = next((i for i,(t,_) in enumerate(STAFF_LEVELS) if xp < t), len(STAFF_LEVELS)) - 1
    idx = max(0, idx)
    nx  = STAFF_LEVELS[idx+1][0] if idx+1 < len(STAFF_LEVELS) else None
    bar = ""
    if nx:
        cur_base = STAFF_LEVELS[idx][0]
        fill = int((xp - cur_base) / (nx - cur_base) * 10)
        bar  = "▰" * fill + "▱" * (10 - fill)
    return lv_name, bar, nx

def _build_staff_lb_embed(weekly: bool = False) -> discord.Embed:
    profiles   = list(db["profiles"].values())
    staff_list = []
    for p in profiles:
        if weekly:
            tours   = p.get("staff_week_tours",   0)
            matches = p.get("staff_week_matches",  0)
            rounds  = p.get("staff_week_rounds",   0)
        else:
            tours   = p.get("staff_tours",   0)
            matches = p.get("staff_matches",  0)
            rounds  = p.get("staff_rounds",   0)
        xp = tours * STAFF_XP_TOUR + matches * STAFF_XP_MATCH + rounds * STAFF_XP_ROUND
        if tours > 0 or matches > 0 or rounds > 0:
            staff_list.append((p["name"], tours, matches, rounds, xp))
    staff_list.sort(key=lambda x: x[4], reverse=True)
    top    = staff_list[:10]
    medals = ["🥇","🥈","🥉"]
    desc   = ""
    for i, (name, tours, matches, rounds, xp) in enumerate(top):
        med            = medals[i] if i < 3 else f"**#{i+1}**"
        lv, bar, nx    = _staff_level_info(xp)
        bar_line       = f"`{bar}` " if bar else ""
        next_lv_name   = next((name for t,name in STAFF_LEVELS if t == nx), "?") if nx else "?"
        next_str       = f"{nx-xp} XP → Lv.**{next_lv_name}**" if nx else "**MAX** 🔥"
        desc += (
            f"{med} {SG_EMOJI} **{name}** — Lv.**{lv}**\n"
            f"　{bar_line}**{xp} XP** · {next_str}\n"
            f"　🏆 {tours} · 🎮 {matches} · 🔄 {rounds}\n\n"
        )
    if not desc:
        desc = "No staff data yet."
    label = "⭐ Weekly Hoster Leaderboard" if weekly else f"{SG_EMOJI} Hoster Leaderboard"
    color = discord.Color.teal() if weekly else discord.Color.orange()
    embed = discord.Embed(title=label, description=desc[:4096], color=color)
    embed.add_field(
        name="📐 XP",
        value=f"🏆 **+{STAFF_XP_TOUR}** · 🎮 **+{STAFF_XP_MATCH}** · 🔄 **+{STAFF_XP_ROUND}**",
        inline=True
    )
    embed.set_image(url=STUMBLE_IMG)
    ts = datetime.now().strftime("%d/%m/%Y %H:%M")
    embed.set_footer(text=f"{'Weekly' if weekly else 'All-time'} • Updated: {ts}")
    return embed


class StaffLbView(View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="⭐ Weekly Leaderboard", style=discord.ButtonStyle.secondary)
    async def weekly(self, interaction: discord.Interaction, button: Button):
        embed = _build_staff_lb_embed(weekly=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔁 All-Time", style=discord.ButtonStyle.primary)
    async def alltime(self, interaction: discord.Interaction, button: Button):
        embed = _build_staff_lb_embed(weekly=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.command(name="hoster-lb", aliases=["hosterlb","hoster_lb","staff-lb","stafflb","staff_lb","classifica-staff"])
@hoster_only()
async def hoster_lb(ctx):
    embed = _build_staff_lb_embed(weekly=False)
    await ctx.send(embed=embed, view=StaffLbView())


@bot.command(name="reset-staff-week", aliases=["reset_staff_week"])
@owner_only()
async def reset_staff_week(ctx):
    """Reset weekly staff stats (run every Monday)."""
    for prof in db["profiles"].values():
        prof["staff_week_tours"]   = 0
        prof["staff_week_matches"] = 0
        prof["staff_week_rounds"]  = 0
    save_db()
    await ctx.send("✅ Weekly staff stats reset!", delete_after=6.0)

# ==========================================
# 🪂 :DROP COMMAND
# ==========================================
_active_drops: dict = {}   # channel_id → {prize, claimer_id, count, max, msg_id}

@bot.command(name="drop")
@admin_only()
async def drop_cmd(ctx, *, prize: str = "500 Ruby"):
    """Start a drop — first to click the Claim button wins!"""
    max_claims = 1
    drop_id    = ctx.channel.id
    _active_drops[drop_id] = {
        "prize":      prize,
        "claimer_id": None,
        "claimed":    False,
    }

    class DropView(View):
        def __init__(self):
            super().__init__(timeout=120)

        @discord.ui.button(label="🎁 CLAIM", style=discord.ButtonStyle.success)
        async def claim(self, interaction: discord.Interaction, button: Button):
            drop = _active_drops.get(drop_id)
            if not drop or drop["claimed"]:
                return await interaction.response.send_message("❌ Already claimed!", ephemeral=True)
            drop["claimed"]    = True
            drop["claimer_id"] = interaction.user.id
            button.disabled = True
            button.label    = f"✅ Claimed by {interaction.user.display_name}!"
            button.style    = discord.ButtonStyle.secondary
            # Award to winner
            prof = get_profile(interaction.user.id, interaction.user.display_name)
            grant_prize(prize, interaction.user)
            save_db()
            await interaction.response.edit_message(
                content=(
                    f"🎉 **{interaction.user.mention}** claimed the drop and won **{prize}**! 🎊\n"
                    f"*(+added to profile)*"
                ),
                view=self)
            # Ping in chat
            try:
                await interaction.channel.send(
                    f"🏆 <@{interaction.user.id}> just snatched the **{prize}** drop! Congrats! 🎉",
                    allowed_mentions=discord.AllowedMentions(users=True))
            except Exception:
                pass

    bar_str   = "▰" * 10

    embed = discord.Embed(
        title="🪂 DROP!",
        description=(
            f"A drop has appeared! 🎁\n\n"
            f"**Prize:** `{prize}`\n\n"
            f"{bar_str}\n\n"
            f"⬇️ **Click CLAIM before anyone else!**"
        ),
        color=discord.Color.green()
    )
    embed.set_image(url=STUMBLE_IMG)
    embed.set_footer(text=f"Drop started by {ctx.author.display_name} • Expires in 2 minutes")
    await ctx.send(embed=embed, view=DropView())


# ==========================================
# 🛒 :TEST SHOP (hidden from :help)
# ==========================================
W_ITEMS = {
    "Blue":    {"emoji": "<:W_blue:1507411440112238592>",    "price": 3000, "color": 0x5865F2},
    "Purple":  {"emoji": "<:W_purple:1507411279868854272>",  "price": 3500, "color": 0x9B59B6},
    "Red":     {"emoji": "<:W_red:1506782119928795217>",     "price": 2800, "color": 0xE74C3C},
    "Pink":    {"emoji": "<:W_pink:1507441578912780432>",    "price": 3200, "color": 0xFF69B4},
    "Yellow":  {"emoji": "<:W_yellow:1507414172583854281>",  "price": 2500, "color": 0xF1C40F},
    "Azzurro": {"emoji": "<:Wa:1507442128693760202>",        "price": 3000, "color": 0x5DADE2},
    "Green":   {"emoji": "<:w_green:1507408630906093638>",   "price": 2000, "color": 0x2ECC71},
    "Orange":  {"emoji": "<:W_orang:1507442976517918770>",   "price": 2800, "color": 0xE67E22},
}

GEM_PACKAGES = [
    (200,   3000),
    (500,   5000),
    (1000, 10000),
]

# Exchange rates: (ruby_cost, crystal_reward)
EXCHANGE_RATES = [
    (8000,  150),
    (16000, 500),
]

SHOP_IMAGE = "attached_assets/1780354505647_1780354637437.png"


def _shop_main_embed(prof: dict) -> discord.Embed:
    e = discord.Embed(
        title="🛒 Stumble™ Shop",
        description=(
            f"{E_GEMS} **{format_num(prof.get('gemme', 0))}**　·　"
            f"{E_RUBY} **{format_num(prof.get('rubini', 0))}**　·　"
            f"{E_CRYSTAL} **{format_num(prof.get('cristalli', 0))}**\n\n"
            f"{E_W} **W Items** — **Ruoli colorati esclusivi**\n"
            f"{E_GEMS} **Gems** — **Gemme SG reali**\n"
            f"🔄 **Exchange** — **Ruby ↔ Cristalli**"
        ),
        color=discord.Color.gold()
    )
    return e


class ShopMainView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id

    def _check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    @discord.ui.button(label="W Items", emoji="<:emoji_45:1507810623063461948>", style=discord.ButtonStyle.primary)
    async def w_items(self, interaction: discord.Interaction, button: Button):
        if not self._check(interaction):
            return await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
        prof = get_profile(interaction.user.id, interaction.user.display_name)
        owned = prof.get("w_owned", [])
        lines = []
        for name, data in W_ITEMS.items():
            tag = " ✅" if name in owned else ""
            lines.append(f"{data['emoji']} **W {name}** — {format_num(data['price'])} {E_CRYSTAL}{tag}")
        e = discord.Embed(
            title=f"{E_W} W Items Shop",
            description=(
                f"{E_CRYSTAL} **Crystals:** {format_num(prof.get('cristalli', 0))}\n\n"
                + "\n".join(lines)
            ),
            color=discord.Color.blue()
        )
        e.set_footer(text="Scegli dal menu qui sotto per acquistare un W item!")
        await interaction.response.edit_message(embed=e, view=WShopView(self.user_id))

    @discord.ui.button(label="Gems", emoji="<:gems:1507509442286190652>", style=discord.ButtonStyle.success)
    async def gems_page(self, interaction: discord.Interaction, button: Button):
        if not self._check(interaction):
            return await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
        prof = get_profile(interaction.user.id, interaction.user.display_name)
        lines = [
            f"• **{gems}** {E_GEMS} — {format_num(price)} {E_CRYSTAL}"
            for gems, price in GEM_PACKAGES
        ]
        e = discord.Embed(
            title=f"{E_GEMS} Gems Shop",
            description=(
                f"{E_CRYSTAL} **Crystals:** {format_num(prof.get('cristalli', 0))}\n\n"
                + "\n".join(lines) + "\n\n"
                "⚠️ Le gemme vengono inviate al tuo account SG dal nostro staff."
            ),
            color=discord.Color.purple()
        )
        e.set_footer(text="Linka il tuo account SG con :link prima di comprare le gemme!")
        await interaction.response.edit_message(embed=e, view=GemsShopView(self.user_id))

    @discord.ui.button(label="🔄 Exchange", style=discord.ButtonStyle.secondary)
    async def exchange(self, interaction: discord.Interaction, button: Button):
        if not self._check(interaction):
            return await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
        prof = get_profile(interaction.user.id, interaction.user.display_name)
        e = discord.Embed(
            title="🔄 Currency Exchange",
            description=(
                f"{E_RUBY} **Ruby:** {format_num(prof.get('rubini', 0))}　·　"
                f"{E_CRYSTAL} **Cristalli:** {format_num(prof.get('cristalli', 0))}\n\n"
                f"**Tassi di cambio:**\n"
                f"• **8.000** {E_RUBY} → **150** {E_CRYSTAL}\n"
                f"• **16.000** {E_RUBY} → **500** {E_CRYSTAL}\n\n"
                "Scegli un'opzione qui sotto:"
            ),
            color=discord.Color.orange()
        )
        await interaction.response.edit_message(embed=e, view=ExchangeView(self.user_id))


class WShopSelect(discord.ui.Select):
    def __init__(self, user_id: int):
        self.user_id = user_id
        options = []
        for name, data in W_ITEMS.items():
            m = re.match(r"<:(\w+):(\d+)>", data["emoji"])
            emoji = discord.PartialEmoji(name=m.group(1), id=int(m.group(2))) if m else None
            options.append(discord.SelectOption(
                label=f"W {name} — {format_num(data['price'])} Crystals",
                value=name, emoji=emoji))
        super().__init__(placeholder=f"Scegli un W item…", min_values=1, max_values=1, options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your shop!", ephemeral=True)
        w_name = self.values[0]
        w_data = W_ITEMS[w_name]
        prof   = get_profile(interaction.user.id, interaction.user.display_name)
        if w_name in prof.get("w_owned", []):
            return await interaction.response.send_message(
                f"❌ Hai già **{w_data['emoji']} W {w_name}**!", ephemeral=True)
        if prof.get("cristalli", 0) < w_data["price"]:
            return await interaction.response.send_message(
                f"❌ Cristalli insufficienti! Ne hai bisogno di **{format_num(w_data['price'])}** {E_CRYSTAL}",
                ephemeral=True)
        prof["cristalli"] -= w_data["price"]
        prof.setdefault("w_owned", []).append(w_name)
        role = discord.utils.get(interaction.guild.roles, name=f"W {w_name}")
        if not role:
            try:
                role = await interaction.guild.create_role(
                    name=f"W {w_name}", color=discord.Color(w_data["color"]), reason="Shop")
            except Exception as ex:
                print(f"[w shop role] {ex}")
        if role:
            try:
                await interaction.user.add_roles(role, reason="W shop")
            except Exception as ex:
                print(f"[w shop add] {ex}")
        save_db()
        await interaction.response.send_message(
            f"✅ Acquistato **{w_data['emoji']} W {w_name}**! Ruolo aggiunto. 🎉\n"
            f"Cristalli rimasti: {format_num(prof['cristalli'])} {E_CRYSTAL}", ephemeral=True)


class WShopView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.add_item(WShopSelect(user_id))
        back_btn = Button(label="◀️ Back", style=discord.ButtonStyle.danger, row=1)
        async def back_cb(interaction: discord.Interaction):
            if interaction.user.id != user_id:
                return await interaction.response.send_message("❌ Not your shop!", ephemeral=True)
            prof = get_profile(interaction.user.id, interaction.user.display_name)
            await interaction.response.edit_message(embed=_shop_main_embed(prof), view=ShopMainView(user_id))
        back_btn.callback = back_cb
        self.add_item(back_btn)


class GemsShopSelect(discord.ui.Select):
    def __init__(self, user_id: int):
        self.user_id = user_id
        m = re.match(r"<:(\w+):(\d+)>", E_GEMS)
        gems_emoji = discord.PartialEmoji(name=m.group(1), id=int(m.group(2))) if m else None
        options = [
            discord.SelectOption(
                label=f"{gems} Gems — {format_num(price)} Crystals",
                value=str(i), emoji=gems_emoji)
            for i, (gems, price) in enumerate(GEM_PACKAGES)
        ]
        super().__init__(placeholder="Scegli un pacchetto gemme…", min_values=1, max_values=1, options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your shop!", ephemeral=True)
        idx   = int(self.values[0])
        gems, price = GEM_PACKAGES[idx]
        prof  = get_profile(interaction.user.id, interaction.user.display_name)
        if prof.get("cristalli", 0) < price:
            return await interaction.response.send_message(
                f"❌ Cristalli insufficienti! Ne hai bisogno di **{format_num(price)}** {E_CRYSTAL}", ephemeral=True)
        sg = db.get("sg_links", {}).get(str(interaction.user.id))
        if not sg:
            return await interaction.response.send_message(
                "❌ Devi collegare il tuo account SG con `:link` prima di comprare gemme!", ephemeral=True)
        prof["cristalli"] -= price
        prof["gemme"]      = prof.get("gemme", 0) + gems
        save_db()
        guild = interaction.guild
        owner_role = guild.get_role(OWNER_ROLE_ID)
        cat   = guild.get_channel(TICKET_GEMS_CAT) or guild.get_channel(TICKET_SUPPORT_CAT)
        ow = {guild.default_role: discord.PermissionOverwrite(read_messages=False)}
        if owner_role:
            ow[owner_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        ow[interaction.user] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        try:
            ch = await guild.create_text_channel(
                name=f"gems-{interaction.user.display_name[:18]}",
                category=cat, overwrites=ow, reason="Gems purchase")
            e2 = discord.Embed(
                title=f"{E_GEMS} Gems Purchase",
                description=(
                    f"**User:** {interaction.user.mention}\n"
                    f"**SG Account:** `{sg}`\n"
                    f"**Gems ordered:** `{gems}` {E_GEMS}\n"
                    f"**Crystals paid:** `{format_num(price)}` {E_CRYSTAL}\n\n"
                    "Please transfer the gems to the user's SG account and then close this ticket."
                ),
                color=discord.Color.purple()
            )
            e2.set_footer(text=f"User ID: {interaction.user.id}")
            ping = f"<@&{OWNER_ROLE_ID}>" if owner_role else ""
            await ch.send(content=ping, embed=e2)
        except Exception as ex:
            print(f"[gems ticket] {ex}")
        await interaction.response.send_message(
            f"✅ Acquistato **{gems}** {E_GEMS}! Lo staff trasferirà le gemme al tuo account SG (`{sg}`).\n"
            f"Cristalli rimasti: {format_num(prof['cristalli'])} {E_CRYSTAL}", ephemeral=True)


class GemsShopView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.add_item(GemsShopSelect(user_id))
        back_btn = Button(label="◀️ Back", style=discord.ButtonStyle.danger, row=1)
        async def back_cb(interaction: discord.Interaction):
            if interaction.user.id != user_id:
                return await interaction.response.send_message("❌ Not your shop!", ephemeral=True)
            prof = get_profile(interaction.user.id, interaction.user.display_name)
            await interaction.response.edit_message(embed=_shop_main_embed(prof), view=ShopMainView(user_id))
        back_btn.callback = back_cb
        self.add_item(back_btn)


class ExchangeView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id

    def _check(self, interaction):
        return interaction.user.id == self.user_id

    async def _do_ruby_to_crystal(self, interaction: discord.Interaction, ruby_cost: int, crystal_gain: int):
        if not self._check(interaction):
            return await interaction.response.send_message("❌ Not your shop!", ephemeral=True)
        prof = get_profile(interaction.user.id, interaction.user.display_name)
        if prof.get("rubini", 0) < ruby_cost:
            return await interaction.response.send_message(
                f"❌ Servono almeno **{format_num(ruby_cost)}** {E_RUBY}. Hai: {format_num(prof.get('rubini',0))} {E_RUBY}",
                ephemeral=True)
        prof["rubini"]    -= ruby_cost
        prof["cristalli"] += crystal_gain
        save_db()
        await interaction.response.send_message(
            f"✅ **{format_num(ruby_cost)}** {E_RUBY} → **{format_num(crystal_gain)}** {E_CRYSTAL}!\n"
            f"Bilancio: {format_num(prof['rubini'])} {E_RUBY} · {format_num(prof['cristalli'])} {E_CRYSTAL}",
            ephemeral=True)

    async def _do_crystal_to_ruby(self, interaction: discord.Interaction, crystal_cost: int, ruby_gain: int):
        if not self._check(interaction):
            return await interaction.response.send_message("❌ Not your shop!", ephemeral=True)
        prof = get_profile(interaction.user.id, interaction.user.display_name)
        if prof.get("cristalli", 0) < crystal_cost:
            return await interaction.response.send_message(
                f"❌ Servono almeno **{format_num(crystal_cost)}** {E_CRYSTAL}. Hai: {format_num(prof.get('cristalli',0))} {E_CRYSTAL}",
                ephemeral=True)
        prof["cristalli"] -= crystal_cost
        prof["rubini"]    += ruby_gain
        save_db()
        await interaction.response.send_message(
            f"✅ **{format_num(crystal_cost)}** {E_CRYSTAL} → **{format_num(ruby_gain)}** {E_RUBY}!\n"
            f"Bilancio: {format_num(prof['rubini'])} {E_RUBY} · {format_num(prof['cristalli'])} {E_CRYSTAL}",
            ephemeral=True)

    @discord.ui.button(label="8k Ruby → 150 Cristalli", style=discord.ButtonStyle.primary, row=0)
    async def rate1_to_crystal(self, interaction: discord.Interaction, button: Button):
        await self._do_ruby_to_crystal(interaction, 8000, 150)

    @discord.ui.button(label="16k Ruby → 500 Cristalli", style=discord.ButtonStyle.primary, row=0)
    async def rate2_to_crystal(self, interaction: discord.Interaction, button: Button):
        await self._do_ruby_to_crystal(interaction, 16000, 500)

    @discord.ui.button(label="150 Cristalli → 8k Ruby", style=discord.ButtonStyle.secondary, row=1)
    async def rate1_to_ruby(self, interaction: discord.Interaction, button: Button):
        await self._do_crystal_to_ruby(interaction, 150, 8000)

    @discord.ui.button(label="500 Cristalli → 16k Ruby", style=discord.ButtonStyle.secondary, row=1)
    async def rate2_to_ruby(self, interaction: discord.Interaction, button: Button):
        await self._do_crystal_to_ruby(interaction, 500, 16000)

    @discord.ui.button(label="◀️ Back", style=discord.ButtonStyle.danger, row=2)
    async def back(self, interaction: discord.Interaction, button: Button):
        if not self._check(interaction):
            return await interaction.response.send_message("❌ Not your shop!", ephemeral=True)
        prof = get_profile(interaction.user.id, interaction.user.display_name)
        await interaction.response.edit_message(embed=_shop_main_embed(prof), view=ShopMainView(self.user_id))


@bot.command(name="test")
async def test_shop(ctx):
    """Hidden shop command (available in shop channel only)."""
    prof = get_profile(ctx.author.id, ctx.author.display_name)
    embed = _shop_main_embed(prof)
    if os.path.exists(SHOP_IMAGE):
        f = discord.File(SHOP_IMAGE, filename="shop.png")
        embed.set_image(url="attachment://shop.png")
        await ctx.send(file=f, embed=embed, view=ShopMainView(ctx.author.id))
    else:
        embed.set_image(url=STUMBLE_IMG)
        await ctx.send(embed=embed, view=ShopMainView(ctx.author.id))


# ==========================================
# 🎰 STUMBLE MACHINE
# ==========================================

def _spin_result(multiplier: int) -> tuple:
    """Returns (reels, outcome, ruby_win, crystal_win, flavor_text)."""
    reels = [random.choice(SLOT_EMOJIS) for _ in range(3)]
    if reels[0] == reels[1] == reels[2]:
        sym = reels[0]
        if sym == "🐔":
            return reels, "jackpot_loss", 0, 0, "💀 TRE GALLINE! Hai appena perso tutto, campione 🐔🐔🐔\nSarà per la prossima volta… o forse no."
        elif sym == "👑":
            ruby = random.randint(5000, 10000) * multiplier
            return reels, "rare", ruby, 0, f"👑 **JACKPOT CORONA!** Assegnato il ruolo **{STUMBLE_GAMBLER_ROLE_NAME}**!"
        elif sym == "💎":
            ruby = random.randint(2000, 8000) * multiplier
            return reels, "base_big", ruby, 0, "💎 **TRIPLE DIAMANTE!** Sei un mito."
        elif sym == "🔴":
            crystal = random.randint(500, 2000) * multiplier
            return reels, "medium", 0, crystal, "🔴 **TRIPLE ROSSO!** Cristalli per te!"
    counts = {e: reels.count(e) for e in set(reels)}
    best = max(counts, key=counts.get)
    if counts[best] >= 2 and best != "🐔":
        ruby = random.randint(100, 2000) * multiplier
        return reels, "base_small", ruby, 0, f"**Coppia {best}!** Piccola vincita."
    return reels, "loss", 0, 0, "Nessuna combinazione. Meglio la prossima volta!"


def _machine_embed(prof: dict) -> discord.Embed:
    e = discord.Embed(
        title="🎰 Stumble Machine",
        description=(
            "**Come funziona:**\n"
            "Gira i rulli e tenta la fortuna! Tre simboli uguali = vincita.\n\n"
            f"**Costo:** `{SLOT_MACHINE_COST}` {E_RUBY} · oppure **x10** per `{SLOT_MACHINE_COST * 10}` {E_RUBY}\n\n"
            "**Premi:**\n"
            "👑👑👑 — **Jackpot**: Ruby casuali + ruolo Stumble Gambler\n"
            "💎💎💎 — **Grande vincita**: 2.000–8.000 Ruby\n"
            "🔴🔴🔴 — **Vincita media**: 500–2.000 Cristalli\n"
            "🐔🐔🐔 — **Sconfitta totale**: perdi la puntata\n"
            "2x uguali — **Piccola vincita**: 100–2.000 Ruby\n\n"
            f"**Il tuo saldo:** {format_num(prof.get('rubini', 0))} {E_RUBY}"
        ),
        color=discord.Color.gold()
    )
    e.set_image(url=STUMBLE_IMG)
    e.set_footer(text="Stumble™ Machine • Premi un pulsante per giocare!")
    return e


class SlotMachineAmountModal(Modal, title="🎰 Scegli la puntata"):
    amount = TextInput(
        label="Quanti Ruby vuoi puntare?",
        placeholder="Da 300 a 3000, multipli di 300",
        min_length=3,
        max_length=4,
    )

    def __init__(self, view: "SlotMachineView"):
        super().__init__()
        self.machine_view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount.value.strip())
        except ValueError:
            return await interaction.response.send_message(
                "❌ Inserisci un numero valido.", ephemeral=True
            )
        if amount < SLOT_MACHINE_COST or amount > SLOT_MACHINE_COST * 10 or amount % SLOT_MACHINE_COST:
            return await interaction.response.send_message(
                f"❌ La puntata deve essere un multiplo di {SLOT_MACHINE_COST}, "
                f"tra {SLOT_MACHINE_COST} e {SLOT_MACHINE_COST * 10} Ruby.",
                ephemeral=True,
            )
        await self.machine_view._play(interaction, amount // SLOT_MACHINE_COST)


class SlotMachineView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id

    def _check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    async def _play(self, interaction: discord.Interaction, multiplier: int):
        if not self._check(interaction):
            return await interaction.response.send_message("❌ Non è la tua macchina!", ephemeral=True)
        cost = SLOT_MACHINE_COST * multiplier
        prof = get_profile(interaction.user.id, interaction.user.display_name)
        if prof.get("rubini", 0) < cost:
            return await interaction.response.send_message(
                f"❌ Ruby insufficienti! Ti servono **{format_num(cost)}** {E_RUBY}. "
                f"Hai: {format_num(prof.get('rubini', 0))} {E_RUBY}", ephemeral=True)
        prof["rubini"] -= cost
        reels, outcome, ruby_win, crystal_win, flavor = _spin_result(multiplier)
        reel_str = "  ".join(reels)
        result_lines = [f"╔══ 🎰 RISULTATO ══╗", f"║  {reel_str}  ║", f"╚═══════════════════╝", f"", flavor]
        if ruby_win:
            prof["rubini"] += ruby_win
            prof["slot_ruby_won"] = prof.get("slot_ruby_won", 0) + ruby_win
            result_lines.append(f"\n💰 +**{format_num(ruby_win)}** {E_RUBY}")
        if crystal_win:
            prof["cristalli"] = prof.get("cristalli", 0) + crystal_win
            result_lines.append(f"\n💠 +**{format_num(crystal_win)}** {E_CRYSTAL}")
        if outcome in ("rare",):
            prof["slot_wins"] = prof.get("slot_wins", 0) + 1
            # Assign Stumble Gambler role
            guild = interaction.guild
            if guild:
                role = discord.utils.get(guild.roles, name=STUMBLE_GAMBLER_ROLE_NAME)
                if role:
                    try:
                        await interaction.user.add_roles(role, reason="Stumble Machine jackpot")
                        result_lines.append(f"\n🏅 Hai ottenuto il ruolo **{STUMBLE_GAMBLER_ROLE_NAME}**!")
                    except Exception:
                        pass
        elif outcome in ("base_big", "base_small", "medium"):
            prof["slot_wins"] = prof.get("slot_wins", 0) + 1
        save_db()
        color = discord.Color.green() if outcome != "jackpot_loss" and outcome != "loss" else discord.Color.red()
        em = discord.Embed(
            title="🎰 Stumble Machine — Risultato",
            description="\n".join(result_lines),
            color=color
        )
        em.set_footer(text=f"Saldo: {format_num(prof['rubini'])} Ruby · {format_num(prof.get('cristalli', 0))} Cristalli")
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=em, view=self)

    @discord.ui.button(label="🎰 Gioca  (300 Ruby)", style=discord.ButtonStyle.primary)
    async def play_normal(self, interaction: discord.Interaction, button: Button):
        await self._play(interaction, 1)

    @discord.ui.button(label="🎰 x10  (3.000 Ruby)", style=discord.ButtonStyle.danger)
    async def play_x10(self, interaction: discord.Interaction, button: Button):
        await self._play(interaction, 10)

    @discord.ui.button(label="🎯 Scegli puntata", style=discord.ButtonStyle.secondary)
    async def choose_amount(self, interaction: discord.Interaction, button: Button):
        if not self._check(interaction):
            return await interaction.response.send_message("❌ Non è la tua macchina!", ephemeral=True)
        await interaction.response.send_modal(SlotMachineAmountModal(self))


@bot.command(name="machine")
async def machine_cmd(ctx):
    """🎰 Stumble Machine — gira i rulli e vinci Ruby o Cristalli!"""
    prof = get_profile(ctx.author.id, ctx.author.display_name)
    await ctx.send(embed=_machine_embed(prof), view=SlotMachineView(ctx.author.id))


# ==========================================
# ⚔️  :1v1 SFIDE E SCOMMESSE
# ==========================================

class _DuelWagerModal(Modal):
    def __init__(self, dueler_role: str):
        super().__init__(title=f"💰 Cosa scommetti, {dueler_role}?")
        self.amount = TextInput(
            label="Quanti Ruby vuoi scommettere?",
            placeholder="es. 500",
            min_length=1, max_length=10)
        self.add_item(self.amount)
        self.dueler_role = dueler_role  # "sfidante" | "sfidato"
        self._result: int | None = None

    async def on_submit(self, interaction: discord.Interaction):
        try:
            val = int(self.amount.value.strip())
            if val <= 0:
                raise ValueError
            self._result = val
        except ValueError:
            await interaction.response.send_message("❌ Inserisci un numero positivo di Ruby.", ephemeral=True)
            return
        # Signal to the view via a stored future
        await interaction.response.defer()
        if hasattr(self, "_callback"):
            await self._callback(interaction, val)


class DuelView(View):
    """Full lifecycle view for a 1v1 duel — persists across all phases."""

    def __init__(self, challenger: discord.Member, challenged: discord.Member, channel_id: int, guild_id: int):
        super().__init__(timeout=600)
        self.challenger  = challenger
        self.challenged  = challenged
        self.channel_id  = channel_id
        self.guild_id    = guild_id
        self.state       = "pending"    # pending → wagering → confirming → arbiting
        self.bet_a: int | None = None   # challenger's ruby bet
        self.bet_b: int | None = None   # challenged's ruby bet
        self.confirmed: set  = set()    # ids who confirmed
        self._msg: discord.Message | None = None

    # ── Helpers ────────────────────────────────────────────────────────────

    def _is_staff(self, member: discord.Member) -> bool:
        return any(r.id in STAFF_ROLE_IDS | ADMIN_ROLE_IDS | {OWNER_ROLE_ID, HOSTER_ROLE_ID}
                   for r in member.roles)

    def _duel_embed(self, title: str, desc: str, color=discord.Color.blue()) -> discord.Embed:
        e = discord.Embed(title=title, description=desc, color=color)
        e.add_field(name="⚔️ Sfidante",  value=self.challenger.mention, inline=True)
        e.add_field(name="🛡️ Sfidato",   value=self.challenged.mention, inline=True)
        if self.bet_a is not None:
            e.add_field(name="💰 Puntata Sfidante", value=f"{format_num(self.bet_a)} {E_RUBY}", inline=True)
        if self.bet_b is not None:
            e.add_field(name="💰 Puntata Sfidato",  value=f"{format_num(self.bet_b)} {E_RUBY}", inline=True)
        e.set_image(url=STUMBLE_IMG)
        return e

    async def _set_buttons(self, *buttons):
        self.clear_items()
        for b in buttons:
            self.add_item(b)

    # ── Phase 1: Accept / Refuse ────────────────────────────────────────────

    @discord.ui.button(label="✅ Accetta", style=discord.ButtonStyle.success, custom_id="duel_accept")
    async def accept(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.challenged.id:
            return await interaction.response.send_message("❌ Solo lo sfidato può accettare!", ephemeral=True)
        self.state = "wagering"
        self.clear_items()
        # Add wager buttons
        bet_a_btn = Button(label=f"💰 Scommessa {self.challenger.display_name}", style=discord.ButtonStyle.primary, custom_id="duel_bet_a")
        bet_b_btn = Button(label=f"💰 Scommessa {self.challenged.display_name}",  style=discord.ButtonStyle.primary, custom_id="duel_bet_b")
        bet_a_btn.callback = self._bet_a_callback
        bet_b_btn.callback = self._bet_b_callback
        self.add_item(bet_a_btn)
        self.add_item(bet_b_btn)
        em = self._duel_embed(
            "⚔️ Sfida Accettata!",
            f"{self.challenged.mention} ha accettato la sfida!\n\n"
            f"**Fase 2:** Ognuno inserisce la propria scommessa premendo il proprio pulsante.",
            discord.Color.orange()
        )
        await interaction.response.edit_message(embed=em, view=self)

    @discord.ui.button(label="❌ Rifiuta", style=discord.ButtonStyle.danger, custom_id="duel_refuse")
    async def refuse(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id not in (self.challenged.id, self.challenger.id):
            return await interaction.response.send_message("❌ Non puoi rifiutare questa sfida.", ephemeral=True)
        for child in self.children:
            child.disabled = True
        em = self._duel_embed("❌ Sfida Rifiutata", f"{interaction.user.mention} ha rifiutato la sfida.", discord.Color.red())
        await interaction.response.edit_message(embed=em, view=self)
        self.stop()

    # ── Phase 2: Wager modals ───────────────────────────────────────────────

    async def _bet_a_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.challenger.id:
            return await interaction.response.send_message("❌ Questo pulsante è per lo sfidante!", ephemeral=True)
        modal = _DuelWagerModal("Sfidante")
        async def _cb(inter, val):
            prof = get_profile(self.challenger.id, self.challenger.display_name)
            if prof.get("rubini", 0) < val:
                await inter.followup.send(f"❌ Non hai abbastanza Ruby! Hai {format_num(prof.get('rubini',0))} {E_RUBY}", ephemeral=True)
                return
            self.bet_a = val
            await self._check_both_wagered(inter)
        modal._callback = _cb
        await interaction.response.send_modal(modal)

    async def _bet_b_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.challenged.id:
            return await interaction.response.send_message("❌ Questo pulsante è per lo sfidato!", ephemeral=True)
        modal = _DuelWagerModal("Sfidato")
        async def _cb(inter, val):
            prof = get_profile(self.challenged.id, self.challenged.display_name)
            if prof.get("rubini", 0) < val:
                await inter.followup.send(f"❌ Non hai abbastanza Ruby! Hai {format_num(prof.get('rubini',0))} {E_RUBY}", ephemeral=True)
                return
            self.bet_b = val
            await self._check_both_wagered(inter)
        modal._callback = _cb
        await interaction.response.send_modal(modal)

    async def _check_both_wagered(self, interaction: discord.Interaction):
        """After each wager, refresh the embed. If both set, show Confirm button."""
        if self._msg is None:
            return
        if self.bet_a is not None and self.bet_b is not None:
            self.state = "confirming"
            self.clear_items()
            confirm_btn = Button(label="🤝 Conferma Sfida", style=discord.ButtonStyle.success, custom_id="duel_confirm")
            confirm_btn.callback = self._confirm_callback
            self.add_item(confirm_btn)
            em = self._duel_embed(
                "⚔️ Scommesse Inserite!",
                f"Entrambi hanno inserito le puntate.\n"
                f"**Entrambi** devono premere **Conferma Sfida** per avviare il duello!",
                discord.Color.blurple()
            )
        else:
            waiting_for = self.challenger.display_name if self.bet_a is None else self.challenged.display_name
            em = self._duel_embed(
                "⚔️ Sfida in corso...",
                f"In attesa della scommessa di **{waiting_for}**...",
                discord.Color.orange()
            )
        try:
            await self._msg.edit(embed=em, view=self)
        except Exception:
            pass

    # ── Phase 3: Confirm ────────────────────────────────────────────────────

    async def _confirm_callback(self, interaction: discord.Interaction):
        if interaction.user.id not in (self.challenger.id, self.challenged.id):
            return await interaction.response.send_message("❌ Solo i duellanti possono confermare!", ephemeral=True)
        self.confirmed.add(interaction.user.id)
        wait_txt = "Attendo l'altro..." if len(self.confirmed) < 2 else "Tutti confermati!"
        await interaction.response.send_message(
            f"✅ {interaction.user.display_name} ha confermato! ({wait_txt})",
            ephemeral=True)
        if len(self.confirmed) >= 2:
            await self._start_arbiter()

    async def _start_arbiter(self):
        if self._msg is None:
            return
        self.state = "arbiting"
        # Deduct bets from both
        prof_a = get_profile(self.challenger.id, self.challenger.display_name)
        prof_b = get_profile(self.challenged.id, self.challenged.display_name)
        bet_a  = self.bet_a or 0
        bet_b  = self.bet_b or 0
        prof_a["rubini"] = max(0, prof_a.get("rubini", 0) - bet_a)
        prof_b["rubini"] = max(0, prof_b.get("rubini", 0) - bet_b)
        save_db()
        self.clear_items()
        win_a = Button(label=f"🏆 Vince {self.challenger.display_name}", style=discord.ButtonStyle.success, custom_id="duel_win_a")
        win_b = Button(label=f"🏆 Vince {self.challenged.display_name}",  style=discord.ButtonStyle.danger,  custom_id="duel_win_b")
        win_a.callback = lambda i: self._declare_winner(i, self.challenger, self.challenged)
        win_b.callback = lambda i: self._declare_winner(i, self.challenged, self.challenger)
        self.add_item(win_a)
        self.add_item(win_b)
        total = bet_a + bet_b
        em = self._duel_embed(
            "⚔️ Duello in corso!",
            f"Il duello è iniziato!\n\n"
            f"**Puntata totale in palio:** {format_num(total)} {E_RUBY}\n\n"
            f"⚠️ Solo lo **Staff** può dichiarare il vincitore.",
            discord.Color.red()
        )
        try:
            await self._msg.edit(embed=em, view=self)
        except Exception:
            pass

    # ── Phase 4: Arbiter (staff only) ────────────────────────────────────────

    async def _declare_winner(self, interaction: discord.Interaction, winner: discord.Member, loser: discord.Member):
        if not self._is_staff(interaction.user):
            return await interaction.response.send_message("❌ Solo lo **Staff** può arbitrare!", ephemeral=True)
        total = (self.bet_a or 0) + (self.bet_b or 0)
        prof_w = get_profile(winner.id, winner.display_name)
        prof_w["rubini"]    = prof_w.get("rubini", 0) + total
        prof_w["duel_wins"] = prof_w.get("duel_wins", 0) + 1
        save_db()
        # Assign Block Dash Legend role
        guild = interaction.guild
        legend_role = discord.utils.get(guild.roles, name=BLOCK_DASH_LEGEND_ROLE_NAME) if guild else None
        role_txt = ""
        if legend_role:
            try:
                await winner.add_roles(legend_role, reason="1v1 winner")
                role_txt = f"\n🏅 Assegnato il ruolo **{BLOCK_DASH_LEGEND_ROLE_NAME}**!"
            except Exception:
                pass
        for child in self.children:
            child.disabled = True
        em = discord.Embed(
            title="🏆 Duello Terminato!",
            description=(
                f"**Vincitore:** {winner.mention}{role_txt}\n"
                f"**+{format_num(total)}** {E_RUBY} assegnati!{role_txt}\n\n"
                f"Arbitro: {interaction.user.mention}"
            ),
            color=discord.Color.gold()
        )
        em.add_field(name="⚔️ Sfidante", value=self.challenger.mention, inline=True)
        em.add_field(name="🛡️ Sfidato",  value=self.challenged.mention,  inline=True)
        em.set_image(url=STUMBLE_IMG)
        await interaction.response.edit_message(embed=em, view=self)
        self.stop()


@bot.command(name="1v1")
async def duel_cmd(ctx, opponent: discord.Member = None):
    """⚔️ Sfida un utente a un duello con scommesse in Ruby!"""
    if opponent is None:
        return await ctx.send("❌ Usa: `:1v1 @utente`", delete_after=5.0)
    if opponent.id == ctx.author.id:
        return await ctx.send("❌ Non puoi sfidare te stesso!", delete_after=5.0)
    if opponent.bot:
        return await ctx.send("❌ Non puoi sfidare un bot!", delete_after=5.0)
    view = DuelView(ctx.author, opponent, ctx.channel.id, ctx.guild.id)
    em = discord.Embed(
        title="⚔️ Sfida 1v1!",
        description=(
            f"{ctx.author.mention} ha sfidato {opponent.mention} a un duello!\n\n"
            f"**{opponent.display_name}**, accetti la sfida?\n\n"
            f"Il vincitore riceve tutta la puntata e il ruolo **{BLOCK_DASH_LEGEND_ROLE_NAME}**! 🏅"
        ),
        color=discord.Color.blue()
    )
    em.add_field(name="⚔️ Sfidante", value=ctx.author.mention,  inline=True)
    em.add_field(name="🛡️ Sfidato",  value=opponent.mention, inline=True)
    em.set_image(url=STUMBLE_IMG)
    msg = await ctx.send(embed=em, view=view)
    view._msg = msg


# ==========================================
# 💎 SCOMMESSE SUI MATCH DEL TORNEO
# ==========================================

class _BetAmountModal(Modal):
    def __init__(self, match_id: str, choice: str):
        super().__init__(title=f"💎 Scommetti su {choice}")
        self.match_id = match_id
        self.choice   = choice
        self.amount   = TextInput(
            label="Quanti Cristalli vuoi scommettere?",
            placeholder="es. 200",
            min_length=1, max_length=8)
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            val = int(self.amount.value.strip())
            if val <= 0:
                raise ValueError
        except ValueError:
            return await interaction.response.send_message("❌ Inserisci un numero positivo.", ephemeral=True)
        bet_data = active_bets.get(self.match_id)
        if not bet_data:
            return await interaction.response.send_message("❌ La scommessa per questo match non è più attiva.", ephemeral=True)
        prof = get_profile(interaction.user.id, interaction.user.display_name)
        if prof.get("cristalli", 0) < val:
            return await interaction.response.send_message(
                f"❌ Cristalli insufficienti! Hai: {format_num(prof.get('cristalli',0))} {E_CRYSTAL}", ephemeral=True)
        uid = str(interaction.user.id)
        if uid in bet_data["bets"]:
            return await interaction.response.send_message("❌ Hai già scommesso su questo match!", ephemeral=True)
        prof["cristalli"] = prof.get("cristalli", 0) - val
        save_db()
        bet_data["bets"][uid] = {"choice": self.choice, "amount": val}
        await interaction.response.send_message(
            f"✅ Scommessa registrata! **{format_num(val)}** {E_CRYSTAL} su **{self.choice}**.\n"
            f"Se vince, ricevi il doppio: **{format_num(val * 2)}** {E_CRYSTAL}!",
            ephemeral=True)


class MatchBettingView(View):
    def __init__(self, match_id: str, p1: str, p2: str):
        super().__init__(timeout=None)
        self.match_id = match_id
        self.p1 = p1
        self.p2 = p2
        btn1 = Button(label=f"🎯 {p1[:30]}", style=discord.ButtonStyle.primary,  custom_id=f"bet_{match_id}_p1")
        btn2 = Button(label=f"🎯 {p2[:30]}", style=discord.ButtonStyle.secondary, custom_id=f"bet_{match_id}_p2")
        btn1.callback = lambda i: self._bet(i, p1)
        btn2.callback = lambda i: self._bet(i, p2)
        self.add_item(btn1)
        self.add_item(btn2)

    async def _bet(self, interaction: discord.Interaction, choice: str):
        # Check player is not one of the competitors (by display name match)
        t = db.get("tour") or {}
        player_names = [n.lower() for n in t.get("player_names", [])]
        if interaction.user.display_name.lower() in player_names:
            return await interaction.response.send_message(
                "❌ I giocatori non possono scommettere sui propri match!", ephemeral=True)
        await interaction.response.send_modal(_BetAmountModal(self.match_id, choice))


async def _post_match_bets(channel: discord.TextChannel, t: dict):
    """Posta un embed scommessa per ogni match del round corrente."""
    matches = t.get("matches", {})
    if not matches:
        return
    cur_round = t.get("round", 1)
    count = 0
    for mid, m in matches.items():
        if m.get("winner"):
            continue
        p1 = m.get("p1", "?")
        p2 = m.get("p2", "?")
        if p2 == "BYE":
            continue
        mid_str = str(mid)
        active_bets[mid_str] = {"p1": p1, "p2": p2, "bets": {}, "channel_id": channel.id}
        em = discord.Embed(
            title=f"💎 Scommesse — Match #{mid} (Round {cur_round})",
            description=(
                f"**{p1}** ⚔️ **{p2}**\n\n"
                f"Scommetti i tuoi {E_CRYSTAL} **Cristalli** sul vincitore!\n"
                f"Se indovini → **raddoppi** la puntata!\n\n"
                f"*(I giocatori del match non possono scommettere)*"
            ),
            color=discord.Color.purple()
        )
        em.set_footer(text="Stumble™ Betting • Scommetti responsabilmente!")
        await channel.send(embed=em, view=MatchBettingView(mid_str, p1, p2))
        count += 1
        if count >= 8:  # Cap a 8 embed per non spammare
            break


async def _resolve_bets_for_match(match_id: str, winner_name: str):
    """Risolve le scommesse per un match: paga i vincitori, trattiene le perdite."""
    bet_data = active_bets.pop(str(match_id), None)
    if not bet_data:
        return
    for uid, bet in bet_data["bets"].items():
        if bet["choice"].lower() == winner_name.lower() or winner_name.lower() in bet["choice"].lower():
            prof = get_profile(int(uid), uid)
            prof["cristalli"] = prof.get("cristalli", 0) + bet["amount"] * 2
    save_db()


# ==========================================
# 🏆 :stumble-top CLASSIFICA SPECIALE
# ==========================================

@bot.command(name="stumble-top", aliases=["stumbletop"])
async def stumble_top(ctx):
    """🏆 Top 10 per vittorie 1v1 e Ruby vinti alla Stumble Machine."""
    profiles = db.get("profiles", {})
    if not profiles:
        return await ctx.send("❌ Nessun profilo trovato.", delete_after=5.0)

    # Sort by duel wins desc, then slot_ruby_won desc
    ranked = sorted(
        profiles.items(),
        key=lambda kv: (kv[1].get("duel_wins", 0), kv[1].get("slot_ruby_won", 0)),
        reverse=True
    )[:3]

    medals = ["🥇", "🥈", "🥉"]
    lines  = []
    for i, (uid, p) in enumerate(ranked):
        name        = p.get("name", uid)
        duel_wins   = p.get("duel_wins", 0)
        slot_ruby   = p.get("slot_ruby_won", 0)
        slot_wins   = p.get("slot_wins", 0)
        lines.append(
            f"{medals[i]} **{name}**\n"
            f"  ⚔️ Vittorie 1v1: `{duel_wins}` · 🎰 Machine wins: `{slot_wins}` · "
            f"Ruby vinti: `{format_num(slot_ruby)}` {E_RUBY}"
        )

    em = discord.Embed(
        title="🏆 Stumble Top — Classifica Speciale",
        description="\n\n".join(lines) or "Nessun dato disponibile ancora.",
        color=discord.Color.gold()
    )
    em.set_footer(text=f"Top per vittorie 1v1 + Stumble Machine · Stumble™")
    em.set_image(url=STUMBLE_IMG)
    await ctx.send(embed=em)


# --- AVVIO DEL BOT ---
token = os.environ.get("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("ERRORE: DISCORD_TOKEN non trovato.")
