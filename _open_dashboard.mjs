import { spawn } from "child_process";

const SERVER_PATH = "C:\\Users\\Rrs computers\\AppData\\Roaming\\npm\\node_modules\\@testsprite\\testsprite-mcp\\dist\\index.js";
const PROJECT_DIR = "E:\\New folder (2)";
const API_KEY = "sk-user--mjQjMNoOJqhR2atmLLmxW-P--x1R4XFZoIrj5qSobBfXALiwdBmA9m2h_YUlqlVXV_NnFXqPglYPVSXeej6QnymK7bnf9-lrZhMPD_CN6hZWHxyOQhXaErzp3cukP5bKgE";

let msgId = 0;

function call(proc, method, params = {}) {
  return new Promise((resolve) => {
    const id = ++msgId;
    const req = JSON.stringify({ jsonrpc: "2.0", id, method, params });
    const listener = (data) => {
      const lines = data.toString().split("\n").filter(Boolean);
      for (const line of lines) {
        try {
          const msg = JSON.parse(line);
          if (msg.id === id) { proc.stdout.removeListener("data", listener); resolve(msg); }
        } catch {}
      }
    };
    proc.stdout.on("data", listener);
    proc.stdin.write(req + "\n");
    setTimeout(() => { proc.stdout.removeListener("data", listener); resolve({ error: "timeout", id }); }, 30000);
  });
}

function extractText(content) {
  if (!content) return "";
  for (const c of content) { if (c.text) return c.text; }
  return JSON.stringify(content);
}

async function main() {
  const proc = spawn("node", [SERVER_PATH], {
    env: { ...process.env, API_KEY },
    stdio: ["pipe", "pipe", "pipe"],
    cwd: PROJECT_DIR,
  });

  proc.stderr.on("data", (c) => {
    const s = c.toString();
    if (!s.includes("[testsprite-mcp]")) process.stderr.write(s);
  });

  await new Promise((r) => setTimeout(r, 2000));

  try {
    console.log("=== Opening Test Result Dashboard ===\n");
    const result = await call(proc, "tools/call", {
      name: "testsprite_open_test_result_dashboard",
      arguments: {
        projectPath: PROJECT_DIR,
        modificationContext: "Review frontend test results for Claudiya.ai fraud detection platform. Tests cover: dashboard KPIs, agent status, transaction search, threat feed, admin panel, data generation flow, and error handling pages.",
      },
    });

    console.log(JSON.stringify(result, null, 2));
  } catch (e) {
    console.error("Error:", e.message);
  }

  proc.stdin.end();
  setTimeout(() => proc.kill(), 3000);
}

main().catch(console.error);
