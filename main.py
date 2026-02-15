import discord
from discord.ext import commands
from discord import app_commands
import os, datetime, json, re, time, asyncio

# --- 💾 1. MEMORIA E INTEGRACIÓN (Railway /datos) ---
FILE_PATH = "/datos/history.json"

def cargar_datos():
    vacio = {"warns": {}, "afk": {}, "m_roles": {}}
    if not os.path.exists(FILE_PATH): return vacio
    try:
        with open(FILE_PATH, "r") as f:
            datos = json.load(f)
            for key in vacio:
                if key not in datos: datos[key] = {}
            return datos
    except: return vacio

def guardar_datos(datos):
    os.makedirs(os.path.dirname(FILE_PATH), exist_ok=True)
    with open(FILE_PATH, "w") as f: json.dump(datos, f, indent=4)

# --- ⚙️ 2. CONFIGURACIÓN HIBRIDACIÓN TOTAL ---
intents = discord.Intents.all()
class UZBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='a!', intents=intents)
        self.history = cargar_datos()

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Comandos hibridados y sincronizados en (/) y a!")

bot = UZBot()

# --- 🛠️ 3. UTILIDADES DE SEGURIDAD Y JERARQUÍA ---

async def check_staff(ctx, permission=None):
    """Verifica Rol de Staff + Permiso real de Discord"""
    user = ctx.author if isinstance(ctx, commands.Context) else ctx.user
    if user.guild_permissions.administrator: return True
    
    sid = str(ctx.guild.id)
    staff_roles = bot.history.get("m_roles", {}).get(sid, [])
    if not isinstance(staff_roles, list): staff_roles = [staff_roles] if staff_roles else []
    
    has_staff_role = any(user.get_role(rid) for rid in staff_roles)
    if not has_staff_role:
        if isinstance(ctx, commands.Context): await ctx.reply("❌ No tienes un rol de Staff configurado.")
        else: await ctx.send("❌ No tienes un rol de Staff configurado.", ephemeral=True)
        return False

    if permission and not getattr(user.guild_permissions, permission):
        msg = f"❌ Tu rol de Staff no tiene el permiso real de Discord: `{permission}`."
        if isinstance(ctx, commands.Context): await ctx.reply(msg)
        else: await ctx.send(msg, ephemeral=True)
        return False
    return True

async def can_interact_logic(ctx, target):
    """Implementación de la Regla de Oro e Inmunidad de Admins"""
    executor = ctx.author if isinstance(ctx, commands.Context) else ctx.user
    sid = str(ctx.guild.id)

    if target.guild_permissions.administrator:
        e = discord.Embed(title="⚖️ Sistema de Seguridad", color=0x8b0000)
        e.description = "❌ **Acción Cancelada:** Estás intentando sancionar a un **Administrador Superior**.\n\n*Tu intento ha sido registrado. No tienes autoridad para aplicar castigos a este rango.*"
        if isinstance(ctx, commands.Context): await ctx.reply(embed=e)
        else: await ctx.send(embed=e)
        return False

    staff_roles = bot.history.get("m_roles", {}).get(sid, [])
    if not isinstance(staff_roles, list): staff_roles = [staff_roles] if staff_roles else []
    
    exec_staff_roles = [r.id for r in executor.roles if r.id in staff_roles]
    target_staff_roles = [r.id for r in target.roles if r.id in staff_roles]
    
    for r_id in exec_staff_roles:
        if r_id in target_staff_roles:
            msg = "❌ No puedes sancionar a alguien con tu mismo rol de Staff."
            if isinstance(ctx, commands.Context): await ctx.reply(msg)
            else: await ctx.send(msg)
            return False
    return True

def get_target(ctx, usuario: discord.Member = None):
    if usuario: return usuario
    if isinstance(ctx, commands.Context) and ctx.message.reference:
        res = ctx.message.reference.resolved
        if isinstance(res, discord.Message): return res.author
    return None

def embed_base(target, titulo, color=0xff0000):
    e = discord.Embed(title=f"⚖️ {titulo}", color=color)
    e.set_thumbnail(url=target.display_avatar.url)
    e.add_field(name="Usuario", value=target.mention)
    return e

# --- 🛡️ 4. COMANDOS DE GESTIÓN (Staff-Only) ---

@bot.hybrid_command(name="managerole", description="Añade un rol de Staff (Máx 5)")
@app_commands.default_permissions(administrator=True)
async def managerole(ctx, rol: discord.Role):
    sid = str(ctx.guild.id)
    if sid not in bot.history["m_roles"]: bot.history["m_roles"][sid] = []
    if len(bot.history["m_roles"][sid]) >= 5: 
        return await (ctx.reply("❌ Máximo 5 roles permitidos.") if isinstance(ctx, commands.Context) else ctx.send("❌ Máximo 5 roles permitidos."))
    
    if rol.id not in bot.history["m_roles"][sid]:
        bot.history["m_roles"][sid].append(rol.id)
        guardar_datos(bot.history)
        msg = f"🛡️ Rol {rol.mention} añadido como Staff con éxito."
        await (ctx.reply(msg) if isinstance(ctx, commands.Context) else ctx.send(msg))
    else: 
        msg = "❌ El rol ya está en la lista de gestión."
        await (ctx.reply(msg) if isinstance(ctx, commands.Context) else ctx.send(msg))

@bot.hybrid_command(name="managerole_list", description="Lista los roles con acceso Staff")
@app_commands.default_permissions(moderate_members=True)
async def managerole_list(ctx):
    sid = str(ctx.guild.id)
    roles = bot.history.get("m_roles", {}).get(sid, [])
    if not roles: 
        msg = "No hay roles configurados actualmente."
        return await (ctx.reply(msg) if isinstance(ctx, commands.Context) else ctx.send(msg))
    mentions = [f"<@&{rid}>" for rid in roles]
    msg = f"🛡️ **Roles de Staff registrados:**\n" + "\n".join(mentions)
    await (ctx.reply(msg) if isinstance(ctx, commands.Context) else ctx.send(msg))

@bot.hybrid_command(name="managerole_delete", description="Elimina un rol de la gestión")
@app_commands.default_permissions(administrator=True)
async def managerole_delete(ctx, rol: discord.Role):
    sid = str(ctx.guild.id)
    if sid in bot.history["m_roles"] and rol.id in bot.history["m_roles"][sid]:
        bot.history["m_roles"][sid].remove(rol.id)
        guardar_datos(bot.history)
        msg = f"🗑️ Acceso revocado al rol {rol.mention}."
        await (ctx.reply(msg) if isinstance(ctx, commands.Context) else ctx.send(msg))
    else: 
        msg = "❌ Ese rol no está en la base de datos de Staff."
        await (ctx.reply(msg) if isinstance(ctx, commands.Context) else ctx.send(msg))

# --- ⚖️ 5. MODERACIÓN AVANZADA ---

@bot.hybrid_command(name="warn", description="Aplica una advertencia (Sistema progresivo)")
@app_commands.default_permissions(moderate_members=True)
async def warn(ctx, usuario: discord.Member = None, *, motivo: str = "NO ESTABLECIDO"):
    if not await check_staff(ctx): return
    target = get_target(ctx, usuario)
    if not target: 
        msg = "❌ Menciona a alguien o responde a un mensaje."
        return await (ctx.reply(msg) if isinstance(ctx, commands.Context) else ctx.send(msg))
    
    # Manejo de argumentos inteligentes para Context (reply)
    if isinstance(ctx, commands.Context) and ctx.message.reference and not usuario:
        args = ctx.message.content.split()
        if len(args) > 1: motivo = " ".join(args[1:])

    if not await can_interact_logic(ctx, target): return

    uid = str(target.id)
    if uid not in bot.history["warns"]: bot.history["warns"][uid] = []
    bot.history["warns"][uid].append(motivo)
    count = len(bot.history["warns"][uid])
    
    acc = "Aviso visual"
    if count == 2: await target.timeout(datetime.timedelta(hours=12)); acc = "Mute automático (12h)"
    elif count == 3: await target.timeout(datetime.timedelta(days=1)); acc = "Mute automático (1d)"
    elif count >= 4: 
        await target.ban(reason="Acumulación de 4 advertencias")
        acc = "BAN PERMANENTE"
        bot.history["warns"][uid] = [] 
    
    guardar_datos(bot.history)
    e = embed_base(target, "Sistema de Castigos")
    e.add_field(name="Warns", value=f"{count}/4")
    e.add_field(name="Acción", value=acc, inline=False)
    e.add_field(name="Motivo", value=motivo, inline=False)
    await (ctx.reply(embed=e) if isinstance(ctx, commands.Context) else ctx.send(embed=e))

@bot.hybrid_command(name="unwarn", description="Retira la última falta")
@app_commands.default_permissions(moderate_members=True)
async def unwarn(ctx, usuario: discord.Member = None, *, motivo: str = "NO ESTABLECIDO"):
    if not await check_staff(ctx): return
    target = get_target(ctx, usuario)
    if not target: 
        msg = "❌ Menciona a alguien o responde a un mensaje."
        return await (ctx.reply(msg) if isinstance(ctx, commands.Context) else ctx.send(msg))

    if isinstance(ctx, commands.Context) and ctx.message.reference and not usuario:
        args = ctx.message.content.split()
        if len(args) > 1: motivo = " ".join(args[1:])

    if not await can_interact_logic(ctx, target): return
    
    uid = str(target.id)
    if uid in bot.history["warns"] and bot.history["warns"][uid]:
        bot.history["warns"][uid].pop()
        guardar_datos(bot.history)
        if target.is_timed_out(): await target.timeout(None)
        
        e = embed_base(target, "Advertencia Retirada", color=0x2ecc71)
        e.add_field(name="Warns restantes", value=f"{len(bot.history['warns'][uid])}/4")
        e.add_field(name="Motivo del Perdón", value=motivo, inline=False)
        await (ctx.reply(embed=e) if isinstance(ctx, commands.Context) else ctx.send(embed=e))
    else: 
        msg = "El usuario no tiene advertencias activas."
        await (ctx.reply(msg) if isinstance(ctx, commands.Context) else ctx.send(msg))

@bot.hybrid_command(name="mute", description="Silenciar usuario temporalmente")
@app_commands.default_permissions(moderate_members=True)
async def mute(ctx, usuario: discord.Member = None, tiempo: str = None, *, motivo: str = "NO ESTABLECIDO"):
    if not await check_staff(ctx, "moderate_members"): return
    target = get_target(ctx, usuario)
    if not target: 
        msg = "❌ Menciona a alguien o responde a un mensaje."
        return await (ctx.reply(msg) if isinstance(ctx, commands.Context) else ctx.send(msg))
    
    if not await can_interact_logic(ctx, target): return

    # Lógica de argumentos opcionales para Reply/Prefijo
    if isinstance(ctx, commands.Context) and ctx.message.reference and not usuario:
        args = ctx.message.content.split()
        if len(args) > 1:
            potential_time = args[1]
            if re.search(r'\d+[smhd]', potential_time.lower()):
                tiempo = potential_time
                motivo = " ".join(args[2:]) if len(args) > 2 else "NO ESTABLECIDO"
            else:
                tiempo = None
                motivo = " ".join(args[1:])

    dur = datetime.timedelta(days=28)
    disp_time = "PERMANENTE"
    if tiempo:
        m = re.search(r'(\d+)([smhd])', tiempo.lower())
        if m:
            val, unit = int(m.group(1)), m.group(2)
            td = {"s":1, "m":60, "h":3600, "d":86400}[unit]
            dur = datetime.timedelta(seconds=val*td)
            disp_time = tiempo
            
    await target.timeout(dur, reason=motivo)
    e = embed_base(target, "Mute Aplicado")
    e.add_field(name="Duración", value=disp_time)
    e.add_field(name="Motivo", value=motivo, inline=False)
    await (ctx.reply(embed=e) if isinstance(ctx, commands.Context) else ctx.send(embed=e))

@bot.hybrid_command(name="unmute", description="Quitar el silencio a un usuario")
@app_commands.default_permissions(moderate_members=True)
async def unmute(ctx, usuario: discord.Member = None, *, motivo: str = "NO ESTABLECIDO"):
    if not await check_staff(ctx, "moderate_members"): return
    target = get_target(ctx, usuario)
    if not target: 
        msg = "❌ Menciona a alguien o responde a un mensaje."
        return await (ctx.reply(msg) if isinstance(ctx, commands.Context) else ctx.send(msg))

    if isinstance(ctx, commands.Context) and ctx.message.reference and not usuario:
        args = ctx.message.content.split()
        if len(args) > 1: motivo = " ".join(args[1:])

    if not await can_interact_logic(ctx, target): return
    
    await target.timeout(None)
    e = embed_base(target, "Voz Devuelta", color=0x2ecc71)
    e.add_field(name="Acción", value="Unmute")
    e.add_field(name="Motivo", value=motivo, inline=False)
    await (ctx.reply(embed=e) if isinstance(ctx, commands.Context) else ctx.send(embed=e))

@bot.hybrid_command(name="warns", description="Ver historial (Solo Staff)")
@app_commands.default_permissions(moderate_members=True)
async def warns(ctx, usuario: discord.Member = None):
    if not await check_staff(ctx): return
    target = get_target(ctx, usuario) or (ctx.author if isinstance(ctx, commands.Context) else ctx.user)
    
    h = bot.history["warns"].get(str(target.id), [])
    e = discord.Embed(title="⚖️ Historial de Sanciones", color=0x3498db)
    e.description = "\n".join([f"**{i+1}.** {r}" for i, r in enumerate(h)]) or "Este usuario está limpio."
    e.set_thumbnail(url=target.display_avatar.url)
    e.set_footer(text=f"Total: {len(h)}/4")
    await (ctx.reply(embed=e) if isinstance(ctx, commands.Context) else ctx.send(embed=e))

@bot.hybrid_command(name="ban", description="Baneo definitivo")
@app_commands.default_permissions(ban_members=True)
async def ban(ctx, usuario: discord.Member = None, *, motivo: str = "NO ESTABLECIDO"):
    if not await check_staff(ctx, "ban_members"): return
    target = get_target(ctx, usuario)
    if not target: 
        msg = "❌ Menciona a alguien o responde a un mensaje."
        return await (ctx.reply(msg) if isinstance(ctx, commands.Context) else ctx.send(msg))

    if isinstance(ctx, commands.Context) and ctx.message.reference and not usuario:
        args = ctx.message.content.split()
        if len(args) > 1: motivo = " ".join(args[1:])
    
    if await can_interact_logic(ctx, target):
        await target.ban(reason=motivo)
        e = embed_base(target, "BAN PERMANENTE EJECUTADO")
        e.add_field(name="Motivo", value=motivo, inline=False)
        await (ctx.reply(embed=e) if isinstance(ctx, commands.Context) else ctx.send(embed=e))

# --- 🐯 6. SISTEMA AFK (Estilo Nekotina - Actualizado) ---

@bot.event
async def on_message(msg):
    if msg.author.bot: return
    uid = str(msg.author.id)
    
    if msg.content.lower().startswith("uz afk"):
        motivo = msg.content[7:].strip() or "Ausente"
        
        nombre_base = msg.author.display_name.replace("[AFK] ", "").replace(" <UZ>", "").strip()
        bot.history["afk"][uid] = {"m": motivo, "n": nombre_base, "t": time.time()}
        guardar_datos(bot.history)
        
        nuevo_nick = f"[AFK] {nombre_base} <UZ>"[:32]
        try: await msg.author.edit(nick=nuevo_nick)
        except: pass
        
        desc = (
            f"🐯 **{nombre_base} <UZ>**\n"
            f"**Estado ausente establecido.**\n\u200b\n"
            f"**Motivo:** {motivo}\n\u200b\n"
            f"ᴀᴠɪsᴀʀé ᴀ ǫᴜɪᴇɴᴇs ᴛᴇ ᴍᴇɴᴄɪᴏɴᴇɴ."
        )
        
        e = discord.Embed(description=desc, color=0x2b2d31)
        e.set_thumbnail(url=msg.author.display_avatar.url)
        await msg.reply(embed=e)
        return

    if uid in bot.history["afk"]:
        data = bot.history["afk"].pop(uid); guardar_datos(bot.history)
        t = time.time()-data["t"]; h, r = divmod(t, 3600); m, s = divmod(r, 60)
        try: await msg.author.edit(nick=data["n"])
        except: pass
        e = discord.Embed(description=f"**¡Bienvenido/a de regreso!** {msg.author.mention} 🐯, tu estado AFK fue removido. <UZ>\n\n**Ausente desde:** `{int(h)}h {int(m)}m {int(s)}s`", color=0x2ecc71)
        await msg.channel.send(embed=e, delete_after=5)

    for mnt in msg.mentions:
        if str(mnt.id) in bot.history["afk"]:
            info = bot.history["afk"][str(mnt.id)]
            t = time.time()-info["t"]; h, r = divmod(t, 3600); m, s = divmod(r, 60)
            nombre_limpio = mnt.display_name.replace("[AFK] ", "").replace(" <UZ>", "").strip()
            e = discord.Embed(description=f"**{nombre_limpio}** está ausente desde `{int(h)}h {int(m)}m {int(s)}s`.\n\n**Motivo:** {info['m']} 🐯", color=0xf1c40f)
            await msg.reply(embed=e)
            
    await bot.process_commands(msg)

# --- 扫 7. UTILIDADES ---

@bot.hybrid_command(name="clear", description="Limpieza masiva de mensajes")
@app_commands.default_permissions(manage_messages=True)
async def clear(ctx, cantidad: int):
    if not await check_staff(ctx, "manage_messages"): return
    await ctx.channel.purge(limit=min(cantidad, 100))
    msg = f"🗑️ Se han eliminado {cantidad} mensajes."
    await (ctx.reply(msg, delete_after=3) if isinstance(ctx, commands.Context) else ctx.send(msg, delete_after=3))

# --- 🐯 8. SALUDO ACTUALIZADO (SEGÚN IMAGEN) ---

@bot.event
async def on_guild_join(guild):
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            e = discord.Embed(
                title="⚖️ Sistema de Gestión", 
                description="🐯 ¡Hola! Soy tu bot de seguridad\nconfiable profesional.\nLlegó el castigador, portate bien o\nrecibirás una recompensa y no es\nnada bueno.", 
                color=0xed1c24
            )
            if bot.user.avatar: 
                e.set_thumbnail(url=bot.user.avatar.url)
            
            await channel.send(embed=e)
            break

bot.run(os.environ.get("TOKEN"))
                      
