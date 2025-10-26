# SecurityReview

To run generate_sources:
OPENAI_API_KEY=YOUR_KEY uv run --with pydantic --with pydantic-ai --with openai \
            python3 generate_sources/analyze.py \
            --target /Users/arunsoni/SecurityReview/yoctogram-app-main \
            --deployment-model /Users/arunsoni/SecurityReview/deployment_understanding/yoctogram-gpt-5.json \
            --debug-deployment --max-findings 100 \
            --format jsonl --output taintedSources.txt

To run Trace:
OPENAI_API_KEY=YOUR_KEY npm start