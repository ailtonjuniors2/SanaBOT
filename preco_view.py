import discord
import httpx
from config import API_URL

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
