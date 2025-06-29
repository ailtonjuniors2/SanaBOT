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

