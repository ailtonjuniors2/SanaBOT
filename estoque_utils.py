import json
import os

CAMINHO_ESTOQUE = "estoque.json"

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
            del estoque[categoria][item]  # remove o item se acabou

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
