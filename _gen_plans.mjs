import { spawn } from "child_process";
import fs from "fs";
import path from "path";

const SERVER_PATH = "C:\\Users\\Rrs computers\\AppData\\Roaming\\npm\\node_modules\\@testsprite\\testsprite-mcp\\dist\\index.js";
const PROJECT_DIR = "E:\\New folder (2)";
const API_KEY = "sk-user--mjQjMNoOJqhR2atmLLmxW-P--x1R4XFZoIrj5qSobBfXALiwdBmA9m2h_YUlqlVXV_NnFXqPglYPVSXeej6QnymK7bnf9-lrZhMPD_CN6hZWHxyOQhXaErzp3cukP5bKgE";

let msgId = 0;
const OUTPUT_DIR = path.join(PROJECT_DIR, "testsprite_tests");

function call(proc, method, params = {}) {
  return new Promise((resolve) => {
    const id = ++msgId;
    const req = JSON.stringify({ jsonrpc: "2.0", id, method, params });

    const listener = (data) => {
      const lines = data.toString().split("\n").filter(Boolean);
      for (const line of lines) {
        try {
          const msg = JSON.parse(line);
          if (msg.id === id) {
            proc.stdout.removeListener("data", listener);
            resolve(msg);
          }
        } catch {}
      }
    };

    proc.stdout.on("data", listener);
    proc.stdin.write(req + "\n");

    setTimeout(() => {
      proc.stdout.removeListener("data", listener);
      resolve({ error: "timeout", id });
    }, 300000);
  });
}

function extractText(content) {
  if (!content) return "";
  for (const c of content) {
    if (c.text) return c.text;
  }
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
    if (s.includes("[testsprite-mcp]")) return;
    process.stderr.write(s);
  });

  await new Promise((r) => setTimeout(r, 2000));

  try {
    // Step 1: Standardized PRD
    console.log("=== 1. Standardized PRD ===");
    const r1 = await call(proc, "tools/call", {
      name: "testsprite_generate_standardized_prd",
      arguments: { projectPath: PROJECT_DIR },
    });
    console.log(extractText(r1.result?.content).substring(0, 1500));
    fs.mkdirSync(path.join(OUTPUT_DIR, "tmp"), { recursive: true });
    fs.writeFileSync(path.join(OUTPUT_DIR, "tmp", "prd_output.txt"), extractText(r1.result?.content));

    // Step 2: Frontend test plan
    console.log("\n=== 2. Frontend test plan ===");
    const r2 = await call(proc, "tools/call", {
      name: "testsprite_generate_frontend_test_plan",
      arguments: { projectPath: PROJECT_DIR, needLogin: true },
    });
    console.log(extractText(r2.result?.content).substring(0, 1500));
    fs.writeFileSync(path.join(OUTPUT_DIR, "tmp", "fe_plan_output.txt"), extractText(r2.result?.content));

    const fePlan = path.join(OUTPUT_DIR, "testsprite_frontend_test_plan.json");
    if (fs.existsSync(fePlan)) console.log("✅ Frontend plan:", fs.statSync(fePlan).size, "bytes");

    // Step 3: Backend test plan
    console.log("\n=== 3. Backend test plan ===");
    const r3 = await call(proc, "tools/call", {
      name: "testsprite_generate_backend_test_plan",
      arguments: { projectPath: PROJECT_DIR, testType: "backend" },
    });
    console.log(extractText(r3.result?.content).substring(0, 1500));
    fs.writeFileSync(path.join(OUTPUT_DIR, "tmp", "be_plan_output.txt"), extractText(r3.result?.content));

    const bePlan = path.join(OUTPUT_DIR, "testsprite_backend_test_plan.json");
    if (fs.existsSync(bePlan)) console.log("✅ Backend plan:", fs.statSync(bePlan).size, "bytes");

    console.log("\n=== Plans done. Ready to execute ===");
  } catch (e) {
    console.error("Error:", e.message);
  }

  proc.stdin.end();
  setTimeout(() => proc.kill(), 3000);
}

main().catch(console.error);
