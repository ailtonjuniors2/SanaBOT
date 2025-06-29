import discord
import httpx
from config import API_URL
from utils import atualizar_dropdowns_estoque


carrinhos = {}

def adicionar_item(user_id: int, nome: str, categoria: str, preco: float, quantidade: int = 1):
    if user_id not in carrinhos:
        carrinhos[user_id] = []

    for item in carrinhos[user_id]:
        if item['nome'] == nome and item['categoria'] == categoria:
            item['quantidade'] += quantidade
            return carrinhos[user_id]

    carrinhos[user_id].append({
        "nome": nome,
        "categoria": categoria,
        "preco": preco,
        "quantidade": quantidade
    })
    return carrinhos[user_id]

def remover_item(user_id: int, nome: str, categoria: str = None):
    if user_id in carrinhos:
        for item in carrinhos[user_id]:
            if item['nome'] == nome and (categoria is None or item['categoria'] == categoria):
                carrinhos[user_id].remove(item)
                break
    return carrinhos.get(user_id, [])

def listar_carrinho(user_id: int) -> list:
    return carrinhos.get(user_id, [])

def limpar_carrinho(user_id: int):
    if user_id in carrinhos:
        carrinhos[user_id] = []
    return carrinhos.get(user_id, [])

async def finalizar_compra(user_id: int, guild: discord.Guild, bot) -> list:
    itens = listar_carrinho(user_id)
    if not itens:
        return []

    async with httpx.AsyncClient(timeout=10.0) as client:
        for item in itens:
            try:
                payload = {
                    "categoria": item["categoria"],
                    "item": item["nome"],
                    "quantidade": item["quantidade"]
                }

                response = await client.put(f"{API_URL}/estoque/comprar", json=payload)
                response.raise_for_status()

            except httpx.HTTPStatusError as e:
                print(f"[❌ ERRO] Falha na requisição: {e.response.status_code} - {e.response.text}")
                raise
            except httpx.RequestError as e:
                print(f"[❌ ERRO] Falha de conexão: {str(e)}")
                raise
            except Exception as e:
                print(f"[❌ ERRO] Erro inesperado: {str(e)}")
                raise

    limpar_carrinho(user_id)
    await atualizar_dropdowns_estoque(bot, guild)
    return itens