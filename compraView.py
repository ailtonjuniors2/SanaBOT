import discord
from carrinho import adicionar_item
import httpx
import asyncio
from config import API_URL


class CompraViewPorCategoria(discord.ui.View):
    def __init__(self, user: discord.Member, channel: discord.TextChannel):
        super().__init__(timeout=180)
        self.user = user
        self.channel = channel
        self.estoque = {}
        self.message = None
        asyncio.create_task(self.carregar_estoque())

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass

    def criar_callback(self, categoria: str):
        async def callback(interaction: discord.Interaction):
            await self.mostrar_itens(interaction, categoria)
        return callback

    async def carregar_estoque(self):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(f"{API_URL}/estoque")
                response.raise_for_status()
                self.estoque = response.json()

            categorias = [c for c in self.estoque.keys() if self.estoque.get(c)]

            if not categorias:
                raise ValueError("Nenhuma categoria disponível no estoque")

            self.clear_items()

            for categoria in categorias[:5]:
                button = discord.ui.Button(label=categoria, style=discord.ButtonStyle.primary)
                button.callback = self.criar_callback(categoria)
                self.add_item(button)

            if self.message:
                await self.message.edit(view=self)

        except Exception as e:
            print(f"Erro ao carregar estoque: {e}")
            self.clear_items()
            erro_button = discord.ui.Button(label="Erro ao carregar", style=discord.ButtonStyle.danger, disabled=True)
            self.add_item(erro_button)
            if self.message:
                await self.message.edit(view=self)

    async def mostrar_itens(self, interaction: discord.Interaction, categoria: str):
        view_itens = discord.ui.View(timeout=180)
        try:
            itens = [
                (item, dados)
                for item, dados in self.estoque[categoria].items()
                if dados['quantidade'] > 0
            ]

            if not itens:
                await interaction.response.send_message("❌ Nenhum item disponível nessa categoria.", ephemeral=True)
                return

            select_itens = discord.ui.Select(
                placeholder=f"🛍️ Selecione um item de {categoria}",
                min_values=1,
                max_values=1,
                options=[
                    discord.SelectOption(
                        label=item,
                        description=f"R${dados['preco']:.2f} | {dados['quantidade']}x",
                        value=f"{item}::{dados['preco']}"
                    ) for item, dados in itens[:25]
                ]
            )

            async def item_callback(interaction: discord.Interaction):
                item_data = interaction.data['values'][0]
                item, preco_str = item_data.split("::")
                preco = float(preco_str)
                quantidade = 1

                if self.estoque[categoria][item]['quantidade'] < quantidade:
                    await interaction.response.send_message("❌ Estoque insuficiente.", ephemeral=True)
                    return

                adicionar_item(self.user.id, item, categoria, preco, quantidade)
                await interaction.response.send_message(f"✅ {item} adicionado ao carrinho!", ephemeral=True)

                # Atualiza o carrinho
                from carrinho_view import CarrinhoView
                carrinho_view = CarrinhoView(user=self.user, role_atendente=None, estoque=self.estoque, channel=self.channel)

                mensagem_encontrada = None
                async for msg in self.channel.history(limit=50):
                    if msg.author == self.channel.guild.me and msg.embeds:
                        if msg.embeds[0].title and f"Carrinho de {self.user.display_name}" in msg.embeds[0].title:
                            mensagem_encontrada = msg
                            break

                if mensagem_encontrada:
                    await mensagem_encontrada.edit(embed=carrinho_view.create_embed(), view=carrinho_view)
                else:
                    msg = await interaction.followup.send(embed=carrinho_view.create_embed(), view=carrinho_view, ephemeral=True)
                    carrinho_view.message = msg

            select_itens.callback = item_callback
            view_itens.add_item(select_itens)

            await interaction.response.send_message(
                f"Itens disponíveis em **{categoria}**:",
                view=view_itens,
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao carregar itens: {e}", ephemeral=True)
