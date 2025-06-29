import discord
import httpx
import asyncio
from carrinho_view import CarrinhoView
from config import API_URL


class TicketView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        self.guild = guild
        self.role_atendente = discord.utils.get(guild.roles, name="୨୧ ་ 𝐀tendente⸝⸝")

        if not self.role_atendente:
            raise ValueError("Role 'Atendente' não encontrada")

    @discord.ui.button(label="Abrir Carrinho", style=discord.ButtonStyle.primary, custom_id="abrir_carrinho")
    async def abrir_carrinho(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True, thinking=True)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{API_URL}/estoque")
                response.raise_for_status()
                estoque = response.json()

            view = CarrinhoView(
                user=interaction.user,
                role_atendente=self.role_atendente,
                estoque=estoque,
                channel=interaction.channel
            )

            mensagem = {
                "content": f"{interaction.user.mention} <@&{self.role_atendente.id}>",
                "embed": view.create_embed(),
                "view": view,
                "ephemeral": False
            }

            if not interaction.response.is_done():
                await interaction.response.send_message(**mensagem)
            else:
                await interaction.followup.send(**mensagem)

        except httpx.RequestError:
            msg = "⏳ O estoque está demorando para responder. Tente novamente."
            if not interaction.response.is_done():
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await interaction.followup.send(msg, ephemeral=True)

        except Exception as e:
            print(f"Erro em abrir_carrinho: {type(e).__name__}: {e}")
            msg = f"❌ Erro ao abrir carrinho: {str(e)}"
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(msg, ephemeral=True)
                else:
                    await interaction.followup.send(msg, ephemeral=True)
            except:
                pass

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, custom_id="fechar_ticket")
    async def fechar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.role_atendente not in interaction.user.roles:
            await interaction.response.send_message(
                "❌ Apenas atendentes podem fechar tickets!",
                ephemeral=True
            )
            return

        username = interaction.channel.name.replace("ticket-", "").split('-')[0]

        if not interaction.response.is_done():
            await interaction.response.defer()

        try:
            all_channels = interaction.guild.channels
            carrinho_channels = [
                channel for channel in all_channels
                if isinstance(channel, discord.TextChannel) and
                channel.name.startswith(f"carrinho-{username}")
            ]

            message = await interaction.followup.send("🔒 Iniciando processo de fechamento...")

            deleted_channels = 0
            for channel in carrinho_channels:
                try:
                    await channel.delete()
                    deleted_channels += 1
                except discord.Forbidden:
                    print(f"Sem permissão para deletar {channel.name}")
                except discord.HTTPException as e:
                    print(f"Erro ao deletar {channel.name}: {e}")

            await message.edit(content=f"✅ Fechado: Ticket e {deleted_channels} carrinho(s) associado(s)")
            await asyncio.sleep(2)
            await interaction.channel.delete()

        except Exception as e:
            print(f"Erro ao fechar ticket/carrinho: {e}")
            try:
                await interaction.followup.send(
                    "❌ Ocorreu um erro ao fechar. Por favor, tente novamente ou feche manualmente.",
                    ephemeral=True
                )
            except:
                pass
