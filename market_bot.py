import discord
from discord import app_commands, ui
from discord.ext import commands
import datetime
import os
from datetime import timezone
import asyncio

# --- Configuration ---
# This block is now wrapped in a try...except to prevent crashes on startup.
try:
    BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
    MARKETPLACE_CHANNEL_ID = int(os.environ.get("MARKETPLACE_CHANNEL_ID"))
    THIRD_PARTY_CHANNEL_ID = int(os.environ.get("THIRD_PARTY_CHANNEL_ID"))
    GUILD_ID = int(os.environ.get("GUILD_ID"))
    SUPPORT_ROLE_IDS_STR = os.environ.get("SUPPORT_ROLE_IDS")
    SUPPORT_ROLE_IDS = [int(role_id.strip()) for role_id in SUPPORT_ROLE_IDS_STR.split(',')]
    TICKET_CATEGORY_ID = int(os.environ.get("TICKET_CATEGORY_ID"))


    # Check if any essential variable is missing right away
    if not all([BOT_TOKEN, MARKETPLACE_CHANNEL_ID, THIRD_PARTY_CHANNEL_ID, GUILD_ID, SUPPORT_ROLE_IDS, TICKET_CATEGORY_ID]):
        raise ValueError("One or more required environment variables are not set.")

except (TypeError, ValueError) as e:
    print("--- CONFIGURATION ERROR ---")
    print("One of your environment variables is missing or invalid.")
    print("Please check the following variables on Railway:")
    print("- DISCORD_BOT_TOKEN")
    print("- MARKETPLACE_CHANNEL_ID")
    print("- THIRD_PARTY_CHANNEL_ID")
    print("- GUILD_ID")
    print("- SUPPORT_ROLE_IDS (must be a comma-separated list of role IDs)")
    print("- TICKET_CATEGORY_ID (The ID of the category where tickets should be created)")
    print(f"Error details: {e}")
    # Exit gracefully if configuration is bad
    exit()

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MarketBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.user_cooldowns = {}

    async def setup_hook(self) -> None:
        # Register the persistent views so they work after the bot restarts
        self.add_view(MarketplaceDashboard())
        self.add_view(BuyView()) # Register the stateless BuyView
        
        # Manually add the commands to the tree before syncing.
        self.tree.add_command(panel_command, guild=discord.Object(id=GUILD_ID))
        self.tree.add_command(notify_command, guild=discord.Object(id=GUILD_ID))
        self.tree.add_command(close_command, guild=discord.Object(id=GUILD_ID))
        
        # Sync commands in setup_hook for guaranteed registration.
        try:
            print("Attempting to sync commands to the guild from setup_hook...")
            synced = await self.tree.sync(guild=discord.Object(id=GUILD_ID))
            print(f"Successfully synced {len(synced)} commands to the guild.")
        except Exception as e:
            print(f"An error occurred while syncing commands: {e}")

    async def on_ready(self):
        print(f'Logged in as {self.user.name} ({self.user.id})')
        print('------')

bot = MarketBot()

# --- Commands (Defined without a decorator) ---

# --- MODIFIED COMMAND --- Renamed from setup to panel
@app_commands.checks.has_permissions(administrator=True)
async def panel_callback(interaction: discord.Interaction):
    channel = interaction.guild.get_channel(MARKETPLACE_CHANNEL_ID)
    if not channel:
        await interaction.response.send_message("Error: Marketplace channel ID is incorrect. Check your configuration.", ephemeral=True)
        return

    embed = discord.Embed(
        title="Merhba Bikoum F L'Marketplace , Hna T9dro t7to/Tchriw Ga3 Les Services En toute Securité O Guarantie!",
        description="KHTARO HNA DAKCHI LI KAT9DMO OLA WESSFO DAKCHI LI KHASSKOM .",
        color=discord.Color.dark_gold()
    )
    try:
        await channel.send(embed=embed, view=MarketplaceDashboard())
        await interaction.response.send_message(f"Marketplace panel has been sent to {channel.mention}.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"Error: I don't have permission to send messages in {channel.mention}.", ephemeral=True)

panel_command = app_commands.Command(name="panel", description="Posts the marketplace control panel.", callback=panel_callback)

@panel_command.error
async def panel_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You do not have permission to run this command.", ephemeral=True)
    else:
        print(f"An error occurred with the panel command: {error}")
        await interaction.response.send_message("An unexpected error occurred.", ephemeral=True)

# Notify Command
@app_commands.checks.has_permissions(administrator=True)
async def notify_callback(interaction: discord.Interaction, role: discord.Role, message: str):
    await interaction.response.defer(ephemeral=True, thinking=True)
    
    members_with_role = role.members
    if not members_with_role:
        await interaction.followup.send(f"There are no members with the {role.mention} role.", ephemeral=True)
        return

    success_count = 0
    fail_count = 0

    notification_embed = discord.Embed(
        title="A Message from the Staff",
        description=message,
        color=role.color if role.color.value != 0 else discord.Color.blurple()
    )
    notification_embed.set_footer(text=f"This message was sent to all members with the '{role.name}' role.")

    for member in members_with_role:
        if member.bot:
            continue
        try:
            await member.send(embed=notification_embed)
            success_count += 1
            await asyncio.sleep(1) 
        except discord.Forbidden:
            fail_count += 1
        except Exception as e:
            fail_count += 1
            print(f"Failed to send DM to {member.name}: {e}")

    await interaction.followup.send(f"Notification sent!\n\n✅ Successfully sent to **{success_count}** members.\n❌ Failed to send to **{fail_count}** members (they may have DMs disabled).", ephemeral=True)

notify_command = app_commands.Command(name="notify", description="Sends a DM to all members with a specific role.", callback=notify_callback)

@notify_command.error
async def notify_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You do not have permission to run this command.", ephemeral=True)
    else:
        print(f"An error occurred with the notify command: {error}")
        await interaction.response.send_message("An unexpected error occurred.", ephemeral=True)

# Close Ticket Command
@app_commands.checks.has_permissions(manage_channels=True)
async def close_callback(interaction: discord.Interaction):
    if "ticket-" in interaction.channel.name:
        await interaction.response.send_message("Closing this ticket in 5 seconds...")
        await asyncio.sleep(5)
        await interaction.channel.delete()
    else:
        await interaction.response.send_message("This command can only be used in a ticket channel.", ephemeral=True)

close_command = app_commands.Command(name="close", description="Closes a support ticket channel.", callback=close_callback)

@close_command.error
async def close_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You do not have permission to run this command.", ephemeral=True)
    else:
        print(f"An error occurred with the close command: {error}")
        await interaction.response.send_message("An unexpected error occurred.", ephemeral=True)


# --- UI Components ---

class BuyView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Buy Now", style=discord.ButtonStyle.success, custom_id="buy_now_button")
    async def buy_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        if not interaction.message.embeds:
            await interaction.followup.send("Error: Could not find listing details.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        
        item_name = embed.title if embed.title else "N/A"
        item_description = embed.description if embed.description else "No description provided."
        price_field = discord.utils.get(embed.fields, name="Price")
        item_price = price_field.value if price_field else "N/A"
        
        footer_text = embed.footer.text
        if not footer_text or "SellerID:" not in footer_text:
            await interaction.followup.send("Error: Listing is invalid. Seller ID is missing.", ephemeral=True)
            return
        
        try:
            seller_id_str = footer_text.split("SellerID:")[1]
            seller_id = int(seller_id_str)
            seller = await interaction.guild.fetch_member(seller_id)
        except (IndexError, ValueError, discord.NotFound):
            await interaction.followup.send("Error: Could not identify the seller. The user may have left the server.", ephemeral=True)
            return

        buyer = interaction.user
        third_party_channel = interaction.guild.get_channel(THIRD_PARTY_CHANNEL_ID)

        if not third_party_channel:
            await interaction.followup.send("Error: Third-party channel not found. Please contact an admin.", ephemeral=True)
            return
            
        trade_embed = discord.Embed(
            title="Trade Initiated",
            description="A buyer has clicked the 'Buy' button. Please facilitate the trade.",
            color=discord.Color.gold(),
            timestamp=datetime.datetime.now(timezone.utc)
        )
        trade_embed.add_field(name="Item Name", value=item_name, inline=False)
        trade_embed.add_field(name="Item Description", value=item_description, inline=False)
        trade_embed.add_field(name="Price", value=item_price, inline=False)
        trade_embed.add_field(name="Seller", value=f"{seller.mention} (`{seller.id}`)", inline=True)
        trade_embed.add_field(name="Buyer", value=f"{buyer.mention} (`{buyer.id}`)", inline=True)
        trade_embed.set_footer(text="Trade Bot")

        try:
            await third_party_channel.send(embed=trade_embed)
            button.disabled = True
            button.label = "Sold"
            await interaction.message.edit(view=self)
            await interaction.followup.send("Your purchase request has been sent to the third party for processing.", ephemeral=True)
            
            try:
                await seller.send(f"Salam ,Trade Dyalk Katverifya 7aliyan '{item_name}' Une fois Verifié Ghadi Itwasslo M3ak F A9rab We9te.")
            except discord.Forbidden:
                print(f"Could not DM seller {seller.name}. They may have DMs disabled.")

        except discord.Forbidden:
            print(f"Error: Bot missing permissions in third-party channel ({THIRD_PARTY_CHANNEL_ID}).")
            await interaction.followup.send("An error occurred. The bot may be missing permissions.", ephemeral=True)
        except Exception as e:
            print(f"An unexpected error occurred during the buy process: {e}")
            await interaction.followup.send("An unexpected error occurred.", ephemeral=True)

class SellModal(ui.Modal):
    def __init__(self, category: str):
        super().__init__(title=f"List a New {category}")
        self.category = category

        self.item_name = ui.TextInput(label='Product/Service Name', placeholder='e.g., Custom Logo Design')
        self.description = ui.TextInput(label='Description', style=discord.TextStyle.paragraph, placeholder='Provide details about your item.')
        self.price = ui.TextInput(label='Price', placeholder='e.g., $50 or 10 Credits')
        
        self.add_item(self.item_name)
        self.add_item(self.description)
        self.add_item(self.price)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        marketplace_channel = interaction.guild.get_channel(MARKETPLACE_CHANNEL_ID)
        
        if not marketplace_channel:
            await interaction.followup.send("Error: Marketplace channel not found. Please contact an admin.", ephemeral=True)
            return

        embed = discord.Embed(title=self.item_name.value, description=self.description.value, color=discord.Color.blue())
        embed.add_field(name="Category", value=self.category, inline=True)
        embed.add_field(name="Price", value=self.price.value, inline=True)
        embed.set_footer(text=f"SellerID:{interaction.user.id}")
        
        view = BuyView()

        try:
            await marketplace_channel.send(embed=embed, view=view)
            await interaction.followup.send('Your anonymous listing has been posted!', ephemeral=True)
            bot.user_cooldowns[interaction.user.id] = datetime.datetime.now(timezone.utc)
        except Exception as e:
            print(f"Error posting to marketplace: {e}")
            await interaction.followup.send('There was an error posting your listing.', ephemeral=True)

class MarketplaceDashboard(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def check_cooldown_and_show_modal(self, interaction: discord.Interaction, category: str):
        user_id = interaction.user.id
        cooldown_period = datetime.timedelta(hours=12)
        
        if user_id in bot.user_cooldowns:
            last_post_time = bot.user_cooldowns[user_id]
            time_since_last_post = datetime.datetime.now(timezone.utc) - last_post_time
            
            if time_since_last_post < cooldown_period:
                time_remaining = cooldown_period - time_since_last_post
                hours, remainder = divmod(int(time_remaining.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)
                await interaction.response.send_message(f"You must wait {hours}h {minutes}m before posting again.", ephemeral=True)
                return
        
        await interaction.response.send_modal(SellModal(category=category))

    @ui.button(label="Sell a Service", style=discord.ButtonStyle.primary, custom_id="sell_service_button", emoji="💼")
    async def sell_service_button(self, interaction: discord.Interaction, button: ui.Button):
        await self.check_cooldown_and_show_modal(interaction, "Service")

    @ui.button(label="Sell a Product", style=discord.ButtonStyle.primary, custom_id="sell_product_button", emoji="📦")
    async def sell_product_button(self, interaction: discord.Interaction, button: ui.Button):
        await self.check_cooldown_and_show_modal(interaction, "Product")

    @ui.button(label="Sell a Tool", style=discord.ButtonStyle.primary, custom_id="sell_tool_button", emoji="🛠️")
    async def sell_tool_button(self, interaction: discord.Interaction, button: ui.Button):
        await self.check_cooldown_and_show_modal(interaction, "Tool")
        
    @ui.button(label="Pro Consultation", style=discord.ButtonStyle.primary, custom_id="sell_consultation_button", emoji="🎓")
    async def sell_consultation_button(self, interaction: discord.Interaction, button: ui.Button):
        await self.check_cooldown_and_show_modal(interaction, "Pro Consultation")

    @ui.button(label="Contact Support", style=discord.ButtonStyle.secondary, custom_id="contact_support_button", row=2, emoji="🎟️")
    async def contact_support_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)

        support_roles = [interaction.guild.get_role(role_id) for role_id in SUPPORT_ROLE_IDS]
        support_roles = [role for role in support_roles if role is not None] 

        if not support_roles:
            await interaction.followup.send("Error: No valid support roles found. Please contact an admin.", ephemeral=True)
            return

        for channel in interaction.guild.text_channels:
            if channel.name == f"ticket-{interaction.user.name.lower()}":
                await interaction.followup.send(f"You already have an open ticket: {channel.mention}", ephemeral=True)
                return

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        for role in support_roles:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        try:
            category = interaction.guild.get_channel(TICKET_CATEGORY_ID)
            if not category or not isinstance(category, discord.CategoryChannel):
                await interaction.followup.send("Error: The ticket category ID is invalid or not a category.", ephemeral=True)
                return

            ticket_channel = await category.create_text_channel(
                name=f"ticket-{interaction.user.name.lower()}",
                overwrites=overwrites,
                topic=f"Support ticket for {interaction.user.name} (ID: {interaction.user.id})"
            )
            
            support_mentions = " ".join(role.mention for role in support_roles)
            await ticket_channel.send(
                f"Welcome {interaction.user.mention}! {support_mentions} will be with you shortly.\n"
                f"Please describe your issue in detail."
            )

            await interaction.followup.send(f"A support ticket has been created for you: {ticket_channel.mention}", ephemeral=True)

        except discord.Forbidden:
            print("Error: Bot is missing permissions to create a channel in the specified category.")
            await interaction.followup.send("I don't have the required permissions to create a ticket channel.", ephemeral=True)
        except Exception as e:
            print(f"An error occurred while creating a ticket: {e}")
            await interaction.followup.send("An unexpected error occurred while creating your ticket.", ephemeral=True)

# --- Bot Execution ---
bot.run(BOT_TOKEN)
