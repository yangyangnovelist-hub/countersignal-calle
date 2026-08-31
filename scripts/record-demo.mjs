import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";

const outputDir = "video/build/browser";
await mkdir(outputDir, { recursive: true });
await mkdir("assets", { recursive: true });

const executablePath = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const browser = await chromium.launch({ headless: true, executablePath });
const demoUrl = process.env.COUNTERSIGNAL_DEMO_URL || "https://countersignal.vercel.app/";
const evidenceUrl =
  process.env.COUNTERSIGNAL_EVIDENCE_URL ||
  "https://yangyangnovelist-hub.github.io/countersignal-calle/";

async function addOutcome(page, name) {
  await page.getByRole("button", { name }).click();
  await page.waitForTimeout(300);
}

// Devpost recommends 3:2 gallery images. These use the same public demo a judge sees.
const stillContext = await browser.newContext({
  viewport: { width: 1200, height: 800 },
  colorScheme: "light",
});
const stillPage = await stillContext.newPage();
await stillPage.goto(demoUrl, { waitUntil: "networkidle" });
await stillPage.screenshot({ path: "assets/countersignal-cover.png" });
await addOutcome(stillPage, "+ Contradiction");
await addOutcome(stillPage, "+ Contradiction");
await addOutcome(stillPage, "+ Contradiction");
await stillPage.screenshot({ path: "assets/countersignal-decision.png" });
await stillContext.close();

const context = await browser.newContext({
  viewport: { width: 1280, height: 720 },
  recordVideo: { dir: outputDir, size: { width: 1280, height: 720 } },
  colorScheme: "light",
});
const page = await context.newPage();
const video = page.video();
const pause = (seconds) => page.waitForTimeout(seconds * 1000);

await page.goto(demoUrl, { waitUntil: "networkidle" });
await pause(12);
await page.locator(".grid").first().scrollIntoViewIfNeeded();
await pause(12);

await addOutcome(page, "+ Voicemail");
await pause(10);
await addOutcome(page, "+ Contradiction");
await pause(10);
await addOutcome(page, "+ Contradiction");
await pause(10);
await addOutcome(page, "+ Contradiction");
await pause(15);

await page.goto(evidenceUrl, { waitUntil: "networkidle" });
await pause(15);
await page.locator('[data-scenario="confirmation"]').click();
await pause(12);
await page.locator("#preview").click();
await pause(18);

await page.goto("https://github.com/CALLE-AI/awesome-phone-call-agents/pull/198", {
  waitUntil: "domcontentloaded",
});
await pause(18);
await page.goto("https://github.com/yangyangnovelist-hub/countersignal-calle", {
  waitUntil: "domcontentloaded",
});
await pause(20);

await page.close();
await context.close();
console.log(await video.path());
await browser.close();
