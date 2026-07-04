# Scrapper Manga

Script em Python para baixar capítulos de mangá do [youngchampion.jp](https://youngchampion.jp), extraindo as imagens em resolução original (1440×2048) e desembaralhando o grid 4×4.

## Funcionamento

O site youngchampion.jp exibe as páginas de mangá scrambladas (pedaços do grid 4×4 fora de ordem) e as desembaralha via JavaScript no navegador. O scraper funciona em 3 etapas:

1. **Obter informações do episódio** — via `GET /api/episodes/{id}` (requests direto). Retorna metadados da série e `viewerId`.

2. **Capturar dados das páginas** — via `GET /api/book/contentsInfo` com Playwright (precisa de cookies de sessão do navegador). Retorna `totalPages`, e para cada página: `imageUrl` (assinada), `scramble` (array de permutação), `sort`, `width`, `height`.

3. **Download + Unscramble** — as imagens são baixadas via requests direto (URLs assinadas do CloudFront são self-contained). O array `scramble` é interpretado em indexação **column-major** para remontar o grid 4×4 corretamente via PIL.

## Requisitos

- Python 3.12+
- [Playwright](https://playwright.dev/python/) (com Chromium instalado: `playwright install chromium`)

### Dependências

```
pip install requests pillow playwright
playwright install chromium
```

## Uso

1. Coloque a URL do episódio na primeira linha do arquivo `tips.txt`:

```
https://youngchampion.jp/episodes/136b3e04b2369
```

2. Execute o script:

```
python scraper.py
```

3. As páginas serão salvas em `downloads/{Série} - {Episódio}/page_{001..N}.png`.

## Estrutura

```
scrapper-manga/
├── scraper.py      # Script principal
├── tips.txt        # URL do episódio (1 linha)
├── downloads/      # Páginas baixadas e desembaralhadas
└── README.md       # Documentação
```

## Explicação do Scramble

Cada imagem baixada contém 16 pedaços (grid 4×4) fora de ordem. A API retorna um array `scramble` de 16 inteiros que mapeia a posição de destino para a posição de origem, ambos em indexação **column-major** (diferente da row-major tradicional):

```
scramble[i] = posição no grid scramblado de onde copiar o pedaço
```

**Column-major**: o índice 0-15 é mapeado para (coluna, linha) como `col = idx // 4, row = idx % 4`.

Isso foi descoberto através do userscript [Rippper](https://greasyfork.org/en/scripts/573396-rippper) (Greasy Fork), que implementa o mesmo algoritmo de unscramble para sites que usam o Comici reader.

## Notas

- O script usa Playwright apenas para capturar o JSON da API (necessita de sessão autenticada do navegador). As imagens em si são baixadas com `requests`.
- As URLs das imagens expiram em aproximadamente 30 minutos (parâmetro `Expires` na URL assinada).
- As páginas já baixadas são puladas automaticamente em execuções subsequentes.
