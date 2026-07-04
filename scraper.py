import asyncio, sys, time, json, re, io
from pathlib import Path
import requests
from PIL import Image
from playwright.async_api import async_playwright


class YoungChampionScraper:
    API_EPISODE = "https://youngchampion.jp/api/episodes/{episode_id}"
    API_CONTENTS = "https://youngchampion.jp/api/book/contentsInfo"

    def __init__(self, episode_url, output_dir="downloads"):
        self.episode_url = episode_url
        self.output_dir = Path(output_dir)

        match = re.search(r"/episodes/([a-f0-9]+)", episode_url)
        if not match:
            raise ValueError(f"URL inválida: {episode_url}")
        self.episode_id = match.group(1)

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://youngchampion.jp/",
        })

        self.series_title = None
        self.episode_title = None
        self.total_pages = 0
        self.pages_data = []
        self.chapter_dir = None

    def _get_episode_info(self):
        print("[*] Obtendo informações do episódio...")
        resp = self.session.get(
            self.API_EPISODE.format(episode_id=self.episode_id), timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        ep = data.get("episode", {})
        self.series_title = ep.get("series", {}).get("name", "Desconhecido")
        self.episode_title = ep.get("summary", {}).get("title", "Desconhecido")
        print(f"  Série: {self.series_title}")
        print(f"  Episódio: {self.episode_title}")

    async def _get_contents_info(self):
        print("[*] Capturando dados das páginas via Playwright...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(viewport={"width": 1920, "height": 1080})
            page = await ctx.new_page()

            contents_data = {}

            async def on_response(response):
                url = response.url
                if "api/book/contentsInfo" in url:
                    try:
                        data = await response.json()
                        if "result" in data:
                            contents_data["data"] = data
                    except:
                        pass

            page.on("response", on_response)
            await page.goto(self.episode_url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(5)
            await browser.close()

        if not contents_data.get("data"):
            raise RuntimeError("Falha ao capturar dados das páginas")

        return contents_data["data"]

    def run(self):
        self._get_episode_info()
        data = asyncio.run(self._get_contents_info())

        self.total_pages = data.get("totalPages", 0)
        for item in data.get("result", []):
            self.pages_data.append({
                "sort": item["sort"],
                "image_url": item["imageUrl"],
                "scramble": item.get("scramble", ""),
                "width": item["width"],
                "height": item["height"],
            })
        self.pages_data.sort(key=lambda x: x["sort"])

        print(f"  Total de páginas: {self.total_pages}")

        safe_series = re.sub(r'[\\/*?:"<>|]', "_", self.series_title).strip()
        safe_ep = re.sub(r'[\\/*?:"<>|]', "_", self.episode_title).strip()
        self.chapter_dir = self.output_dir / f"{safe_series} - {safe_ep}"
        self.chapter_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n[*] Baixando {len(self.pages_data)} páginas...\n")

        for page in self.pages_data:
            n = page["sort"] + 1
            final = self.chapter_dir / f"page_{n:03d}.png"

            if final.exists():
                print(f"  [{n:02d}/{self.total_pages}] Pulando: {final.name}")
                continue

            print(f"  [{n:02d}/{self.total_pages}] {final.name}", end="", flush=True)
            try:
                r = self.session.get(page["image_url"], timeout=60)
                r.raise_for_status()
                print(f" ({len(r.content)//1024}KB)", end="", flush=True)

                img = Image.open(io.BytesIO(r.content))
                if img.mode != "RGB":
                    img = img.convert("RGB")

                if page["scramble"]:
                    img = self._unscramble(img, page["scramble"])

                img.save(final, optimize=True)
                print()
            except Exception as e:
                print(f"  ERRO: {e}")

            time.sleep(0.3)

        print(f"\n✓ Download concluído em: {self.chapter_dir.resolve()}")

    def _unscramble(self, img, scramble_str):
        scramble = json.loads(scramble_str)
        if len(scramble) != 16:
            return img

        w, h = img.size
        g = 4
        pw, ph = w // g, h // g
        out = Image.new("RGB", (w, h))

        for i, source_idx in enumerate(scramble):
            sx = (source_idx // g) * pw
            sy = (source_idx % g) * ph
            piece = img.crop((sx, sy, sx + pw, sy + ph))
            dx = (i // g) * pw
            dy = (i % g) * ph
            out.paste(piece, (dx, dy))

        return out


def main():
    tips = Path(__file__).parent / "tips.txt"
    if not tips.exists():
        print("tips.txt não encontrado")
        sys.exit(1)

    # Read first line (ignore comments below)
    url = tips.read_text(encoding="utf-8").strip().split("\n")[0].strip()
    if not url:
        print("tips.txt está vazio")
        sys.exit(1)

    print(f"URL: {url}\n")
    YoungChampionScraper(url).run()


if __name__ == "__main__":
    main()
