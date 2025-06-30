import discord
import httpx
import asyncio
from discord.ext import commands
from config import API_URL, CANAL_PEDIDOS, ROLE_BOOSTER
from typing import Tuple

# ==================== Ticket Related Views ====================

class CriarTicketView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="📩 Criar Ticket", style=discord.ButtonStyle.green, custom_id="criar_ticket")
    async def criar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        existing_ticket = discord.utils.get(
            guild.text_channels,
            name=f"ticket-{user.name}"
        )
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
                "Clique no botão abaixo para abrir seu carrinho de compras"
            ),
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Atendimento disponível das 9h às 18h")

        await ticket_channel.send(
            content=f"{user.mention} {role_atendente.mention}",
            embed=embed,
            view=TicketView(guild)
        )

        await interaction.response.send_message(
            f"✅ Ticket criado com sucesso: {ticket_channel.mention}",
            ephemeral=True
        )

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

# ==================== Shopping Cart Related Views ====================

def calcular_valores(itens: list, user: discord.Member) -> Tuple[str, bool]:
    subtotal = sum(item['preco'] * item['quantidade'] for item in itens)
    tem_desconto = discord.utils.get(user.roles, name=ROLE_BOOSTER) is not None

    if tem_desconto:
        desconto = subtotal * 0.05
        total_com_desconto = subtotal - desconto
        texto = (
            f"**Subtotal:** R${subtotal:.2f}\n"
            f"**Desconto Booster (5%):** -R${desconto:.2f}\n"
            f"**Total a Pagar:** R${total_com_desconto:.2f}"
        )
    else:
        total_com_desconto = subtotal * 0.95
        texto = (
            f"**Total:** R${subtotal:.2f}\n"
            f"**Com Booster:** R${total_com_desconto:.2f} (economize R${subtotal * 0.05:.2f})"
        )

    return texto, tem_desconto

class CarrinhoView(discord.ui.View):
    def __init__(self, user: discord.Member, role_atendente: discord.Role | None,
                 estoque: dict, channel: discord.TextChannel):
        super().__init__(timeout=1800)
        self.user = user
        self.role_atendente = role_atendente
        self.estoque = estoque
        self.channel = channel
        self._setup_components()
        self.message = None

    def _setup_components(self):
        self.clear_items()
        self.add_item(AddItemsButton())

        from carrinho import listar_carrinho
        if listar_carrinho(self.user.id):
            self.add_item(RemoveItemSelect(self.user))
            self.add_item(CheckoutButton(
                user=self.user,
                estoque=self.estoque,
                channel=self.channel
            ))
            self.add_item(ClearCartButton(self.user))

    def create_embed(self):
        from carrinho import listar_carrinho
        itens = listar_carrinho(self.user.id)
        embed = discord.Embed(
            title=f"🛒 Carrinho de {self.user.display_name}",
            color=discord.Color.green()
        )

        if itens:
            texto_valores, tem_desconto = calcular_valores(itens, self.user)

            embed.description = "\n".join(
                f"• {item['nome']} x{item['quantidade']} - R${item['preco']:.2f} cada"
                for item in itens
            )

            embed.add_field(
                name="Valores",
                value=texto_valores,
                inline=False
            )

            if not tem_desconto:
                embed.set_footer(text="Torne-se Booster para ganhar 5% de desconto!")
        else:
            embed.description = "Seu carrinho está vazio 😞"

        return embed

class AddItemsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="➕ Adicionar Itens",
            custom_id="add_items_button",
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.response.is_done():
            return
        await interaction.response.defer(ephemeral=True)
        try:
            view = CompraViewPorCategoria(interaction.user, interaction.channel)
            message = await interaction.followup.send(
                "Selecione uma categoria:",
                view=view,
                ephemeral=True,
                wait=True
            )
            view.message = message
        except Exception as e:
            await interaction.followup.send(
                f"❌ Erro ao abrir menu: {str(e)}",
                ephemeral=True
            )

class RemoveItemSelect(discord.ui.Select):
    def __init__(self, user: discord.Member):
        self.user = user
        from carrinho import listar_carrinho
        itens = listar_carrinho(user.id)
        options = [
            discord.SelectOption(
                label=f"{item['nome']} x{item['quantidade']}",
                value=f"{item['nome']}::{item['categoria']}"
            )
            for item in itens
        ]
        super().__init__(
            placeholder="🗑️ Remover item",
            min_values=1,
            max_values=1,
            options=options,
            row=1
        )

    async def callback(self, interaction: discord.Interaction):
        from carrinho import remover_item
        value = self.values[0]
        nome, categoria = value.split("::")
        remover_item(self.user.id, nome, categoria)
        await interaction.response.send_message(f"✅ Removido: {nome}", ephemeral=True)
        if self.view and hasattr(self.view, "message") and self.view.message:
            await self.view.message.edit(embed=self.view.create_embed(), view=self.view)

class CheckoutButton(discord.ui.Button):
    def __init__(self, user: discord.Member, estoque: dict, channel: discord.TextChannel):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="✅ Finalizar Compra",
            custom_id="checkout_button",
            row=2
        )
        self.user = user
        self.estoque = estoque
        self.channel = channel

    async def callback(self, interaction: discord.Interaction):
        from carrinho import listar_carrinho
        itens = listar_carrinho(self.user.id)
        if not itens:
            await interaction.response.send_message("❌ Carrinho vazio!", ephemeral=True)
            return

        texto_valores, _ = calcular_valores(itens, self.user)

        confirm_embed = discord.Embed(
            title="🔎 Confirmar Compra",
            description=(
                f"Tem certeza que deseja finalizar a compra de {len(itens)} itens?\n\n"
                f"{texto_valores}"
            ),
            color=discord.Color.gold()
        )

        confirm_view = ConfirmCheckoutView(
            self.user, self.estoque, self.channel, carrinho_view=self.view
        )
        await interaction.response.send_message(
            embed=confirm_embed,
            view=confirm_view,
            ephemeral=True
        )

class ClearCartButton(discord.ui.Button):
    def __init__(self, user: discord.Member):
        super().__init__(
            style=discord.ButtonStyle.danger,
            label="❌ Esvaziar Carrinho",
            custom_id="clear_cart",
            row=2
        )
        self.user = user

    async def callback(self, interaction: discord.Interaction):
        from carrinho import limpar_carrinho
        limpar_carrinho(self.user.id)
        await interaction.response.send_message("🛒 Carrinho esvaziado!", ephemeral=True)
        if self.view and hasattr(self.view, "message") and self.view.message:
            await self.view.message.edit(embed=self.view.create_embed(), view=self.view)

class ConfirmCheckoutView(discord.ui.View):
    def __init__(self, user: discord.Member, estoque: dict, channel: discord.TextChannel,
                 carrinho_view: 'CarrinhoView' = None):
        super().__init__(timeout=60)
        self.user = user
        self.estoque = estoque
        self.channel = channel
        self.carrinho_view = carrinho_view
        self.responded = False
        self.confirmation_message = None

    async def on_timeout(self):
        if self.confirmation_message:
            try:
                await self.confirmation_message.delete()
            except:
                pass

    @discord.ui.button(label="Confirmar", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.responded:
            return

        self.responded = True
        self.confirmation_message = interaction.message
        button.disabled = True
        button.label = "Processando..."

        try:
            await interaction.response.edit_message(view=self)
            await self._processar_compra(interaction)
        except Exception as e:
            print(f"Erro ao processar compra: {e}")
            await interaction.followup.send(
                "❌ Ocorreu um erro ao processar sua compra.",
                ephemeral=True
            )

    async def _processar_compra(self, interaction: discord.Interaction):
        try:
            from carrinho import listar_carrinho, finalizar_compra
            itens_comprados = listar_carrinho(self.user.id)
            if not itens_comprados:
                await interaction.followup.send("❌ Carrinho vazio!", ephemeral=True)
                return

            texto_valores, tem_desconto = calcular_valores(itens_comprados, self.user)

            await finalizar_compra(self.user.id, interaction.guild, interaction.client)

            embed_usuario = discord.Embed(
                title="🎉 Compra Finalizada!",
                description=(
                        f"✅ Seu pedido foi registrado com sucesso!\n\n"
                        "**Itens Comprados:**\n" +
                        "\n".join(f"• {item['nome']} x{item['quantidade']}" for item in itens_comprados) +
                        f"\n\n{texto_valores}"
                ),
                color=discord.Color.blue()
            )

            if tem_desconto:
                embed_usuario.set_footer(text="✨ Desconto Booster aplicado")
            else:
                embed_usuario.set_footer(text="🔹 Torne-se Booster para ganhar 5% de desconto!")

            embed_pedidos = discord.Embed(
                title=f"📦 NOVO PEDIDO - {self.user.display_name}",
                description=(
                        "\n".join(f"• {item['nome']} x{item['quantidade']} - R${item['preco']:.2f} cada"
                                  for item in itens_comprados) +
                        f"\n\n{texto_valores}"
                ),
                color=discord.Color.green()
            )

            embed_pedidos.add_field(
                name="Cliente",
                value=f"{self.user.mention} (ID: {self.user.id})" +
                      ("\n🐝 **Cliente Booster**" if tem_desconto else ""),
                inline=False
            )

            embed_pedidos.add_field(
                name="Ticket",
                value=f"[Ir para ticket]({self.channel.jump_url})",
                inline=True
            )

            embed_pedidos.set_footer(
                text=f"Pedido realizado em {discord.utils.format_dt(discord.utils.utcnow(), 'F')}"
            )

            pedidos_channel = discord.utils.get(interaction.guild.text_channels, name=CANAL_PEDIDOS)
            if pedidos_channel:
                role = discord.utils.get(interaction.guild.roles, name="♡ ་ ┆𝐄qp ་ 𝐄ntregas")
                if role:
                    await pedidos_channel.send(
                        content=f"{role.mention}",
                        embed=embed_pedidos
                    )
                else:
                    await pedidos_channel.send(
                        content="❌ Role de entregas não encontrada.",
                        embed=embed_pedidos
                    )

                await self.channel.send("Utilize o comando +pg para prosseguir com o pagamento.")

            if self.carrinho_view and self.carrinho_view.message:
                try:
                    await self.carrinho_view.message.edit(
                        embed=self.carrinho_view.create_embed(),
                        view=None
                    )
                except discord.errors.NotFound:
                    pass

            await self.channel.send(embed=embed_usuario)

            try:
                await interaction.delete_original_response()
            except:
                try:
                    await interaction.message.delete()
                except:
                    pass

        except Exception as e:
            print(f"Erro ao processar compra: {e}")
            await interaction.followup.send(
                "❌ Ocorreu um erro ao processar sua compra. Por favor, tente novamente.",
                ephemeral=True
            )

class AddItemsDropdown(discord.ui.Select):
    def __init__(self, estoque: dict):
        options = []
        for categoria, itens in estoque.items():
            for nome, dados in itens.items():
                if dados['quantidade'] > 0:
                    label = f"{nome} ({categoria})"
                    description = f"R$ {dados['preco']:.2f} - {dados['quantidade']} disponíveis"
                    value = f"{nome}::{categoria}::{dados['preco']}"
                    options.append(discord.SelectOption(label=label, description=description, value=value))

        super().__init__(
            placeholder="Selecione um item para adicionar",
            min_values=1,
            max_values=1,
            options=options[:25]
        )
        self.estoque = estoque

    async def callback(self, interaction: discord.Interaction):
        from carrinho import adicionar_item
        valor = self.values[0]
        nome, categoria, preco_str = valor.split("::")
        preco = float(preco_str)
        quantidade = 1

        adicionar_item(interaction.user.id, nome, categoria, preco, quantidade)
        await interaction.response.send_message(
            f"✅ Adicionado ao carrinho: {nome} ({categoria}) x{quantidade}",
            ephemeral=True
        )

        if self.view and hasattr(self.view, "message") and self.view.message:
            await self.view.message.edit(embed=self.view.create_embed(), view=self.view)

# ==================== Purchase Related Views ====================

class CompraViewPorCategoria(discord.ui.View):
    def __init__(self, user: discord.Member, channel: discord.TextChannel):
        super().__init__(timeout=180)
        self.loading = None
        self.user = user
        self.channel = channel
        self.estoque = {}
        self.categorias = []
        self.message = None

        self.categoria_select = discord.ui.Select(
            placeholder="📂 Carregando categorias...",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label="Aguarde...", value="loading")],
            disabled=True
        )
        self.categoria_select.callback = self.categoria_callback
        self.add_item(self.categoria_select)

        asyncio.create_task(self.carregar_estoque())

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass

    async def carregar_estoque(self):
        if self.loading:
            return

        self.loading = True
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(f"{API_URL}/estoque")
                response.raise_for_status()
                self.estoque = response.json()

                print(f"Dados recebidos da API: {self.estoque}")

                if not isinstance(self.estoque, dict):
                    raise ValueError("Resposta da API em formato inválido")

                self.categorias = [c for c in self.estoque.keys() if self.estoque.get(c)]

                if not self.categorias:
                    response = await client.get(f"{API_URL}/estoque")
                    response.raise_for_status()
                    self.estoque = response.json()
                    self.categorias = [c for c in self.estoque.keys() if self.estoque.get(c)]
                    if not self.categorias:
                        raise ValueError("API retornou estoque vazio após tentativa")

                self.categoria_select.options = [
                    discord.SelectOption(label=categoria, value=categoria)
                    for categoria in self.categorias[:25]
                ]
                self.categoria_select.placeholder = "📂 Selecione uma categoria"
                self.categoria_select.disabled = False

        except httpx.RequestError as e:
            self.categoria_select.options = [
                discord.SelectOption(label="Erro de conexão com a API", value="error")
            ]
            self.categoria_select.placeholder = "❌ Clique para recarregar"
            print(f"Erro de conexão com a API: {e}")

        except Exception as e:
            self.categoria_select.options = [
                discord.SelectOption(label=f"Erro: {str(e)[:100]}", value="error")
            ]
            self.categoria_select.placeholder = "❌ Clique para recarregar"
            print(f"Erro ao carregar estoque: {e}")

        finally:
            self.loading = False
            if self.message:
                try:
                    await self.message.edit(view=self)
                except:
                    pass

    async def categoria_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if interaction.data['values'][0] == "error":
            if not self.loading:
                await self.carregar_estoque()
            return

        categoria = interaction.data['values'][0]
        if categoria in ["loading", "error"]:
            return

        view_itens = discord.ui.View(timeout=180)

        select_itens = discord.ui.Select(
            placeholder=f"🔄 Carregando itens de {categoria}...",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label="Carregando...", value="loading")],
            disabled=True
        )

        async def item_callback(interaction: discord.Interaction):
            if select_itens.options[0].value == "loading":
                await interaction.response.send_message("⏳ Itens ainda não carregados", ephemeral=True)
                return

            item_data = interaction.data['values'][0]
            item, preco_str = item_data.split("::")
            preco = float(preco_str)
            quantidade = 1

            if self.estoque[categoria][item]['quantidade'] < quantidade:
                await interaction.response.send_message(
                    "❌ Quantidade indisponível no estoque",
                    ephemeral=True
                )
                return

            from carrinho import adicionar_item
            adicionar_item(self.user.id, item, categoria, preco, quantidade)

            await interaction.response.send_message(
                f"✅ {item} adicionado ao carrinho!",
                ephemeral=True
            )

            from views import CarrinhoView
            view = CarrinhoView(
                user=self.user,
                role_atendente=None,
                estoque=self.estoque,
                channel=self.channel
            )

            mensagem_encontrada = None
            async for msg in self.channel.history(limit=50):
                if msg.author == self.channel.guild.me and msg.embeds:
                    if msg.embeds[0].title and f"Carrinho de {self.user.display_name}" in msg.embeds[0].title:
                        mensagem_encontrada = msg
                        break

            if mensagem_encontrada:
                await mensagem_encontrada.edit(embed=view.create_embed(), view=view)
            else:
                msg = await interaction.followup.send(embed=view.create_embed(), view=view, ephemeral=True)
                view.message = msg

        select_itens.callback = item_callback
        view_itens.add_item(select_itens)

        try:
            itens = [
                (item, dados)
                for item, dados in self.estoque[categoria].items()
                if dados['quantidade'] > 0
            ]

            select_itens.options = [
                discord.SelectOption(
                    label=item,
                    description=f"R${dados['preco']:.2f} | {dados['quantidade']}x",
                    value=f"{item}::{dados['preco']}"
                )
                for item, dados in itens[:25]
            ]
            select_itens.placeholder = f"🛍️ Selecione um item de {categoria}"
            select_itens.disabled = False

        except Exception as e:
            select_itens.options = [
                discord.SelectOption(label=f"Erro: {str(e)[:100]}", value="error")
            ]
            select_itens.placeholder = "❌ Falha ao carregar itens"

        await interaction.followup.send(
            f"Itens disponíveis em {categoria}:",
            view=view_itens,
            ephemeral=True
        )

# ==================== Price Related Views ====================

class PrecoDropdownView(discord.ui.View):
    def __init__(self, categoria: str, estoque: dict):
        super().__init__(timeout=None)
        self.add_item(PrecoDropdown(categoria, estoque))

class PrecoDropdown(discord.ui.Select):
    def __init__(self, categoria: str, estoque: dict):
        self.categoria = categoria.upper()
        self.estoque = estoque
        options = []

        try:
            response = httpx.get(f"{API_URL}/estoque", timeout=10.0)
            estoque = response.json()

            for item, dados in estoque.get(self.categoria, {}).items():
                if dados["quantidade"] > 0:
                    options.append(
                        discord.SelectOption(
                            label=item,
                            description=f"R${dados['preco']:.2f} | {dados['quantidade']}x",
                            value=item
                        )
                    )

            if not options:
                options = [discord.SelectOption(label="❌ Nenhum item disponível", value="none")]

        except Exception as e:
            options = [discord.SelectOption(label="❌ Erro ao carregar estoque", value="erro")]
            print(f"[Dropdown Preços] Erro: {e}")

        super().__init__(
            placeholder=f"🍭 {self.categoria}",
            min_values=1,
            max_values=1,
            options=options[:25]
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"ℹ️ **{self.values[0]}** está disponível na categoria **{self.categoria}**.",
            ephemeral=True
        )