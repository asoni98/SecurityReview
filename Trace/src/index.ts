import { Codex } from "@openai/codex-sdk";
import { readFileSync } from "fs";
import { runPrompt } from "./openaiClient.js";
import { buildStep1Prompt } from "../prompts/step1Analysis.js";

async function main() {
    /*
    uv run --with pydantic --with pydantic-ai --with openai \
    python3 analyze.py \
    --target ~/Documents/GitHub/infracourse/yoctogram-app-main \
    --max-findings 100 \
    --format json --output yoctogram.json
    */
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
    Start at ${filePath}:${line} in function ${function_name}. 
    Walk the code to build a complete stack trace of every function it calls (directly or indirectly). 
    For each call, show the call site with argument names/values and then paste the full body of the called function before continuing. 
    Skip external/framework calls once their bodies are unavailable.
    `;

    const codex = new Codex();
    const thread = codex.startThread();

    // Start the streamed run
    console.log("Running Trace Agent...");
    console.log(prompt);
    const resultStream = (await thread.runStreamed(prompt)).events;

    let finalResult = "";

    const currentTime = Date.now();
    // The SDK returns an async iterable of events
    while (true) {
        const event = await resultStream.next();

        // only update the final result if the event is a text event
        if (event?.value?.item?.text) {
            finalResult = event?.value?.item?.text ?? "";
        }

        if (!event.done) {
            console.log(event.value)
        }
        
        if (event.done) {
            console.log("Done!");
            break;
        }
        if (event.value.type === "error") {
            console.log("Error breaking ...");
            break;
        }

        // Stop if one step takes more than 3 minutes
        if (Date.now() - currentTime > 3 * 60 * 1000) {
            console.log("Timeout! Breaking ...");
            break;
        }
    }

    console.log("\n \n Stack Trace:\n", finalResult);

    const vulnerabilityAnalysisPrompt = buildStep1Prompt({ traceJson: finalResult });
    console.log("\n \n Vulnerability Analysis Prompt:\n", vulnerabilityAnalysisPrompt);

    console.log("Running VulnerabilityAnalysis of the trace...");
    const vulnerabilityAnalysisResult = await runPrompt(vulnerabilityAnalysisPrompt);
    console.log("\n \n Vulnerability Analysis Result:\n", vulnerabilityAnalysisResult);
}

export default main();
