import OpenAI from "openai";

const client = new OpenAI();

export async function runPrompt(prompt: string): Promise<string> {
    const response = await client.responses.create({
        model: process.env.OPENAI_MODEL ?? "gpt-4.1-mini",
        input: prompt,
    });

    return response.output_text ?? JSON.stringify(response, null, 2);
}
