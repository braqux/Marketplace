import discord
from discord import app_commands, ui
from discord.ext import commands
import datetime
import os
from datetime import timezone

# --- Configuration ---
# Securely gets credentials from the hosting environment (Railway).
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN") 
MARKETPLACE_CHANNEL_ID = int(os.environ.get("MARKETPLACE_CHANNEL_ID"))
THIRD_PARTY_CHANNEL_ID = int(os.environ.get("THIRD_PARTY_CHANNEL_ID"))
GUILD_ID = int(os.environ.get("GUILD_ID"))

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MarketBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.user_cooldowns = {}

    async def on_ready(self):
        print(f'Logged in as {self.user.name} ({self.user.id})')
        print('------')
        await self.tree.sync(guild=discord.Object(id=GUILD_ID))

bot = MarketBot()

# --- UI Components ---
class BuyView(ui.View):
    def __init__(self, seller: discord.Member, item_name: str, item_description: str, item_price: str):
        super().__init__(timeout=None)
        self.seller = seller
        self.item_name = item_name
        self.item_description = item_description
        self.item_price = item_price

    @ui.button(label="Buy Now", style=discord.ButtonStyle.success, custom_id="buy_now_button")
    async def buy_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
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
        trade_embed.add_field(name="Item Name", value=self.item_name, inline=False)
        trade_embed.add_field(name="Item Description", value=self.item_description, inline=False)
        trade_embed.add_field(name="Price", value=self.item_price, inline=False)
        trade_embed.add_field(name="Seller", value=f"{self.seller.mention} (`{self.seller.id}`)", inline=True)
        trade_embed.add_field(name="Buyer", value=f"{buyer.mention} (`{buyer.id}`)", inline=True)
        trade_embed.set_footer(text="Trade Bot")

        try:
            await third_party_channel.send(embed=trade_embed)
            button.disabled = True
            button.label = "Sold"
            await interaction.message.edit(view=self)
            await interaction.followup.send("Your purchase request has been sent to the third party for processing.", ephemeral=True)
            
            try:
                await self.seller.send(f"Your item '{self.item_name}' is being purchased by {buyer.mention}.")
            except discord.Forbidden:
                print(f"Could not DM seller {self.seller.name}. They may have DMs disabled.")

        except discord.Forbidden:
            print(f"Error: Bot missing permissions in third-party channel ({THIRD_PARTY_CHANNEL_ID}).")
            await interaction.followup.send("An error occurred. The bot may be missing permissions.", ephemeral=True)
        except Exception as e:
            print(f"An unexpected error occurred during the buy process: {e}")
            await interaction.followup.send("An unexpected error occurred.", ephemeral=True)

class SellModal(ui.Modal, title='List an Item for Sale'):
    item_name = ui.TextInput(label='Product/Service Name', placeholder='e.g., Custom Logo Design')
    description = ui.TextInput(label='Description', style=discord.TextStyle.paragraph, placeholder='Provide details about your item.')
    price = ui.TextInput(label='Price', placeholder='e.g., $50 or 10 Credits')

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        marketplace_channel = interaction.guild.get_channel(MARKETPLACE_CHANNEL_ID)
        
        if not marketplace_channel:
            await interaction.followup.send("Error: Marketplace channel not found. Please contact an admin.", ephemeral=True)
            return

        embed = discord.Embed(title=self.item_name.value, description=self.description.value, color=discord.Color.blue())
        embed.add_field(name="Price", value=self.price.value, inline=False)
        embed.set_footer(text="Posted by an anonymous seller")
        
        view = BuyView(seller=interaction.user, item_name=self.item_name.value, item_description=self.description.value, item_price=self.price.value)

        try:
            await marketplace_channel.send(embed=embed, view=view)
            await interaction.followup.send('Your anonymous listing has been posted!', ephemeral=True)
            bot.user_cooldowns[interaction.user.id] = datetime.datetime.now(timezone.utc)
        except Exception as e:
            print(f"Error posting to marketplace: {e}")
            await interaction.followup.send('There was an error posting your listing.', ephemeral=True)

# --- Slash Commands ---
@bot.tree.command(name="sell", description="List a service or product anonymously.", guild=discord.Object(id=GUILD_ID))
async def sell(interaction: discord.Interaction):
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
            
    await interaction.response.send_modal(SellModal())

# --- Bot Execution ---
if all([BOT_TOKEN, MARKETPLACE_CHANNEL_ID, THIRD_PARTY_CHANNEL_ID, GUILD_ID]):
    bot.run(BOT_TOKEN)
else:
    print("ERROR: One or more required environment variables are missing.")
    print("Please set DISCORD_BOT_TOKEN, MARKETPLACE_CHANNEL_ID, THIRD_PARTY_CHANNEL_ID, and GUILD_ID in Railway.")
