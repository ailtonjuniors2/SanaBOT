import discord
from carrinho import adicionar_item
import httpx
import asyncio
from config import API_URL


class CompraViewPorCategoria(discord.ui.View):
    def __init__(self, user: discord.Member, channel: discord.TextChannel):
        super().__init__(timeout=180)  # Aumentado para 3 minutos
        self.loading = None
        self.user = user
        self.channel = channel
        self.estoque = {}
        self.categorias = []
        self.message = None

        # Dropdown de categorias
        self.categoria_select = discord.ui.Select(
            placeholder="📂 Carregando categorias...",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label="Aguarde...", value="loading")],
            disabled=True
        )
        self.categoria_select.callback = self.categoria_callback
        self.add_item(self.categoria_select)

        # Inicia carregamento
        asyncio.create_task(self.carregar_estoque())

    async def on_timeout(self):
        """Limpa a view quando o tempo expira"""
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

                # Debug: Mostrar o que foi recebido da API
                print(f"Dados recebidos da API: {self.estoque}")

                if not isinstance(self.estoque, dict):
                    raise ValueError("Resposta da API em formato inválido")

                self.categorias = [c for c in self.estoque.keys() if self.estoque.get(c)]

                if not self.categorias:
                    # Tenta recarregar uma vez mais antes de dar erro
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
        """Modificado para evitar recursão"""
        await interaction.response.defer()

        if interaction.data['values'][0] == "error":
            # Recarrega apenas se clicar no erro
            if not self.loading:
                await self.carregar_estoque()
            return

        categoria = interaction.data['values'][0]
        if categoria in ["loading", "error"]:
            return

        # Cria novo dropdown para itens
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

            # Verifica estoque antes de adicionar ao carrinho
            if self.estoque[categoria][item]['quantidade'] < quantidade:
                await interaction.response.send_message(
                    "❌ Quantidade indisponível no estoque",
                    ephemeral=True
                )
                return

            # Adiciona apenas ao carrinho local
            adicionar_item(self.user.id, item, categoria, preco, quantidade)

            await interaction.response.send_message(
                f"✅ {item} adicionado ao carrinho!",
                ephemeral=True
            )

            # Atualiza a mensagem do carrinho
            from carrinho_view import CarrinhoView
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

        # Carrega itens da categoria selecionada
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