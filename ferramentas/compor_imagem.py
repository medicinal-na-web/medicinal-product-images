"""Composição da imagem de embalagem (padrão Medicinal aprovado em 18/06/2026).

Composição programática em Pillow sobre o mockup branco. Não é geração por IA.
Fonte da verdade: SOP "descricaoProdutos" (Notion), seção "Padrão do campo cover_image_url".

Uso:
    python3 scripts/compor_imagem.py --mockup poteCapsula.jpeg --fontes DIR --titulo "Terasen" --saida terasen.jpg
    python3 scripts/compor_imagem.py ... --titulo "UC-II 40mg - 30 Doses" --selos assets/selos/uc-ii.png --saida uc-ii.jpg
"""
import argparse
import re

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Geometria do poteCapsula (1600x1600), mapeada por análise de cor
GEOMETRIA = {
    "poteCapsula": {
        "centro_x": 796,
        "fundo_branco": True,        # fundo do mockup tem textura 247–253: vira branco puro (23/10/2026)
        "largura_max": 500,          # alvo confortável (rótulo vai de 506 a 1086 = 580 px)
        "titulo_y": (810, 1060),     # faixa do título (acima da tarja alta)
        "tarja_y": (1148, 1275),     # tarja azul do mockup, RGB(24,104,158)
        # tarja alta (regra de 21/10/2026): a tarja do mockup é esticada para cima, coluna a coluna,
        # quadro "uso interno / CONTÉM" centrado na altura da tarja (tarja em x≈937: y 1077–1276),
        # preservando o sombreado e a curva do pote. "Contém" vai à direita, selos à esquerda.
        "tarja_alta": {"subir": 75, "centro_y": 1172, "quadro_escala": 0.9, "quadro_topo": 1106, "quadro_dx": 16},
        "selo": {"x0": 532, "altura": 165, "altura_min": 70, "largura_max": 250, "entre": 12, "folga_conteudo": 28, "centro_y": 1172},
    },
    # vidroAmbarContaGotas: original 4000x5000 (retrato). Enquadrado num quadrado de 4400 px
    # (centro x 2000, topo y 350) e reduzido para 1600 (escala 0,3636). Mapeado em 19/10/2026:
    # rótulo x 1291-2708 / y 2380-3999, logo y 2476-2590, tarja y 4000-4334.
    "vidroAmbarContaGotas": {
        "preparo": {"centro_x": 2000, "lado": 4400, "topo": 350},
        "centro_x": 797,
        "largura_max": 440,          # rótulo de 542 a 1058 = 516 px
        "titulo_y": (847, 1240),     # abaixo do logo, acima da tarja alta
        "tarja_y": (1327, 1449),     # tarja do mockup (antes de esticar)
        # tarja alta (23/10/2026), mesmo desenho do pote: rótulo mais estreito, quadro 12 px mais à esquerda
        "tarja_alta": {"subir": 70, "centro_y": 1353, "quadro_escala": 0.9, "quadro_topo": 1284, "quadro_dx": -12},
        "selo": {"x0": 566, "altura": 160, "altura_min": 70, "largura_max": 240, "entre": 12, "folga_conteudo": 24, "centro_y": 1353},
    },
}


def branqueia_fundo(img, limiar=244, ponto_branco=251, ganho=1.6):
    """Fundo do mockup em branco puro (regra de 23/10/2026: o pote tinha fundo 247–253 com textura).

    A embalagem (maior objeto com mínimo do canal < limiar, preenchido linha a linha) fica intacta. Fora dela,
    tudo vira 255, exceto a sombra numa faixa sob a embalagem (fundo suavizado, remapeado a partir de `ponto_branco`).
    """
    a = np.asarray(img).astype(np.float32)
    escuro = a.min(2) < limiar
    # só a embalagem: o maior objeto escuro (manchas soltas do fundo do mockup ficam de fora)
    n, rotulos, est, _ = cv2.connectedComponentsWithStats(
        cv2.morphologyEx(escuro.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8)))
    escuro = rotulos == 1 + int(np.argmax(est[1:, cv2.CC_STAT_AREA]))
    corpo = np.zeros_like(escuro)
    for y in np.nonzero(escuro.any(1))[0]:
        xs = np.nonzero(escuro[y])[0]
        corpo[y, xs[0]:xs[-1] + 1] = True
    m = Image.fromarray((corpo * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(3))
    peso = np.asarray(m).astype(np.float32)[..., None] / 255
    lum = a.mean(2)
    lum[corpo] = ponto_branco
    lum = np.asarray(Image.fromarray(lum.round().astype(np.uint8)).filter(ImageFilter.GaussianBlur(18))).astype(np.float32)
    # sombra só numa faixa sob a embalagem (fora dela, branco puro), com transição suave
    ys, xs = np.nonzero(corpo)
    zona = np.zeros(corpo.shape, np.uint8)
    zona[ys.max() - 80:ys.max() + 90, max(xs.min() - 90, 0):xs.max() + 90] = 255
    zona = np.asarray(Image.fromarray(zona).filter(ImageFilter.GaussianBlur(30))).astype(np.float32) / 255
    fundo = 255 - np.clip(ponto_branco - lum, 0, None) * ganho * zona
    out = a * peso + fundo[..., None] * (1 - peso)
    return Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8))


def abre_mockup(path, g):
    """Abre o mockup; se a geometria pedir, enquadra num quadrado branco e reduz para 1600."""
    img = Image.open(path).convert("RGB")
    if g.get("fundo_branco"):
        img = branqueia_fundo(img)
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
# Espaço entre ativos diferentes, em múltiplos do leading interno (0,30 × maiúsculas): bem maior que o
# espaço entre linhas do mesmo ativo, para separar visualmente os ativos (21/10/2026; antes 2x, "Sep2x")
SEP_ATIVOS = 4
# Na tarja alta (21/10/2026) a dose segue o número do quadro, como no site: Varela Round, zero com ponto, SEM negrito,
# algarismos com 28 px de altura (o site usa 33 px; reduzido a pedido em 21/10/2026), IGUAL em todos os rótulos.
# Com mais de 2 ativos, as doses não aparecem (regra de 21/10/2026).
ALT_DOSE_ALTA = 28
MAX_ATIVOS_COM_DOSE = 2

# Tarja (regra de 19/10/2026): "Contém N doses" (ou cápsulas / ml / g), uma linha, centralizada na tarja.
# Substitui o aviso "Siga orientações de um / profissional habilitado".
# "Contém" e a unidade em fonte menor; o número (volume) maior e em negrito, mesma linha de base.
COR_TARJA_TXT = (232, 242, 250)
TAM_TARJA_MENOR = 28      # Poppins Medium
TAM_TARJA_NUMERO = 56     # Poppins Bold
# Tarja alta (regra de 21/10/2026): réplica do quadro dos potes atuais do site (ex.: UC-II, 1069):
# "uso interno" / quadro arredondado com CONTÉM / NÚMERO (zero com ponto) / UNIDADE, separados por fios.
# Medidas tiradas da imagem do site (1571 px) e convertidas para o mockup (escala 1,023, pela largura do rótulo).
# Cada caixa: (x0, y0, x1, y1) no mockup de 1600 px; os textos são ajustados pela altura e centralizados em x.
COR_QUADRO = (226, 232, 238)
QUADRO = {
    "uso": (884, 1072, 992, 1088),
    "caixa": (881, 1097, 993, 1226),
    "raio": 13, "fio": 2,
    "contem": (892, 1105, 983, 1122),
    "div1": (889, 1128, 986),
    "numero": (902, 1136, 971, 1189),
    "div2": (889, 1196, 986),
    "unidade": (900, 1202, 978, 1218),
}
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
        # "e" seguido de 1–2 caracteres não separa ativo ("Ômega 3 6 e 9")
        saida += re.split(r"\s+e\s+(?=\S)(?!\S{1,2}(?:\s|$))", p)
    ativos = []
    for p in (x.strip() for x in saida if x.strip()):
        m = RE_DOSE.match(p)
        ativos.append((m.group(1), m.group(2).replace(" ", "")) if m else (p, None))
    return ativos


def quebra(texto, fonte, largura):
    """Quebra um ativo em linhas que caibam na largura. " / " no texto força a quebra naquele ponto."""
    if " / " in texto:   # cada trecho é quebrado (e equilibrado) separadamente
        return [l for trecho in texto.split(" / ") for l in quebra(trecho.strip(), fonte, largura)]
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
    # linha de 1 ou 2 caracteres não fica sozinha ("METABOLIZE / 4"): junta com a vizinha;
    # se passar da largura, o título reduz de 2 em 2 px em monta_titulo
    k = 0
    while len(linhas) > 1 and k < len(linhas):
        if len(linhas[k]) <= 2:
            if k > 0:
                linhas[k - 1] += " " + linhas.pop(k)
            else:
                linhas[1] = linhas.pop(0) + " " + linhas[0]
            continue
        k += 1
    return equilibra(linhas, fonte, largura)


PREPOSICOES = {"de", "da", "do", "das", "dos", "e", "com", "em"}


def equilibra(linhas, fonte, largura):
    """Mantém o nº de linhas, mas redistribui as palavras para a linha mais larga ficar a menor possível
    (regra de 21/10/2026): "HAMAMELIS / EXT SECO", nunca "HAMAMELIS EXT / SECO".
    Nenhuma linha fica com 1 ou 2 caracteres, se houver alternativa."""
    from itertools import combinations
    palavras = " ".join(linhas).split()
    n = len(linhas)
    if n < 2 or len(palavras) <= n:
        return linhas
    melhor = None
    for cortes in combinations(range(1, len(palavras)), n - 1):
        limites = (0,) + cortes + (len(palavras),)
        cand = [" ".join(palavras[a:b]) for a, b in zip(limites, limites[1:])]
        larguras = [fonte.getlength(l) for l in cand]
        # preposição/conjunção não fica no fim da linha ("TINTURA DE / CENTELLA" -> "TINTURA / DE CENTELLA")
        # é só desempate: vale quando a largura fica parecida (até 12% a mais), não às custas de letra menor
        solta = any(l.split()[-1].lower() in PREPOSICOES for l in cand[:-1])
        chave = (any(len(l) <= 2 for l in cand), max(larguras) * (1.12 if solta else 1), max(larguras) - min(larguras))
        if melhor is None or chave < melhor[0]:
            melhor = (chave, cand)
    # hífen solto não fica no fim nem no começo da linha ("MSM -" / "ENXOFRE...")
    return [l.strip(" -–") or l for l in melhor[1]]


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


def estica_tarja(img, g):
    """Sobe o topo da tarja em `subir` px: cada coluna da tarja é reamostrada na vertical,
    então o sombreado horizontal e a curva das bordas do pote ficam iguais aos do mockup."""
    subir = g["tarja_alta"]["subir"]
    ty0, ty1 = g["tarja_y"]
    a = np.asarray(img).copy()
    azul = (a[:, :, 2].astype(int) - a[:, :, 0].astype(int)) > 60
    for x in range(a.shape[1]):
        ys = np.nonzero(azul[ty0 - 20:ty1 + 10, x])[0]
        if len(ys) < 20:
            continue
        topo, base = ty0 - 20 + ys.min(), ty0 - 20 + ys.max()
        col = a[topo:base + 1, x].astype(float)
        novo = base - (topo - subir) + 1
        pos = np.linspace(0, len(col) - 1, novo)
        a[topo - subir:base + 1, x] = np.stack([np.interp(pos, np.arange(len(col)), col[:, c]) for c in range(3)], 1).round()
    return Image.fromarray(a)


def texto_na_caixa(img, texto, fonte_path, caixa, cor, negrito=2, ponto_no_zero=False):
    """Desenha `texto` ajustado pela altura da caixa (largura limitada a ela), centralizado em x.
    Renderiza 4x maior e reduz, para bordas limpas. ponto_no_zero: ponto no centro de cada "0"."""
    x0, y0, x1, y1 = caixa
    f = ImageFont.truetype(fonte_path, 400)
    camada = Image.new("L", (int(f.getlength(texto)) + 80, 600), 0)
    dd = ImageDraw.Draw(camada)
    dd.text((40, 100), texto, font=f, fill=255, stroke_width=negrito * 4, stroke_fill=255)
    if ponto_no_zero:
        x = 40
        for ch in texto:
            w = f.getlength(ch)
            if ch == "0":
                bx = dd.textbbox((x, 100), ch, font=f)
                cx, cy, r = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2, 0.075 * (bx[3] - bx[1])
                dd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
            x += w
    camada = camada.crop(camada.getbbox())
    alt = y1 - y0
    larg = min(x1 - x0, round(camada.width * alt / camada.height))
    camada = camada.resize((larg, alt), Image.LANCZOS)
    img.paste(Image.new("RGB", camada.size, cor), (round((x0 + x1) / 2 - larg / 2), y0), camada)


def mascara_numero(texto, fonte_path, alt_digitos, negrito=3, ponto_no_zero=True):
    """Máscara (L) do texto no estilo do número do quadro: renderiza 4x maior (com o mesmo negrito e
    o ponto no zero) e reduz até os algarismos terem `alt_digitos` px. Devolve (máscara, topo dos algarismos)."""
    f = ImageFont.truetype(fonte_path, 400)
    camada = Image.new("L", (int(f.getlength(texto)) + 80, 700), 0)
    dd = ImageDraw.Draw(camada)
    dd.text((40, 100), texto, font=f, fill=255, stroke_width=negrito * 4, stroke_fill=255)
    x = 40
    for ch in texto:
        if ponto_no_zero and ch == "0":
            bx = dd.textbbox((x, 100), ch, font=f)
            cx, cy, r = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2, 0.075 * (bx[3] - bx[1])
            dd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
        x += f.getlength(ch)
    caixa = camada.getbbox()
    dig = dd.textbbox((40, 100), "0", font=f, stroke_width=negrito * 4)
    k = alt_digitos / (dig[3] - dig[1])
    camada = camada.crop(caixa)
    camada = camada.resize((round(camada.width * k), round(camada.height * k)), Image.LANCZOS)
    return camada, round((dig[1] - caixa[1]) * k)


def quadro_ajustado(g):
    """Coordenadas do QUADRO reduzidas por `quadro_escala` (em torno do centro em x), deslocadas `quadro_dx`
    para a direita e com o topo em `quadro_topo`."""
    ta = g["tarja_alta"]
    f, topo = ta.get("quadro_escala", 1), ta.get("quadro_topo", QUADRO["uso"][1])
    cx, y_ref = (QUADRO["caixa"][0] + QUADRO["caixa"][2]) / 2, QUADRO["uso"][1]
    X = lambda x: round(cx + (x - cx) * f + ta.get("quadro_dx", 0))
    Y = lambda y: round(topo + (y - y_ref) * f)
    q = {}
    for k, v in QUADRO.items():
        if k in ("raio",):
            q[k] = round(v * f)
        elif k == "fio":
            q[k] = v
        elif k.startswith("div"):
            q[k] = (X(v[0]), Y(v[1]), X(v[2]))
        else:
            q[k] = (X(v[0]), Y(v[1]), X(v[2]), Y(v[3]))
    return q


def desenha_quadro(img, partes, fontes_dir, g, uso="uso interno"):
    """Réplica do quadro do site: "uso interno", moldura arredondada, CONTÉM / NÚMERO / UNIDADE e dois fios."""
    q, fonte = quadro_ajustado(g), f"{fontes_dir}/VarelaRound-Regular.ttf"
    d = ImageDraw.Draw(img)
    texto_na_caixa(img, uso, fonte, q["uso"], COR_QUADRO, negrito=3)
    S = 4  # moldura desenhada 4x maior e reduzida, para o contorno fino ficar suave
    x0, y0, x1, y1 = q["caixa"]
    m = Image.new("L", ((x1 - x0 + 4) * S, (y1 - y0 + 4) * S), 0)
    ImageDraw.Draw(m).rounded_rectangle((2 * S, 2 * S, (x1 - x0 + 2) * S, (y1 - y0 + 2) * S), radius=q["raio"] * S,
                                        outline=255, width=q["fio"] * S)
    m = m.resize((x1 - x0 + 4, y1 - y0 + 4), Image.LANCZOS)
    img.paste(Image.new("RGB", m.size, COR_QUADRO), (x0 - 2, y0 - 2), m)
    for k in ("div1", "div2"):
        a, y, b = q[k]
        d.line((a, y, b, y), fill=COR_QUADRO, width=q["fio"])
    texto_na_caixa(img, partes[0].strip().upper(), fonte, q["contem"], COR_QUADRO, negrito=3)
    texto_na_caixa(img, partes[1], fonte, q["numero"], COR_QUADRO, negrito=3, ponto_no_zero=True)
    texto_na_caixa(img, partes[2].strip().upper(), fonte, q["unidade"], COR_QUADRO, negrito=3)
    return x0


def posiciona_selos(selos, g, x_max):
    """Abre os PNG dos selos e devolve [(imagem, x, y)] na tarja, à esquerda, lado a lado, centrados
    na altura da tarja. Todos com a MESMA altura: a maior que caiba até x_max (teto em `altura`;
    cada selo limitado a `largura_max`). Abaixo de `altura_min`, para com erro."""
    cfg = g["selo"]
    cy = cfg.get("centro_y", g["tarja_alta"]["centro_y"])
    imgs = [Image.open(c).convert("RGBA") for c in selos]
    livre = x_max - cfg["x0"] - cfg["entre"] * (len(imgs) - 1)

    def larguras(h):
        return [min(cfg["largura_max"], s.width * h / s.height) for s in imgs]

    h = cfg["altura"]
    while sum(larguras(h)) > livre:
        h -= 1
        if h < cfg["altura_min"]:
            raise ValueError(f"selos demais para a tarja: {len(selos)}")
    x, saida = cfg["x0"], []
    for s, w in zip(imgs, larguras(h)):
        f = min(h / s.height, w / s.width)
        s = s.resize((round(s.width * f), round(s.height * f)), Image.LANCZOS)
        saida.append((s, x, round(cy - s.height / 2)))
        x += s.width + cfg["entre"]
    return saida


def cola_selos(img, posicionados):
    """Cola os selos com uma sombra leve, como etiqueta aplicada na tarja."""
    camada = img.convert("RGBA")
    for s, x, y in posicionados:
        sombra = Image.new("RGBA", camada.size, (0, 0, 0, 0))
        sombra.paste((0, 0, 0, 255), (x + 3, y + 5), s.split()[3].point(lambda v: v * 0.45))
        camada.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(5)))
        camada.alpha_composite(s, (x, y))
    return camada.convert("RGB")


def compor(mockup_path, fontes_dir, titulo, saida, tipo="poteCapsula", dose=None, doses=None, conteudo=None, selos=None,
           uso="uso interno"):
    """dose: dose única (produto de 1 ativo). doses: lista, uma por ativo.
    Sem nenhum dos dois, a dose de cada ativo é lida do próprio título.
    conteudo: texto da tarja (ex.: "Contém 30 doses"); sem ele, é lido do fim do título
    ("... - 30 Doses", "... 60ml"). O conteúdo sai do título ANTES de ler as doses.
    selos: caminhos dos PNG dos selos de procedência (assets/selos/), na ordem de colocação."""
    m = RE_CONT.search(titulo)
    if m:
        conteudo = conteudo or texto_conteudo(m.group(1), m.group(2))
        titulo = titulo[:m.start()].rstrip(" -")
    g = GEOMETRIA[tipo]
    img = abre_mockup(mockup_path, g)
    if "tarja_alta" in g:
        img = estica_tarja(img, g)
    d = ImageDraw.Draw(img)
    preta = f"{fontes_dir}/Poppins-Bold.ttf"   # título: Poppins Bold (23/10/2026; antes Black)
    media = f"{fontes_dir}/Poppins-SemiBold.ttf"

    ativos = separa_ativos(titulo)
    nomes = [n.upper() for n, _ in ativos]
    lidas = [ds for _, ds in ativos]
    if doses:
        lidas = list(doses) + [None] * (len(nomes) - len(doses))
    elif dose:
        lidas = [None] * (len(nomes) - 1) + [dose]   # dose única vai abaixo do último ativo
    y0, y1 = g["titulo_y"]

    tam_d = TAM_DOSE
    fd = ImageFont.truetype(media, tam_d)
    cap_d = fd.getbbox("0")[3] - fd.getbbox("0")[1]
    dose_alta = "tarja_alta" in g
    mascaras = {}

    if dose_alta and len(nomes) > MAX_ATIVOS_COM_DOSE:
        lidas = [None] * len(nomes)

    def alt_dose(cap):
        return ALT_DOSE_ALTA if dose_alta else cap_d

    def mede(fonte, blocos):
        """Altura do bloco: cada grupo = linhas do ativo (leading interno) + dose; entre grupos, 2x ("Sep2x").
        Respiro título→dose: sempre 1x o leading interno (a dose fica colada no seu ativo)."""
        cap = fonte.getbbox("H")[3] - fonte.getbbox("H")[1]
        lead = round(0.30 * cap)
        total = 0
        for gi, b in enumerate(blocos):
            total += len(b) * cap + sum(espaco_linhas(fonte, b[k], b[k + 1], lead) for k in range(len(b) - 1))
            if lidas[gi]:
                total += lead + alt_dose(cap)
            if gi < len(blocos) - 1:
                total += SEP_ATIVOS * lead
        return cap, lead, lead, total

    fonte, tam, blocos = monta_titulo(nomes, preta, g["largura_max"])
    while True:
        cap, lead, gap_d, total = mede(fonte, blocos)
        if total <= (y1 - y0) or tam <= 30:
            break
        # caso extremo de não-caber: reduz o título de 2 em 2 px
        tam -= 2
        fonte = ImageFont.truetype(preta, tam)
        blocos = [quebra(a, fonte, g["largura_max"]) for a in nomes]

    def layout(topo):
        """Posições do texto a partir do topo do bloco: [(x, y, texto, fonte, cor, caixa)]."""
        ops, y = [], topo
        for gi, b in enumerate(blocos):
            larg = max(fonte.getlength(l) for l in b)
            for li, l in enumerate(b):
                w = fonte.getlength(l)
                # ancora pelo topo das maiúsculas (bbox de 'H') para alinhar visualmente
                x = g["centro_x"] - w / 2
                ops.append((x, y - fonte.getbbox("H")[1], l, fonte, (0, 0, 0), (x, y, x + w, y + cap)))
                y += cap + (espaco_linhas(fonte, l, b[li + 1], lead) if li < len(b) - 1 else 0)
            if lidas[gi]:
                # dose: abaixo do ativo, alinhada à direita pela linha mais larga desse ativo, azul da tarja
                y += gap_d
                if dose_alta:
                    ad = alt_dose(cap)
                    chave = (lidas[gi], ad)
                    if chave not in mascaras:
                        mascaras[chave] = mascara_numero(lidas[gi], f"{fontes_dir}/VarelaRound-Regular.ttf", ad, negrito=0)
                    m, off = mascaras[chave]
                    wd = m.width
                    x = round(g["centro_x"] + larg / 2 - wd)
                    ops.append((x, round(y) - off, m, None, COR_DOSE, (x, y, x + wd, y + ad)))
                    y += ad - cap_d
                else:
                    wd = fd.getlength(lidas[gi])
                    x = g["centro_x"] + larg / 2 - wd
                    ops.append((x, y - fd.getbbox("0")[1], lidas[gi], fd, COR_DOSE, (x, y, x + wd, y + cap_d)))
                y += cap_d
            if gi < len(blocos) - 1:
                y += SEP_ATIVOS * lead
        return ops

    topo = round((y0 + y1) / 2 - total / 2)
    # verificador anti-sobreposição: o bloco (títulos + doses) não pode sair da faixa do título
    if topo < y0 or topo + total > y1:
        raise ValueError(f"título não cabe na faixa ({total}px > {y1 - y0}px): {titulo}")
    ops = layout(topo)
    for x, yy, texto, f, cor, _ in ops:
        if f is None:                                   # dose no estilo do quadro: máscara pronta
            img.paste(Image.new("RGB", texto.size, cor), (x, yy), texto)
        else:
            d.text((x, yy), texto, font=f, fill=cor)
    linhas = [l for b in blocos for l in b]
    larg_titulo = max(fonte.getlength(l) for l in linhas)

    # tarja: "Contém" + NÚMERO (maior, negrito) + unidade
    x_selos = quadro_ajustado(g)["caixa"][0] if "tarja_alta" in g else None
    if conteudo:
        if isinstance(conteudo, str):                    # texto livre: tenta separar o número
            mm = re.match(r"^(.*?)(\d+(?:[.,]\d+)?)(.*)$", conteudo)
            conteudo = (mm.group(1), mm.group(2), mm.group(3)) if mm else (conteudo, "", "")
        if "tarja_alta" in g:
            x_selos = desenha_quadro(img, conteudo, fontes_dir, g, uso)
        else:
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

    pos_selos = []
    if selos:
        if "selo" not in g:
            raise ValueError(f"selos ainda não mapeados para a embalagem {tipo}")
        pos_selos = posiciona_selos(selos, g, round(x_selos - g["selo"]["folga_conteudo"]))
    if pos_selos:
        img = cola_selos(img, pos_selos)
    img.save(saida, "JPEG", quality=92)
    return {"conteudo": conteudo, "tamanho_fonte": tam, "linhas": linhas, "doses": lidas, "tamanho_dose": tam_d if any(lidas) else None,
            "largura_max_px": round(larg_titulo), "altura_bloco": total, "topo_bloco": topo,
            "selos": [{"x": x, "y": y, "w": s.width, "h": s.height} for s, x, y in pos_selos]}


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
    ap.add_argument("--selos", default=None, help='PNG dos selos separados por "|", ex.: "assets/selos/uc-ii.png"')
    ap.add_argument("--uso", default="uso interno", help='texto acima do quadro: "uso interno" ou "uso externo"')
    a = ap.parse_args()
    print(compor(a.mockup, a.fontes, a.titulo, a.saida, a.tipo, a.dose, a.doses.split("|") if a.doses else None, a.conteudo,
                 a.selos.split("|") if a.selos else None, a.uso))
