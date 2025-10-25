import { Codex } from "@openai/codex-sdk";
import { runPrompt } from "./openaiClient.js";
import { buildStep1Prompt } from "../prompts/step1Analysis.js";
import {createReadStream} from "fs";
import {createInterface} from "readline";
import { Tail } from 'tail';

async function processFile(path: string): Promise<void> {
  const fileStream = createReadStream(path, { encoding: "utf8" });
  const rl = createInterface({ input: fileStream, crlfDelay: Infinity });

  for await (const line of rl) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    try {
      const data = JSON.parse(trimmed);
      await processTaintedSourceLine(data); // Sequentially await each async call
    } catch (err) {
      console.warn("⚠️ Invalid JSON line:", err);
    }
  }
}

async function processTaintedSourceLine(taintedSourceLine: any) {
    const { function_name, location } = taintedSourceLine;
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

        // Stop if one step takes more than 3 minutes
        if (Date.now() - currentTime > 3 * 60 * 1000) {
            console.log("Timeout! Breaking ...");
            break;
        }
    }

    console.log("\n\nStack Trace:\n", finalResult);

    const vulnerabilityAnalysisPrompt = buildStep1Prompt({ traceJson: finalResult });
    // console.log("\n \n Vulnerability Analysis Prompt:\n", vulnerabilityAnalysisPrompt);

    console.log("Running Vulnerability Analysis of the trace...");
    const vulnerabilityAnalysisResult = await runPrompt(vulnerabilityAnalysisPrompt);
    console.log("\n\nVulnerability Analysis Result:\n", vulnerabilityAnalysisResult);
}

async function main() {
    const taintedSourcePath = process.argv[2] ?? "../taintedSources.txt";

    // Create a new Tail instance
    const tail = new Tail(taintedSourcePath, {
        fromBeginning: false,  // Only read new lines (not existing content)
        follow: true,         // Continue watching for new lines
        logger: console,      // Optional: log errors to console
        useWatchFile: true,   // Use fs.watchFile for better reliability
        fsWatchOptions: {     // Optional: customize watch behavior
            interval: 1000    // Check every second
        }
    });


    // Process each new line
    tail.on('line', async (line: string) => {
        await processTaintedSourceLine(JSON.parse(line));
    });

    // Handle errors
    tail.on('error', (error: Error) => {
        console.error('Error:', error);
    });
    
    // Start watching
    console.log(`Watching ${taintedSourcePath} for new lines...`);
    
    // Graceful shutdown
    process.on('SIGINT', () => {
        console.log('\nStopping file watcher...');
        tail.unwatch();
        process.exit(0);
    });

    // Keep the process alive
    await new Promise(() => {});
}

export default main();
