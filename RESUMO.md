# Scrapper Manga

## Objetivo
Criar um script Python que baixa páginas de mangá do site youngchampion.jp, extraindo as imagens via API REST e desembaralhando (unscramble) as páginas.

## O Que Fizemos Até Agora

### 1. Análise do Site
- Identificamos que o youngchampion.jp usa Next.js com RSC (React Server Components).
- O viewer de mangá carrega as imagens client-side via uma API REST privada.
- As imagens são servidas do domínio `viewer.youngchampion.jp` (CloudFront/S3) com URLs assinadas (expiração ~30 min).

### 2. Descoberta dos Endpoints
- **Informações do episódio**: `GET /api/episodes/{episode_id}` (funciona via requests direto) → retorna metadados e `viewerId`.
- **Informações das páginas**: `GET /api/book/contentsInfo?user-id=&comici-viewer-id={viewerId}&page-from=0&page-to=N` (só funciona com cookies de sessão do navegador, precisa de Playwright) → retorna `totalPages`, array `result` com `imageUrl`, `scramble`, `sort`, `width`, `height`.

### 3. Abordagens de Download Tentadas

#### A. Canvas Extraction (Playwright) — Funciona parcialmente
- Usa Playwright para abrir a página em navegador headless.
- Aguarda o viewer renderizar as páginas em `<canvas>`.
- Extrai os dados via `canvas.toDataURL()`.
- **Problema**: viewer só renderiza ~3 páginas (lazy loading), imagens saem em baixa resolução (949×1350 vs 1440×2048 original).

#### B. Requests + Unscramble (playwright p/ API + requests p/ imagens) — Resolução cheia
- Usa Playwright só para capturar o JSON da API.
- Baixa as imagens scrambladas diretamente via requests (URLs assinadas).
- Aplica unscramble no PIL.
- **Problema**: O array `scramble` da API não corresponde nem ao método 1 nem ao método 2 de unscramble que testamos.
- Conseguimos deduzir o mapeamento correto para a página 1 por correlação NCC (com resultados perfeitos), mas não sabemos a relação entre esse mapeamento descoberto e o array `scramble` da API — ou seja, não conseguimos generalizar para as outras páginas nem para outros episódios.

### 4. Entendimento do Scramble
- Cada imagem baixada é um JPEG de 1440×2048 contendo 16 pedaços (grid 4×4) fora de ordem.
- A API retorna um array `scramble` de 16 inteiros.
- Método 1 testado: `scramble[orig] = scr_pos` → copiar de `scr_pos` para `orig`.
- Método 2 testado: `scramble[scr_pos] = orig_pos` → copiar de `scr_pos` para `orig_pos`.
- **Nenhum dos dois funcionou** — o mapeamento real para página 1 foi `[3, 7, 11, 4, 13, 5, 10, 14, 8, 1, 12, 15, 6, 9, 0, 2]`, que difere do `scramble` da API `[12, 7, 2, 9, 13, 5, 4, 6, 14, 10, 3, 0, 1, 11, 15, 8]`.
- A relação entre o mapeamento real e o `scramble` da API ainda não foi descoberta.
- Suspeita: a ordem de indexação dos pedaços no grid (row-major vs column-major ou outra) pode ser diferente entre nossa implementação e a API.

### 5. Diagnóstico Realizado
- Descobrimos que `page_002.jpg` (referência boa do canvas) corresponde a `result[0]` da API (manga page 1).
- Usando correlação NCC normalizada, deduzimos o mapeamento real dos 16 pedaços para a página 1.
- Os pedaços corrigidos têm NCC > 0.91 vs referência (praticamente idênticos, diferença só de compressão JPEG).
- Salvamos `page_002_FIXED.png` na pasta do capítulo.

## Problemas a Resolver

### 1. Interpretação do Scramble (RESOLVIDO)
- Descoberto via userscript "Rippper" no Greasy Fork (scripts/573396-rippper).
- O array `scramble` da API usa indexação **column-major** (não row-major).
- `scramble[i] = sourceIndex` significa: o pedaço na posição destino `i` (column-major) deve vir da posição `sourceIndex` (column-major) na imagem scramblada.
- Conversão de coordenadas column-major: `x = (idx // 4) * tileW`, `y = (idx % 4) * tileH`.
- Confirmado via NCC: o `discovered` em row-major `[3, 7, 11, 4, 13, 5, 10, 14, 8, 1, 12, 15, 6, 9, 0, 2]` convertido para column-major resulta exatamente no array da API `[12, 7, 2, 9, 13, 5, 4, 6, 14, 10, 3, 0, 1, 11, 15, 8]`.

### 2. Lazy Loading do Viewer (NÃO É MAIS NECESSÁRIO)
- Não precisamos mais de canvas extraction, pois o download via requests + unscramble funciona perfeitamente.

### 3. API Sessions (RESOLVIDO)
- `/api/book/contentsInfo` precisa de cookies de navegador → usamos Playwright apenas para capturar o JSON.

### 4. Signed URLs (RESOLVIDO)
- Funcionam diretamente via requests (self-contained com Expires/Signature/Key-Pair-Id).

### 5. Encoding (SEM SOLUÇÃO)
- Terminal Windows não exibe japonês corretamente, mas não afeta o funcionamento.

## Status Atual
- ✅ Download de todas as 10 páginas concluído com sucesso
- ✅ Unscramble corrigido usando column-major (método confirmado pelo Rippper)
- ✅ Imagens salvas em PNG sem perdas em 1440×2048
- ✅ `scraper.py` funcional para qualquer episódio do youngchampion.jp
