import discord
from carrinho import listar_carrinho, limpar_carrinho, remover_item, finalizar_compra, adicionar_item
import discord.utils
from config import ROLE_BOOSTER, CANAL_PEDIDOS


from typing import Tuple


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

        if listar_carrinho(self.user.id):
            self.add_item(RemoveItemSelect(self.user))
            self.add_item(CheckoutButton(
                user=self.user,
                estoque=self.estoque,
                channel=self.channel
            ))
            self.add_item(ClearCartButton(self.user))

    def create_embed(self):
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


# python
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
            view = self._criar_compra_view(interaction.user, interaction.channel)
            message = await interaction.followup.send(
                "Selecione uma categoria:",
                view=view,
                ephemeral=True,
                wait=True
            )
            view.message = message
        except Exception as e:
            print(f"Erro ao abrir menu: {e}")  # Log no terminal
            await interaction.followup.send(
                f"❌ Erro ao abrir menu: {str(e)}",
                ephemeral=True
            )

    def _criar_compra_view(self, user: discord.Member, channel: discord.TextChannel):
        from compraView import CompraViewPorCategoria
        return CompraViewPorCategoria(user, channel)


class RemoveItemSelect(discord.ui.Select):
    def __init__(self, user: discord.Member):
        self.user = user
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
            itens_comprados = listar_carrinho(self.user.id)
            if not itens_comprados:
                await interaction.followup.send("❌ Carrinho vazio!", ephemeral=True)
                return

            texto_valores, tem_desconto = calcular_valores(itens_comprados, self.user)

            # Processar compra na API
            await finalizar_compra(self.user.id, interaction.guild, interaction.client)

            # Mensagem para o usuário
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

            # Mensagem para o canal de pedidos
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

            # Enviar para o canal de pedidos
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

            # Atualizar mensagem do carrinho
            if self.carrinho_view and self.carrinho_view.message:
                try:
                    await self.carrinho_view.message.edit(
                        embed=self.carrinho_view.create_embed(),
                        view=None
                    )
                except discord.errors.NotFound:
                    pass

            # Enviar confirmação para o usuário
            await self.channel.send(embed=embed_usuario)

            # Apagar mensagem de confirmação original
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