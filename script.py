import os
from config import API_URL, BOT_PREFIX
import discord
from discord.ext import commands
from ticket_view import TicketView
from compraView import CompraViewPorCategoria
import httpx
import asyncio
from preco_view import PrecoDropdownView
from botao_ticket_view import CriarTicketView
from fastapi import FastAPI
import threading
import uvicorn

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

port = int(os.environ.get("PORT", 8000))
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)



@bot.event
async def on_ready():
    for guild in bot.guilds:
        print(f"Bot logado como {bot.user}")

    # Verifica se o canal de pedidos existe
    pedidos_channel = discord.utils.get(bot.get_all_channels(), name="﹙📝﹚⋆﹒𝐏edidos﹒")
    if not pedidos_channel:
        print("⚠️ Canal de pedidos não encontrado! Certifique-se de criar o canal '﹙📝﹚⋆﹒𝐏edidos﹒'")

# Comando para criar ticket com menu de categorias (botões)
@bot.command()
async def ticket(ctx):
    """
    Cria um ticket de atendimento com acesso ao carrinho de compras
    """
    guild = ctx.guild
    user = ctx.author

    # Verifica se o usuário já tem um ticket aberto
    existing_ticket = discord.utils.get(
        guild.text_channels,
        name=f"ticket-{user.name}"
    )

    if existing_ticket:
        await ctx.send(
            f"{user.mention}, você já tem um ticket aberto em {existing_ticket.mention}",
            delete_after=15
        )
        return

    # Configura as permissões do canal
    role_atendente = discord.utils.get(guild.roles, name="୨୧ ་ 𝐀tendente⸝⸝")
    if not role_atendente:
        await ctx.send("❌ A role 'Atendente' não foi encontrada!")
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

    # Cria o canal de ticket
    try:
        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            overwrites=overwrites,
            topic=f"Ticket de {user.display_name} | ID: {user.id}",
            position=0
        )
    except Exception as e:
        await ctx.send(f"❌ Erro ao criar ticket: {e}")
        return

    print(f"Novo ticket criado para {user.name} - Canal: {ticket_channel.name}")

    # Cria a mensagem inicial do ticket
    embed = discord.Embed(
        title=f"🎫 TICKET DE ATENDIMENTO",
        description=(
            f"Olá {user.mention}, seja bem-vindo ao seu ticket!\n\n"
            f"🔹 **Um atendente virá te atender!**\n\n"
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

    # Cria a view com os botões (SEM criar o carrinho automaticamente)
    view = TicketView(ctx.guild)  # Usa a classe TicketView que definimos anteriormente

    # Envia a mensagem inicial
    try:
          # Substitua pelo ID real
        await ticket_channel.send(
            content=f"{user.mention} {role_atendente.mention}",
            embed=embed,
            view=view
        )

        # Mensagem de confirmação
        confirm_embed = discord.Embed(
            description=f"✅ Ticket criado com sucesso em {ticket_channel.mention}",
            color=discord.Color.green()
        )
        await ctx.send(embed=confirm_embed, delete_after=15)


    except ValueError as e:

        await ctx.send(f"❌ {str(e)}", delete_after=15)

    except Exception as e:

        await ctx.send(f"❌ Erro ao criar ticket: {str(e)}", delete_after=15)

        print(f"Erro no comando ticket: {type(e).__name__}: {e}")

# Handler para os botões do ticket
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return

    try:
        if interaction.data.get('custom_id') == "abrir_carrinho":
            # Usar bot existente
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{API_URL}/estoque")
                estoque = response.json()

            from carrinho_view import CarrinhoView
            view = CarrinhoView(
                user=interaction.user,
                role_atendente=discord.utils.get(interaction.guild.roles, name="୨୧ ་ 𝐀tendente⸝⸝"),
                estoque=estoque,
                channel=interaction.channel
            )

            # Resposta única garantida
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=view.create_embed(),
                    view=view,
                    ephemeral=True
                )
    except Exception as e:
        print(f"Erro crítico: {type(e).__name__}: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ Ocorreu um erro inesperado",
                ephemeral=True
            )

# Comando para adicionar item manualmente (só atendente)
@bot.command()
@commands.has_role("୨୧ ་𝐀tendente⸝⸝")
async def adicionar(ctx, categoria: str, quantidade: int, preco: float, *, item: str):
    dados = {
        "categoria": categoria,
        "item": item,
        "quantidade": quantidade,
        "preco": preco
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{API_URL}/estoque/adicionar", json=dados)
            if response.status_code == 200:
                await ctx.send(f"✅ {quantidade}x {item} adicionado à {categoria} por R$ {preco:.2f}")
            else:
                await ctx.send(f"❌ Erro: {response.json().get('detail', 'Unknown error')}")
    except Exception as e:
        await ctx.send(f"❌ Erro de conexão: {str(e)}")

# Comando para fechar ticket (só atendente, só dentro do canal ticket)
@bot.command()
@commands.has_role("୨୧ ་ 𝐀tendente⸝⸝")
async def fechar(ctx):
    """Fecha o ticket e todos os subcanais relacionados"""
    if not ctx.channel.name.startswith("ticket-"):
        await ctx.send("❌ Este comando só funciona em canais de ticket!")
        return

    try:
        # Extrai o nome do usuário do nome do canal
        username = ctx.channel.name.split('ticket-')[-1].split('-')[0]

        # Encontra e deleta todos os canais de carrinho relacionados
        deleted_channels = 0
        for channel in ctx.guild.text_channels:
            if channel.name.startswith(f"🛒carrinho-{username}"):
                try:
                    await channel.delete()
                    deleted_channels += 1
                except discord.Forbidden:
                    print(f"Sem permissão para deletar {channel.name}")
                except discord.HTTPException:
                    print(f"Erro ao deletar {channel.name}")

        # Feedback para o usuário
        msg = await ctx.send(f"🚪 Fechando ticket e {deleted_channels} canais de carrinho...")
        await asyncio.sleep(2)

        # Deleta o ticket principal
        await ctx.channel.delete()

    except Exception as e:
        print(f"ERRO: {type(e).__name__}: {e}")
        await ctx.send("❌ Ocorreu um erro ao fechar o ticket!")

# Comando para mostrar estoque (só atendente)
@bot.command()
@commands.has_role("୨୧ ་ 𝐀tendente⸝⸝")
async def estoque(ctx):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/estoque")
            estoque_data = response.json()

        if not estoque_data:
            await ctx.send("❌ Nenhum item no estoque.")
            return

        embed = discord.Embed(title="📦 ESTOQUE ATUAL", color=discord.Color.blue())

        for categoria, itens in estoque_data.items():
            if not itens:
                embed.add_field(name=f"**🔹 {categoria}**", value="Sem itens", inline=False)
                continue

            # Verifica se é a estrutura nova (com dicionário) ou antiga (valor direto)
            primeiro_item = next(iter(itens.values()))
            if isinstance(primeiro_item, dict):
                # Estrutura nova com preços: {"item": {"quantidade": X, "preco": Y}}
                itens_text = "\n".join(
                    f"• {item} — {dados['quantidade']}x (R$ {dados.get('preco', '?')})"
                    for item, dados in itens.items()
                )
            else:
                # Estrutura antiga: {"item": quantidade}
                itens_text = "\n".join(
                    f"• {item} — {quantidade}x"
                    for item, quantidade in itens.items()
                )

            embed.add_field(
                name=f"**🔹 {categoria}**",
                value=itens_text,
                inline=False
            )

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Erro ao acessar estoque: {str(e)}")
        print(f"Erro no comando estoque: {type(e).__name__}: {e}")

# Comando para iniciar compra mostrando dropdown de uma categoria
@bot.command()
async def comprar(ctx, categoria: str):
    categoria = categoria.upper()

    # Verifica se o comando foi usado em um ticket
    if not ctx.channel.name.startswith("ticket-"):
        await ctx.send("❌ Este comando só pode ser usado em tickets!", delete_after=10)
        return

    # Cria a view de compra
    view = CompraViewPorCategoria(ctx.author, ctx.channel)  # Parâmetros corretos


    await ctx.send(
        f"Selecione os itens da categoria {categoria}:",
        view=view,
        delete_after=60
    )
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/estoque")
            estoque = response.json()

        if categoria not in estoque or not estoque[categoria]:
            await ctx.send(f"❌ Categoria {categoria} não encontrada ou sem itens em estoque.")
            return

        await ctx.send(f"Selecione os itens para seu carrinho na categoria {categoria}:", view=view)

    except httpx.RequestError as e:
        await ctx.send("❌ Erro ao se conectar à API.")
        print(f"Erro de conexão: {e}")

    def get_user_from_channel(channel_name: str):
        """Extrai o nome de usuário do nome do canal"""
        if channel_name.startswith("ticket-"):
            return channel_name.replace("ticket-", "")
        elif channel_name.startswith("carrinho-"):
            return channel_name.replace("carrinho-", "")
        return None

@bot.command()
@commands.has_role("୨୧ ་ 𝐀tendente⸝⸝")
async def enviar_precos(ctx):
    """
    Envia mensagens fixas com os dropdowns nos canais de preços
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/estoque")
            estoque = response.json()

        canais_categorias = {
            "DRESS TO IMPRESS": "﹙💋﹚⋆﹒𝐃𝐓𝐈﹒𝐏reços﹒",
            "ROBUX": "﹙🕹️﹚⋆﹒𝐑𝐨𝐛𝐮𝐱﹒𝐏reços﹒",
            "GROW A GARDEN": "﹙🌱﹚⋆﹒𝐆𝐫𝐨𝐰﹒𝐚﹒𝐆𝐚𝐫𝐝𝐞𝐧﹒𝐏reços﹒"
        }

        for categoria, canal_nome in canais_categorias.items():
            canal = discord.utils.get(ctx.guild.text_channels, name=canal_nome)
            if not canal:
                await ctx.send(f"❌ Canal não encontrado: {canal_nome}")
                continue

            view = PrecoDropdownView(categoria, estoque)
            embed = discord.Embed(
                title=f"⊱ <:emoji_59:1388880400558063636> ⸝⸝ Itens Disponíveis - {categoria}",
                description="<:03_topico:1387904528929521737> Selecione um item abaixo para visualizar o preço e a quantidade atual em estoque .ᐟ",
                color=discord.Color.blue()
            )

            await canal.send(embed=embed, view=view)
            await asyncio.sleep(1)

        await ctx.send("✅ Mensagens de preços enviadas com sucesso.")

    except Exception as e:
        print(f"Erro ao enviar preços: {e}")
        await ctx.send("❌ Ocorreu um erro ao enviar os preços.")

@bot.command()
@commands.has_role("୨୧ ་ 𝐀tendente⸝⸝")
async def enviar_botao_ticket(ctx):
    canal_nome = "﹙🏷️﹚⋆﹒𝐏eça﹒𝐀qui﹒"
    canal = discord.utils.get(ctx.guild.text_channels, name=canal_nome)

    if not canal:
        await ctx.send(f"❌ Canal {canal_nome} não encontrado.")
        return

    embed = discord.Embed(
        title="˚.<:03carrinho:1388608448328896612> ⊹ ࣪ ˖ Abrir um ticket",
        description=(
            "Clique no botão abaixo para abrir um ticket de atendimento.\n"
            "Nossa equipe irá te ajudar com dúvidas, compras ou suporte técnico."
        ),
        color=discord.Color.green()
    )

    await canal.send(embed=embed, view=CriarTicketView(bot))
    await ctx.send("✅ Botão de ticket enviado com sucesso.")

async def on_interaction_error(interaction: discord.Interaction, error: Exception):
    print(f"Erro na interação: {error}")
    if not interaction.response.is_done():
        await interaction.response.send_message(
            "❌ Ocorreu um erro ao processar sua ação",
            ephemeral=True
        )

@bot.event
async def on_message(message):
    if message.author == bot.user:  # Ignora mensagens do próprio bot
        return
    await bot.process_commands(message)  # Processa comandos normalmente

app = FastAPI()

@app.get("/")
def home():
    return {"status": "Bot is running"}

def run_api():
    """Roda o FastAPI em uma thread separada."""
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

# Inicia a API web em segundo plano
threading.Thread(target=run_api, daemon=True).start()

# Inicia o bot Discord (SEM parâmetro 'port'!)
bot.run(os.getenv('DISCORD_TOKEN'))