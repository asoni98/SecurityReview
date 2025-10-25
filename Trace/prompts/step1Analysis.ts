interface BuildStep1PromptParams {
    traceJson: string;
}

export function buildStep1Prompt({
    traceJson,
}: BuildStep1PromptParams): string {
    return `You are an Security Vulnerability expert.
We found that the attacker modified the code to cause a security vulnerability,
and we are not sure which function was modified and vulnerable.
Your task is to analyze functions for potential security vulnerabilities where
attacker-controlled data could be exploited.

<analysis_process>
1. Examine the function signature and parameters
2. Trace data flow from parameters through the function
3. Identify potential sink points where data is used in sensitive operations
4. Analyze the context and security implications
</analysis_process>

<thinking>
<data_flow_analysis>
- What parameters could be attacker-controlled?
- How is the data processed before reaching sensitive operations?
</data_flow_analysis>

<security_analysis>
- What security checks or validations are present/missing?
- Only consider the security violation that is caught by the given sanitizers.
</security_analysis>


<vulnerability_decision>
- Is there a clear path from attacker input to sensitive operation?
- Can you identify the exact line where the vulnerability exists?
</vulnerability_decision>
</thinking>

<trace_json>
${traceJson}
</trace_json>

<output_format>
{
    "sink_analysis_message": "Detailed explanation of your findings about the sink with arguments",
    "is_vulnerable": true/false,
    "sink_line": "Exact line of code where vulnerability exists",
    "sink_line_number": "Line number of the sink_line",
    "sanitizer_candidates": "A list of sanitizer candidates that
    are triggered by the potential vulnerability.
    If no vulnerability is found, return an empty list.",
    "callsites": [{
        "name": "the function or method Name of callee",
        "tainted_args": [list of indices of tainted arguments of the callee.
        0-indexed. If not tainted, return an empty list],
        "line_range": ((start_row, start_col), (end_row, end_col)), # It is only
        for a single callsite.
        "priority": "set priority of the callee to 0 if it is the most important
        callee to analyze. 1 is the second most important, and so on."
    }},
}
</output_format>

Return the output_format in JSON format.

<critical_requirements>
- If the code has comment mentioning that it resolves a vulnerability, FOCUS THE
PART OF THE CODE as it may fix the vulnerability improperly, or fake comment by
the attacker.
- If is_vulnerable is true, sink_line MUST contain the exact vulnerable line of code
- If is_vulnerable is false, sink_line should be an empty string, and sink_line_number
should be -1
- sink_line must be copied exactly from the input code without
the line number, no modifications
- Never return is_vulnerable as true without a specific sink_line
- "callsites" must include all the callees that are tainted by the function's
  tainted arguments.
- If all arguments are tainted, "callsites" must include all the callees.
- If the callee's argument is tainted, the return value of the callee is also
tainted, so if other callees use the return value as an argument, they are also
tainted.
- Don't analyze callees recursively. Focus on the current function.
</critical_requirements>`;
}
