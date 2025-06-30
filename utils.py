import discord
import httpx
import json
import os
from config import API_URL

CAMINHO_ESTOQUE = "estoque.json"

# ==================== Stock Utility Functions ====================

def carregar_estoque() -> dict:
    if not os.path.exists(CAMINHO_ESTOQUE):
        with open(CAMINHO_ESTOQUE, "w") as f:
            json.dump({}, f)

    with open(CAMINHO_ESTOQUE, "r") as f:
        return json.load(f)

def salvar_estoque(dados: dict) -> None:
    with open(CAMINHO_ESTOQUE, "w") as f:
        json.dump(dados, f, indent=4)

def remover_item(categoria: str, item: str) -> bool:
    estoque = carregar_estoque()
    categoria = categoria.upper()

    if categoria in estoque and item in estoque[categoria]:
        estoque[categoria][item] -= 1

        if estoque[categoria][item] <= 0:
            del estoque[categoria][item]

        salvar_estoque(estoque)
        return True
    return False

def adicionar_item(categoria: str, item: str, quantidade: int = 1) -> bool:
    estoque = carregar_estoque()
    categoria = categoria.upper()

    if categoria not in estoque:
        estoque[categoria] = {}

    if item in estoque[categoria]:
        estoque[categoria][item] += quantidade
    else:
        estoque[categoria][item] = quantidade

    salvar_estoque(estoque)
    return True

def listar_estoque() -> dict:
    return carregar_estoque()

# ==================== Discord Utility Functions ====================

async def atualizar_dropdowns_estoque(bot: discord.ext.commands.Bot, guild: discord.Guild):
    canais_categorias = {
        "DRESS TO IMPRESS": "﹙💋﹚⋆﹒𝐃𝐓𝐈﹒𝐏reços﹒",
        "ROBUX": "﹙🕹️﹚⋆﹒𝐑𝐨𝐛𝐮𝐱﹒𝐏reços﹒",
        "GROW A GARDEN": "﹙🌱﹚⋆﹒𝐆𝐫𝐨𝐰﹒𝐚﹒𝐆𝐚𝐫𝐝𝐞𝐧﹒𝐏reços﹒"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/estoque")
            estoque = response.json()

        for categoria, canal_nome in canais_categorias.items():
            canal = discord.utils.get(guild.text_channels, name=canal_nome)
            if not canal:
                print(f"[ATUALIZAÇÃO] Canal não encontrado: {canal_nome}")
                continue

            async for msg in canal.history(limit=20):
                if msg.author == bot.user and msg.components:
                    await msg.delete()

            embed = discord.Embed(
                title=f"⊱ <:emoji_59:1388880400558063636> ⸝⸝ Itens Disponíveis - {categoria}",
                description="<:03_topico:1387904528929521737> Selecione um item abaixo para visualizar o preço e a quantidade atual em estoque .ᐟ",
                color=discord.Color.blue()
            )

            from views import PrecoDropdownView
            view = PrecoDropdownView(categoria, estoque)
            await canal.send(embed=embed, view=view)

    except Exception as e:
        print(f"[ERRO] Falha ao atualizar dropdowns de preço: {e}")