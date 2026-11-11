"""Compõe as imagens de pote dos produtos aprovados que ainda não têm imagem.

Roda no GitHub Actions (.github/workflows/compor-imagens.yml). Lê a lista no Supabase
(função sitemedicinal_imagens_pendentes: só link e nome do produto, nada de preço ou dado pessoal)
e grava vtex/<link_id>.jpg. A esteira do n8n confere o arquivo publicado e preenche a ficha.
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from compor_imagem import compor  # noqa: E402

API = "https://mwhlnlqxtudcgbggkqud.supabase.co/rest/v1/rpc/sitemedicinal_imagens_pendentes"
# Chave publicável (pública por definição; a mesma usada no portal). Só executa a função acima.
CHAVE = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_Mko3fotqVGnCCknOJ6RODQ_rqXh_X8b")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELO = os.path.join(BASE, "ferramentas", "modelo")

req = urllib.request.Request(API, data=b"{}", method="POST",
                             headers={"apikey": CHAVE, "Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=30) as r:
    pendentes = json.load(r)

feitas = 0
for p in pendentes:
    link = p["link_id"]
    if not link or "/" in link or ".." in link:
        print("ignorado (link inválido):", link)
        continue
    saida = os.path.join(BASE, "vtex", f"{link}.jpg")
    if os.path.exists(saida):
        print("já existe:", link)
        continue
    compor(os.path.join(MODELO, "poteCapsula.jpeg"), os.path.join(MODELO, "fontes"), p["nome"], saida)
    feitas += 1
    print("composta:", link)
print(f"{feitas} imagem(ns) nova(s) de {len(pendentes)} pendente(s)")
