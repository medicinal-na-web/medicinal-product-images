"""Reenquadra a imagem de produto para o produto ocupar ~80% do quadro.

As fotos montadas com o mockup (compor_imagem.py) deixam o pote em ~62% do quadro.
Este script corta o branco em volta, num quadrado centrado no produto, sem ampliar:
a saída fica na resolução do recorte (ex.: 1600 -> ~1250 px), sem perda de nitidez.

Uso:
    python3 scripts/enquadrar_imagem.py ENTRADA.jpg SAIDA.jpg [--ocupacao 0.8]
"""
import argparse

from PIL import Image, ImageChops

LIMIAR = 8          # diferença do fundo que conta como produto (pega a sombra suave)
TAMANHO_MIN = 1000  # não reduz abaixo disso (exigência de imagem da VTEX e do Google)


def caixa_do_produto(img):
    fundo = Image.new("RGB", img.size, img.getpixel((2, 2)))
    mascara = ImageChops.difference(img, fundo).convert("L").point(lambda p: 255 if p > LIMIAR else 0)
    return mascara.getbbox()


def enquadra(img, ocupacao):
    caixa = caixa_do_produto(img)
    if not caixa:
        return img, None
    x0, y0, x1, y1 = caixa
    lado = max(x1 - x0, y1 - y0) / ocupacao
    lado = int(min(max(lado, TAMANHO_MIN), img.width, img.height))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    # mantém o recorte dentro da imagem
    esq = int(min(max(cx - lado / 2, 0), img.width - lado))
    topo = int(min(max(cy - lado / 2, 0), img.height - lado))
    recorte = img.crop((esq, topo, esq + lado, topo + lado))
    ocup = max(x1 - x0, y1 - y0) / lado
    return recorte, ocup


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada")
    ap.add_argument("saida")
    ap.add_argument("--ocupacao", type=float, default=0.8)
    a = ap.parse_args()
    img = Image.open(a.entrada).convert("RGB")
    novo, ocup = enquadra(img, a.ocupacao)
    novo.save(a.saida, "JPEG", quality=92, optimize=True)
    print(f"{a.entrada}: {img.size} -> {novo.size}, produto ocupa {ocup:.0%}" if ocup else f"{a.entrada}: sem produto detectado")


if __name__ == "__main__":
    main()
