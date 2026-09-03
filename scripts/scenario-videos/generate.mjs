/**
 * ASGuard scenario-video generator.
 *
 * Records one video per security-test category by driving explainer.html
 * at human speed in a Playwright browser context with video recording.
 *
 * Usage:
 *   node generate.mjs            # generate all category videos
 *   node generate.mjs pi         # only categories whose key contains "pi"
 */
import { chromium } from "playwright";
import { mkdirSync, readFileSync, readdirSync, rmSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = join(HERE, "..", "..", "videos", "scenarios");
const TMP_DIR = join(HERE, ".recordings");
const EXPLAINER_URL = "file://" + join(HERE, "explainer.html");

const filter = process.argv[2] ?? "";
const data = JSON.parse(readFileSync(join(HERE, "verdicts.json"), "utf-8"));

mkdirSync(OUT_DIR, { recursive: true });
mkdirSync(TMP_DIR, { recursive: true });

const browser = await chromium.launch();
const total = data.categories.length;

for (let i = 0; i < total; i++) {
  const cat = data.categories[i];
  if (filter && !cat.key.includes(filter)) continue;

  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: { dir: TMP_DIR, size: { width: 1280, height: 720 } },
  });
  const page = await context.newPage();
  await page.goto(EXPLAINER_URL);
  await page.evaluate((d) => window.__driver.setData(d), {
    ...cat,
    index: i,
    totalCategories: total,
  });

  console.log(`[${i + 1}/${total}] recording: ${cat.key} (${cat.total} cases)`);
  await page.evaluate(() => window.__driver.showIntro());
  await page.evaluate(() => window.__driver.showHow());

  for (let c = 0; c < cat.total; c++) {
    await page.evaluate((idx) => window.__driver.showCase(idx), c);
    await page.evaluate((idx) => window.__driver.typeInput(idx), c);
    await page.evaluate((idx) => window.__driver.runPipeline(idx), c);
    await page.evaluate((idx) => window.__driver.showVerdict(idx), c);
    await page.waitForTimeout(600);
  }

  await page.evaluate(() => window.__driver.showOutro());
  await page.waitForTimeout(400);

  const video = page.video();
  await context.close();
  const out = join(OUT_DIR, `${String(i + 1).padStart(2, "0")}-${cat.key}.webm`);
  await video.saveAs(out);
  console.log(`   saved ${out}`);
}

await browser.close();
rmSync(TMP_DIR, { recursive: true, force: true });
console.log("done.");
