# medicinal-product-images
## Imagens automáticas de novos produtos

`.github/workflows/compor-imagens.yml` roda a cada 15 min (ou manualmente em Actions → "Compor imagens de novos produtos").
Lê no Supabase os produtos aprovados sem imagem, compõe o pote com `ferramentas/compor_imagem.py`
(mockup e fontes em `ferramentas/modelo/`) e publica `vtex/<link_id>.jpg`. Imagem já existente nunca é sobrescrita.
