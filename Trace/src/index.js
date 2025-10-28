import { Codex } from "@openai/codex-sdk";
import { createReadStream } from "fs";
import { createInterface } from "readline";
import { runPrompt } from "./openaiClient.js";
import { buildStep1Prompt } from "../prompts/step1Analysis.js";
async function processTaintedSourceLine(taintedSourceLine) {
    const { function_name, location, deployment_context } = taintedSourceLine;
    const filePath = location?.file_path ?? "unknown file";
    // console.log(filePath);
    const line = location?.line_number ?? "?";
    const context = JSON.stringify(taintedSourceLine, null, 2);
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
    // console.log("Running Trace Agent...");
    // console.log(prompt);
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
            // console.log(event.value)
        }
        if (event.done) {
            console.log("Done with the trace!");
            break;
        }
        if (event.value.type === "error") {
            console.log("Error breaking ...");
            console.log(event.value);
            break;
        }
        // Stop if one step takes more than 12 minutes
        if (Date.now() - currentTime > 12 * 60 * 1000) {
            console.log("Timeout! Breaking ...");
            break;
        }
    }
    console.log("\n\nStack Trace:\n", finalResult);
    const vulnerabilityAnalysisPrompt = buildStep1Prompt({
        traceJson: finalResult,
        deploymentContext: deployment_context ?? "",
    });
    // console.log("\n \n Vulnerability Analysis Prompt:\n", vulnerabilityAnalysisPrompt);
    console.log("Running Vulnerability Analysis of the trace...");
    const vulnerabilityAnalysisResult = await runPrompt(vulnerabilityAnalysisPrompt);
    console.log("\n\nVulnerability Analysis Result:\n", vulnerabilityAnalysisResult);
}
async function main() {
    const taintedSourcePath = process.argv[2] ?? "../taintedSources.txt";
    const stream = createReadStream(taintedSourcePath, { encoding: "utf8" });
    const rl = createInterface({
        input: stream,
        crlfDelay: Infinity,
    });
    try {
        for await (const rawLine of rl) {
            const line = rawLine.trim();
            if (!line)
                continue;
            try {
                const parsed = JSON.parse(line);
                await processTaintedSourceLine(parsed);
            }
            catch (error) {
                console.error("Failed to process line:", error);
            }
        }
    }
    finally {
        rl.close();
    }
}
export default main();
//# sourceMappingURL=index.js.map