import discord
import os
from dotenv import load_dotenv

load_dotenv()

# Configurações
BOT_PREFIX = os.getenv("BOT_PREFIX")
API_URL = os.getenv("API_URL")
ROLE_ATENDENTE_ID = int(os.getenv("ROLE_ATENDENTE_ID", 0))
CANAL_PEDIDOS = os.getenv("CANAL_PEDIDOS")
ROLE_ATENDENTE = os.getenv("ROLE_ATENDENTE")
ROLE_BOOSTER = os.getenv("ROLE_BOOSTER")


def init_config(guild: discord.Guild) -> bool:
    """Configura a role de atendente com fallback se não for encontrada"""
    global ROLE_ATENDENTE

    try:
        # Tenta encontrar a role pelo ID
        ROLE_ATENDENTE = guild.get_role(ROLE_ATENDENTE_ID)

        # Se não encontrou pelo ID, tenta pelo nome
        if not ROLE_ATENDENTE:
            ROLE_ATENDENTE = discord.utils.get(guild.roles, name="୨୧ ་𝐀tendente⸝⸝")

        if not ROLE_ATENDENTE:
            print(f"⚠️ Role de atendente não encontrada (ID: {ROLE_ATENDENTE_ID})")
            print("Roles disponíveis:", [f"{r.name} (ID: {r.id})" for r in guild.roles])
            return False

        return True

    except Exception as e:
        print(f"❌ Erro na configuração: {str(e)}")
        return False


def get_pedidos_channel(guild: discord.Guild) -> discord.TextChannel | None:
    """Obtém o canal de pedidos com fallback"""
    try:
        channel = discord.utils.get(guild.text_channels, name=CANAL_PEDIDOS)
        if not channel:
            channel = discord.utils.get(guild.text_channels, name="pedidos")
        return channel
    except Exception as e:
        print(f"❌ Erro ao buscar canal de pedidos: {str(e)}")
        return None