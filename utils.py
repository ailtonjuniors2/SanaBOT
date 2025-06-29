import discord
import httpx
from config import API_URL
from preco_view import PrecoDropdownView

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

            # Apaga mensagens antigas
            async for msg in canal.history(limit=20):
                if msg.author == bot.user and msg.components:
                    await msg.delete()

            # Envia mensagem atualizada
            embed = discord.Embed(
                title=f"                  ︶ ⏝ ︶ <:03_laco_amarelo:1387876036494233841> ︶ ⏝ ︶ \n"
                      f"⊱ <:emoji_59:1388880400558063636> ⸝⸝ Itens Disponíveis - {categoria}",
                description="<:03_topico:1387904528929521737> Selecione um item abaixo para visualizar o preço e a quantidade atual em estoque .ᐟ",
                color=discord.Color.blue()
            )

            view = PrecoDropdownView(categoria, estoque)  # Adicionar estoque
            await canal.send(embed=embed, view=view)

    except Exception as e:
        print(f"[ERRO] Falha ao atualizar dropdowns de preço: {e}")
