import discord
from discord.ext import commands
from compraView import CompraViewPorCategoria  # Sua view de compra
from ticket_view import TicketView  # Sua view com botões Abrir Carrinho e Fechar Ticket

class CriarTicketView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="📩 Criar Ticket", style=discord.ButtonStyle.green, custom_id="criar_ticket")
    async def criar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        # Verifica se já tem ticket aberto
        existing_ticket = discord.utils.get(guild.text_channels, name=f"ticket-{user.name}")
        if existing_ticket:
            await interaction.response.send_message(
                f"⚠️ Você já tem um ticket aberto: {existing_ticket.mention}",
                ephemeral=True
            )
            return

        role_atendente = discord.utils.get(guild.roles, name="୨୧ ་ 𝐀tendente⸝⸝")
        if not role_atendente:
            await interaction.response.send_message("❌ A role 'Atendente' não foi encontrada!", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                attach_files=True,
                embed_links=True
            ),
            role_atendente: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_messages=True
            ),
            guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_channels=True
            )
        }

        try:
            ticket_channel = await guild.create_text_channel(
                name=f"ticket-{user.name}",
                overwrites=overwrites,
                topic=f"Ticket de {user.display_name} | ID: {user.id}",
                position=0
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao criar ticket: {e}", ephemeral=True)
            return

        embed = discord.Embed(
            title="🎫 TICKET DE ATENDIMENTO",
            description=(
                f"Olá {user.mention}, seja bem-vindo ao seu ticket!\n\n"
                "🔹 **Como podemos ajudar?**\n"
                "• Acompanhamento de compras\n"
                "• Suporte técnico\n"
                "• Dúvidas sobre produtos\n\n"
                "🛒 **Gerenciar Carrinho**\n"
                "Use os botões abaixo para navegar e controlar seu carrinho"
            ),
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Atendimento disponível das 9h às 18h")


        # Envia embed com CompraViewPorCategoria
        compra_view = CompraViewPorCategoria(user=user, channel=ticket_channel)
        msg_compra = await ticket_channel.send(embed=embed, view=compra_view)
        compra_view.message = msg_compra  # para permitir edição da view depois

        # Envia mensagem com os botões Abrir Carrinho e Fechar Ticket (TicketView)
        ticket_view = TicketView(guild=guild)
        await ticket_channel.send("⚙️ Controles do ticket:", view=ticket_view)

        await interaction.response.send_message(
            f"✅ Ticket criado com sucesso: {ticket_channel.mention}",
            ephemeral=True
        )
