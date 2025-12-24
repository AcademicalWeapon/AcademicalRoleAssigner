"""The Academical Role Assigner Discord Bot: create/update a cosmetic role
Repurposed from Academical Creator Discord Bot. Refer to Documentation on Obsidian for usage.

This File reads the bot token from a .env file (use the key `DC_TOKEN`).
Roles are cosmetic only: the bot will create or update a role's colour and will assign the role to the user.

Arguments: !addrole <hexcolor> <true/assign/false> 
- The 'true'/'assign' argument is optional; if provided, the bot will also assign the role to the user. If not provided, the role is created/updated but not assigned to the User Running the Command

Command: `!addrole #RRGGBB` or `!addrole RRGGBB`
"""

# * Imports
import os
import re
import logging
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv() 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# * .env file needed here
TOKEN = os.getenv("DC_TOKEN")

intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents,
                   description="Cosmetic role creator")

HEX_RE = re.compile(r"^#?[0-9A-Fa-f]{6}$")


@bot.event
async def on_ready():
    logger.info("Logged in as %s (ID: %s)", bot.user, bot.user.id)
    # * Sync application (slash) commands. Global sync can take up to an hour to appear;
    # * syncing each guild could be used for faster testing.
    try:
        await bot.tree.sync()
        logger.info("Slash commands synced.")
    except Exception:
        logger.exception("Failed to sync slash commands")


def _hex_to_color(hex_str: str) -> discord.Color:
    hex_clean = hex_str.lstrip("#")
    return discord.Color(int(hex_clean, 16))


@bot.command(name="addrole", help="Create or update a cosmetic role named after you with a hex colour")
@commands.guild_only()
async def addrole(ctx: commands.Context, hex_color: str, assign: str | None = None):
    """
    Creates or updates a role named after the invoking user's display name.
    """

    if not HEX_RE.match(hex_color):
        await ctx.send("Please provide a valid hex color code, like `#RRGGBB` or `RRGGBB`.")
        return

    role_name = ctx.author.display_name
    guild = ctx.guild

    # Permission checks
    if not guild.me.guild_permissions.manage_roles:
        await ctx.send("I need the `Manage Roles` permission to create or edit roles.")
        return

    bot_top_role = guild.me.top_role

    hex_clean = hex_color.lstrip("#").upper()
    color = _hex_to_color(hex_clean)

    existing = discord.utils.get(guild.roles, name=role_name)
    try:
        if existing:
                    # * Ensure the bot can edit this role (role below the bot's top role)
            if existing >= bot_top_role:
                await ctx.send("I cannot modify that role because it is equal or higher than my top role.")
                return
            await existing.edit(color=color, reason=f"Cosmetic color update by {ctx.author}")
            await ctx.send(f"Updated colour of role **{role_name}** to `#{hex_clean}`.")
            role = existing
        else:
            # * Create the role — new roles are created below the bot's top role by default
            role = await guild.create_role(name=role_name, color=color, reason=f"Cosmetic role created by {ctx.author}")
            await ctx.send(f"Created cosmetic role **{role.name}** with colour `#{hex_clean}`.")
        # * parse optional assign parameter (text command accepts words like yes/true/assign)

        def _parse_assign(val: str | None) -> bool:
            if val is None:
                return False
            if isinstance(val, bool):
                return val
            v = str(val).strip().lower()
            return v in ("1", "true", "yes", "y", "assign")

        assign_flag = _parse_assign(assign)
        if assign_flag:
                # * ensure bot can assign the role
            if role >= bot_top_role:
                await ctx.send("I cannot assign that role because it is equal or higher than my top role.")
                return
            try:
                await ctx.author.add_roles(role, reason="Assigned by addrole command")
                await ctx.send(f"Assigned role **{role.name}** to you.")
            except discord.Forbidden:
                await ctx.send("I cannot assign the role to you. Ensure my highest role is above the role I'm creating.")
            except Exception as e:
                await ctx.send(f"Role created/updated but failed to assign: {e}")
        else:
            await ctx.send("Role created/updated but not assigned (cosmetic only). Provide `assign` to assign.")
    except discord.Forbidden:
        await ctx.send("I don't have permission to create or edit roles. Please check my permissions and role position.")
    except discord.HTTPException as e:
        await ctx.send(f"Discord API error: {e}")
    except Exception as e:  # fallback
        logger.exception("Unexpected error in addrole")
        await ctx.send(f"Unexpected error: {e}")


# * Slash (application) command
@bot.tree.command(name="addrole", description="Create or update a cosmetic role named after you with a hex colour")
@app_commands.describe(hex_color="Hex color like #RRGGBB or RRGGBB")
async def addrole_slash(interaction: discord.Interaction, hex_color: str, assign: bool = False):
    if not HEX_RE.match(hex_color):
        await interaction.response.send_message("Please provide a valid hex color code like `#RRGGBB` or `RRGGBB`.", ephemeral=True)
        return

    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("This command must be used in a server (guild).", ephemeral=True)
        return

    member = guild.get_member(interaction.user.id)
    if member is None:
        # fallback to interaction.user
        member = interaction.user

    if not guild.me.guild_permissions.manage_roles:
        await interaction.response.send_message("I need the `Manage Roles` permission to create or edit roles.", ephemeral=True)
        return

    bot_top_role = guild.me.top_role
    role_name = member.display_name
    hex_clean = hex_color.lstrip("#").upper()
    color = _hex_to_color(hex_clean)

    existing = discord.utils.get(guild.roles, name=role_name)
    # ! This is a fucking mess.
    try:
        if existing:
            if existing >= bot_top_role:
                await interaction.response.send_message("I cannot modify that role because it is equal or higher than my top role.", ephemeral=True)
                return
            await existing.edit(color=color, reason=f"Cosmetic color update via slash command by {interaction.user}")
            role = existing
            # optionally assign
            if assign:
                if role >= bot_top_role:
                    await interaction.response.send_message("I cannot assign that role because it is equal or higher than my top role.", ephemeral=True)
                    return
                try:
                    await member.add_roles(role, reason="Assigned via slash command")
                    await interaction.response.send_message(f"Updated colour of role **{role_name}** to `#{hex_clean}` and assigned to you.")
                except discord.Forbidden:
                    await interaction.response.send_message("I cannot assign the role to you. Ensure my highest role is above the role I'm creating.", ephemeral=True)
                except Exception as e:
                    await interaction.response.send_message(f"Role updated but failed to assign: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"Updated colour of role **{role_name}** to `#{hex_clean}`.")
        else:
            role = await guild.create_role(name=role_name, color=color, reason=f"Cosmetic role created via slash command by {interaction.user}")
            # optionally assign the created role
            if assign:
                try:
                    await member.add_roles(role, reason="Assigned via slash command")
                    await interaction.response.send_message(f"Created and assigned role **{role.name}** with colour `#{hex_clean}`.")
                except discord.Forbidden:
                    await interaction.response.send_message("Created role but I couldn't assign it due to permission/role position.", ephemeral=True)
                except Exception as e:
                    await interaction.response.send_message(f"Created role but failed to assign: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"Created role **{role.name}** with colour `#{hex_clean}`. (Not assigned.)")
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to create or edit roles. Please check my permissions and role position.", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"Discord API error: {e}", ephemeral=True)
    except Exception as e:
        logger.exception("Unexpected error in addrole_slash")
        await interaction.response.send_message(f"Unexpected error occurred: {e}", ephemeral=True)

# ? I still don't understand why people do this but it's in like every Tutorial.
if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception as e:
        logger.exception(f"Failed to start bot: {e}")
        exit()
