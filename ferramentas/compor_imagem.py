"""Composição da imagem de embalagem (padrão Medicinal aprovado em 18/06/2026).

Composição programática em Pillow sobre o mockup branco. Não é geração por IA.
Fonte da verdade: SOP "descricaoProdutos" (Notion), seção "Padrão do campo cover_image_url".

Uso:
    python3 scripts/compor_imagem.py --mockup poteCapsula.jpeg --fontes DIR --titulo "Terasen" --saida terasen.jpg
"""
import argparse
import re

from PIL import Image, ImageDraw, ImageFont

# Geometria do poteCapsula (1600x1600), mapeada por análise de cor
GEOMETRIA = {
    "poteCapsula": {
        "centro_x": 796,
        "largura_max": 500,          # alvo confortável (rótulo vai de 506 a 1086 = 580 px)
        "titulo_y": (810, 1135),     # faixa do título
        "tarja_y": (1148, 1275),     # tarja azul RGB(24,104,158)
    },
    # vidroAmbarContaGotas: original 4000x5000 (retrato). Enquadrado num quadrado de 4400 px
    # (centro x 2000, topo y 350) e reduzido para 1600 (escala 0,3636). Mapeado em 19/10/2026:
    # rótulo x 1291-2708 / y 2380-3999, logo y 2476-2590, tarja y 4000-4334.
    "vidroAmbarContaGotas": {
        "preparo": {"centro_x": 2000, "lado": 4400, "topo": 350},
        "centro_x": 797,
        "largura_max": 440,          # rótulo de 542 a 1058 = 516 px
        "titulo_y": (847, 1305),     # abaixo do logo, acima da tarja
        "tarja_y": (1327, 1449),
    },
}


def abre_mockup(path, g):
    """Abre o mockup; se a geometria pedir, enquadra num quadrado branco e reduz para 1600."""
    img = Image.open(path).convert("RGB")
    pre = g.get("preparo")
    if not pre:
        return img
    lado = pre["lado"]
    quadro = Image.new("RGB", (lado, lado), (255, 255, 255))
    x0 = pre["centro_x"] - lado // 2
    quadro.paste(img, (-x0, -pre["topo"]))
    return quadro.resize((1600, 1600), Image.LANCZOS)

# Dose (regra criada em 19/10/2026): linha própria abaixo de cada ativo, alinhada à direita
# pela linha mais larga do ativo, Poppins SemiBold em tamanho FIXO, azul da tarja.
COR_DOSE = (24, 104, 158)
TAM_DOSE = 36                # igual em todos os rótulos

# Tarja (regra de 19/10/2026): "Contém N doses" (ou cápsulas / ml / g), uma linha, centralizada na tarja.
# Substitui o aviso "Siga orientações de um / profissional habilitado".
# "Contém" e a unidade em fonte menor; o número (volume) maior e em negrito, mesma linha de base.
COR_TARJA_TXT = (232, 242, 250)
TAM_TARJA_MENOR = 28      # Poppins Medium
TAM_TARJA_NUMERO = 56     # Poppins Bold
# conteúdo no fim do nome: "- 30 Doses", "90 cápsulas", "60ml", "100 g"
RE_CONT = re.compile(r"\s*-?\s*(\d+(?:[.,]\d+)?)\s*(doses?|c[aá]psulas?|caps|ml|g)\s*$", re.I)


def texto_conteudo(n, unidade):
    """Devolve as partes da tarja: (antes, número, depois)."""
    u = unidade.lower()
    if u.startswith("dose"):
        return ("Contém ", n, " doses")
    if u.startswith(("cáp", "cap")):
        return ("Contém ", n, " cápsulas")
    return ("Contém ", n, u)                   # ml / g colados ao número


RE_DOSE = re.compile(r"^(.*?\S)\s+(\d+(?:[.,]\d+)?\s*(?:(?:mg|mcg|µg|g|ui|ml|bi|ufc)\b|%).*)$", re.I)


def separa_ativos(titulo):
    """Cada ativo em linha própria: remove os conectores 'com', '+' e 'e'.
    Devolve [(nome, dose)], com a dose lida do fim de cada ativo ("Ômega 3 1000mg" -> ("Ômega 3", "1000mg"))."""
        # conectores só em minúsculas: o "E" maiúsculo é de vitamina ("Vitamina E 400UI")
    partes = re.split(r"\s*\+\s*|\s+com\s+", titulo.strip())
    saida = []
    for p in partes:
        saida += re.split(r"\s+e\s+(?=\S)", p)
    ativos = []
    for p in (x.strip() for x in saida if x.strip()):
        m = RE_DOSE.match(p)
        ativos.append((m.group(1), m.group(2).replace(" ", "")) if m else (p, None))
    return ativos


def quebra(texto, fonte, largura):
    """Quebra um ativo em linhas que caibam na largura."""
    palavras, linhas, atual = texto.split(), [], ""
    for p in palavras:
        teste = (atual + " " + p).strip()
        if fonte.getlength(teste) <= largura or not atual:
            atual = teste
        else:
            linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


def monta_titulo(ativos, fonte_path, largura):
    """Escala 92 × 0,85^(n−1) pelo nº de linhas; depois reduz de 2 em 2 px até caber."""
    n = len(ativos)
    for _ in range(6):  # converge: o nº de linhas depende do tamanho e vice-versa
        tam = round(92 * 0.85 ** (n - 1))
        fonte = ImageFont.truetype(fonte_path, tam)
        blocos = [quebra(a, fonte, largura) for a in ativos]
        novo_n = sum(len(b) for b in blocos)
        if novo_n == n:
            break
        n = novo_n
    while max(fonte.getlength(l) for b in blocos for l in b) > largura and tam > 20:
        tam -= 2
        fonte = ImageFont.truetype(fonte_path, tam)
        blocos = [quebra(a, fonte, largura) for a in ativos]
    return fonte, tam, blocos


def espaco_linhas(fonte, de_cima, de_baixo, lead):
    """Leading interno, aumentado só se a cedilha/descendente da linha de cima encostar
    no acento da linha de baixo (anti-sobreposição de glifos)."""
    h = fonte.getbbox("H")
    desce = max(0, fonte.getbbox(de_cima)[3] - h[3])       # o que passa abaixo da base
    sobe = max(0, h[1] - fonte.getbbox(de_baixo)[1])       # o que passa acima das maiúsculas
    return max(lead, desce + sobe + round(0.15 * (h[3] - h[1])))


def compor(mockup_path, fontes_dir, titulo, saida, tipo="poteCapsula", dose=None, doses=None, conteudo=None):
    """dose: dose única (produto de 1 ativo). doses: lista, uma por ativo.
    Sem nenhum dos dois, a dose de cada ativo é lida do próprio título.
    conteudo: texto da tarja (ex.: "Contém 30 doses"); sem ele, é lido do fim do título
    ("... - 30 Doses", "... 60ml"). O conteúdo sai do título ANTES de ler as doses."""
    m = RE_CONT.search(titulo)
    if m:
        conteudo = conteudo or texto_conteudo(m.group(1), m.group(2))
        titulo = titulo[:m.start()].rstrip(" -")
    g = GEOMETRIA[tipo]
    img = abre_mockup(mockup_path, g)
    d = ImageDraw.Draw(img)
    preta = f"{fontes_dir}/Poppins-Black.ttf"
    media = f"{fontes_dir}/Poppins-SemiBold.ttf"

    ativos = separa_ativos(titulo)
    nomes = [n.upper() for n, _ in ativos]
    lidas = [ds for _, ds in ativos]
    if doses:
        lidas = list(doses) + [None] * (len(nomes) - len(doses))
    elif dose:
        lidas = [None] * (len(nomes) - 1) + [dose]   # dose única vai abaixo do último ativo
    y0, y1 = g["titulo_y"]

    fonte, tam, blocos = monta_titulo(nomes, preta, g["largura_max"])
    while True:
        cap = fonte.getbbox("H")[3] - fonte.getbbox("H")[1]
        lead = round(0.30 * cap)
        tam_d = TAM_DOSE
        fd = ImageFont.truetype(media, tam_d)
        cap_d = fd.getbbox("0")[3] - fd.getbbox("0")[1]
        # cada grupo: linhas do ativo (leading interno) + dose; entre grupos, 2x ("Sep2x").
        # respiro título→dose: sempre 1x o leading interno (a dose fica colada no seu ativo)
        gap_d = lead
        total = 0
        for gi, b in enumerate(blocos):
            total += len(b) * cap + sum(espaco_linhas(fonte, b[k], b[k + 1], lead) for k in range(len(b) - 1))
            if lidas[gi]:
                total += gap_d + cap_d
            if gi < len(blocos) - 1:
                total += 2 * lead
        if total <= (y1 - y0) or tam <= 30:
            break
        # caso extremo de não-caber: reduz o título de 2 em 2 px
        tam -= 2
        fonte = ImageFont.truetype(preta, tam)
        blocos = [quebra(a, fonte, g["largura_max"]) for a in nomes]

    topo = round((y0 + y1) / 2 - total / 2)
    # verificador anti-sobreposição: o bloco (títulos + doses) não pode sair da faixa do título
    if topo < y0 or topo + total > y1:
        raise ValueError(f"título não cabe na faixa ({total}px > {y1 - y0}px): {titulo}")
    y = topo
    for gi, b in enumerate(blocos):
        larg = max(fonte.getlength(l) for l in b)
        for li, l in enumerate(b):
            w = fonte.getlength(l)
            # ancora pelo topo das maiúsculas (bbox de 'H') para alinhar visualmente
            d.text((g["centro_x"] - w / 2, y - fonte.getbbox("H")[1]), l, font=fonte, fill=(0, 0, 0))
            y += cap + (espaco_linhas(fonte, l, b[li + 1], lead) if li < len(b) - 1 else 0)
        if lidas[gi]:
            # dose: abaixo do ativo, alinhada à direita pela linha mais larga desse ativo, azul da tarja
            y += gap_d
            wd = fd.getlength(lidas[gi])
            d.text((g["centro_x"] + larg / 2 - wd, y - fd.getbbox("0")[1]), lidas[gi], font=fd, fill=COR_DOSE)
            y += cap_d
        if gi < len(blocos) - 1:
            y += 2 * lead
    linhas = [l for b in blocos for l in b]
    larg_titulo = max(fonte.getlength(l) for l in linhas)

    # tarja: "Contém" + NÚMERO (maior, negrito) + unidade, centralizado na tarja, mesma linha de base
    if conteudo:
        if isinstance(conteudo, str):                    # texto livre: tenta separar o número
            mm = re.match(r"^(.*?)(\d+(?:[.,]\d+)?)(.*)$", conteudo)
            conteudo = (mm.group(1), mm.group(2), mm.group(3)) if mm else (conteudo, "", "")
        fm = ImageFont.truetype(f"{fontes_dir}/Poppins-Medium.ttf", TAM_TARJA_MENOR)
        fb = ImageFont.truetype(f"{fontes_dir}/Poppins-Bold.ttf", TAM_TARJA_NUMERO)
        partes = [(conteudo[0], fm), (conteudo[1], fb), (conteudo[2], fm)]
        larg = sum(f.getlength(s) for s, f in partes)
        # centraliza verticalmente pela altura dos algarismos do número
        alt_num = -fb.getbbox("0", anchor="ls")[1]
        ty0, ty1 = g["tarja_y"]
        base = (ty0 + ty1) / 2 + alt_num / 2
        x = g["centro_x"] - larg / 2
        for s, f in partes:
            d.text((x, base), s, font=f, fill=COR_TARJA_TXT, anchor="ls")
            x += f.getlength(s)
        conteudo = "".join(conteudo)

    img.save(saida, "JPEG", quality=92)
    return {"conteudo": conteudo, "tamanho_fonte": tam, "linhas": linhas, "doses": lidas, "tamanho_dose": tam_d if any(lidas) else None,
            "largura_max_px": round(larg_titulo), "altura_bloco": total}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mockup", required=True)
    ap.add_argument("--fontes", required=True)
    ap.add_argument("--titulo", required=True)
    ap.add_argument("--saida", required=True)
    ap.add_argument("--tipo", default="poteCapsula")
    ap.add_argument("--dose", default=None, help='dose única, ex.: "500mg"')
    ap.add_argument("--doses", default=None, help='uma por ativo, separadas por "|", ex.: "1000mg|400UI|50mcg"')
    ap.add_argument("--conteudo", default=None, help='texto da tarja, ex.: "Contém 60ml"')
    a = ap.parse_args()
    print(compor(a.mockup, a.fontes, a.titulo, a.saida, a.tipo, a.dose, a.doses.split("|") if a.doses else None, a.conteudo))
