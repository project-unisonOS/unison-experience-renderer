import { chromium } from "playwright";
import AxeBuilder from "@axe-core/playwright";

const baseUrl = process.env.UNISON_RENDERER_TEST_URL || "http://127.0.0.1:8099";
const browser = await chromium.launch({ headless: true });
try {
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });

  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  if (results.violations.length) {
    throw new Error(`axe violations: ${results.violations.map((item) => item.id).join(", ")}`);
  }

  const required = [
    "bootstrapDisplayName",
    "bootstrapHousehold",
    "bootstrapUser",
    "bootstrapPassword",
    "bootstrapToken",
    "bootstrapConfirmed",
    "bootstrapCancel",
    "loginHandle",
    "loginPassword",
    "loginAction",
    "logoutAction",
    "lockAction",
    "recoveryAction",
    "recoveryCancel",
  ];
  for (const id of required) {
    const locator = page.locator(`#${id}`);
    if ((await locator.count()) !== 1) throw new Error(`missing semantic control: ${id}`);
  }

  await page.keyboard.press("Tab");
  const focused = await page.evaluate(() => document.activeElement?.id || document.activeElement?.tagName);
  if (!focused) throw new Error("keyboard focus did not enter the document");

  await page.emulateMedia({ reducedMotion: "reduce", forcedColors: "active" });
  const status = page.locator('#actionNote[role="status"][aria-live="polite"]');
  if ((await status.count()) !== 1) throw new Error("semantic live status is missing");
  console.log(`[PASS] Phase 1 renderer accessibility: axe=0, controls=${required.length}, first-focus=${focused}`);
} finally {
  await browser.close();
}
