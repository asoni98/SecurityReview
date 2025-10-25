import { Codex } from "@openai/codex-sdk";
import { readFileSync } from "fs";
import { runPrompt } from "./openaiClient.js";
import { buildStep1Prompt } from "../prompts/step1Analysis.js";

async function main() {
    const inputPath = process.argv[2] ?? "../yoctogramSmall.json";
    const index = Number(process.argv[3] ?? "0");
    const data = JSON.parse(readFileSync(inputPath, "utf8"));
    const finding = Array.isArray(data.findings) ? data.findings[index] : data;
    if (!finding) throw new Error(`No finding at index ${index}`);
    const { function_name, location } = finding;
    const filePath = location?.file_path ?? "unknown file";
    console.log(filePath);
    const line = location?.line_number ?? "?";
    const context = JSON.stringify(finding, null, 2);

    // Add pruning for irrelevant functions. 
    const prompt = `
    Finding context:
    ${context}
    
    Task:
    Start at ${filePath}:${line} in function ${function_name}. Walk the code to build a complete stack trace of every function it calls (directly or indirectly). For each call, show the call site with argument names/values and then paste the full body of the called function before continuing. Skip external/framework calls once their bodies are unavailable.
    `;

    const codex = new Codex();
    const thread = codex.startThread();
    const result = await thread.run(prompt);

    console.log(result);

    const result2 = await runPrompt(buildStep1Prompt({ traceJson: result.finalResponse }));
    console.log(result2);
}

export default main();
