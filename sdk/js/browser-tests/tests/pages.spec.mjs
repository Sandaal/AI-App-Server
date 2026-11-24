import { test, expect } from "@playwright/test";
import fs from "node:fs";

// The server half (scripts/e2e-browser-server.sh) deploys:
//   kb    ui: chat-widget, a streaming /chat on a fake model ("tok0 tok1 ...")
//   kbui  ui: ./ui, a page of its own with <aiapp-chat> from /_sdk/aiapp.js
// and starts `aiapp console`, writing its link to /out/console.txt.

test("the built-in chat page streams an answer", async ({ page }) => {
  await page.goto("/apps/kb/");
  await page.fill("#input", "How many days of leave?");
  await page.click("#send");
  await expect(page.locator("#log")).toContainText("tok0 tok1 tok2", { timeout: 15_000 });
  await expect(page.locator("#log")).toContainText("How many days of leave?");
});

test("<aiapp-chat> on the app's own page streams an answer", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/apps/kbui/");
  const chat = page.locator("aiapp-chat");
  await expect(chat).toBeVisible();
  await chat.locator("textarea").fill("What about remote work?");
  await chat.locator("button").click();
  await expect(chat.locator(".log")).toContainText("tok0 tok1 tok2", { timeout: 15_000 });
  expect(errors).toEqual([]);
});

test("the console shows apps, model calls, the audit log and acts", async ({ page }) => {
  const link = fs.readFileSync("/out/console.txt", "utf8").match(/http:\/\/127\.0\.0\.1:\d+\/[0-9a-f]+\//)[0];
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(link);
  await expect(page.locator("#mode")).toHaveText("local console");
  await expect(page.locator("nav")).toContainText("kb");
  await page.locator("nav button", { hasText: "kbui" }).click();
  await expect(page.locator("h2")).toHaveText("kbui");
  await page.locator("nav button", { hasText: /^kb\s/ }).click();
  await expect(page.locator(".cards")).toContainText("Version");
  await page.locator(".tabs button", { hasText: "Model calls" }).click();
  await expect(page.locator("#body")).toContainText("model calls from the audit log");
  await page.locator(".tabs button", { hasText: "Cron" }).click();
  const run = page.locator("button[data-act]", { hasText: "Run now" });
  await expect(run).toBeVisible();
  await run.click(); // POST through ConsoleClient with the CSRF header
  await page.locator(".tabs button", { hasText: "Jobs" }).click();
  await expect(page.locator("#body")).toContainText("nightly", { timeout: 10_000 });
  await page.locator("nav button", { hasText: "Audit log" }).click();
  await expect(page.locator("main")).toContainText("Newest records");
  await expect(page.locator("main")).toContainText("model_chat");
  await page.locator("nav button", { hasText: "Recent requests" }).click();
  await expect(page.locator("main table")).toContainText("kb");
  expect(errors).toEqual([]);
});
