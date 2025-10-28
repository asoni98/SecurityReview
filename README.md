# SecurityReview

Full script run:
./run_security_pipeline.sh \
--code-path /Users/arunsoni/Documents/bedrock_code/webapp/apollo \
--infra-path /Users/arunsoni/Documents/bedrock_code/webapp/apollo/terraform/Webapp-main.yml \
--deployment-output ./tmp/bedrock-terraform.json \
--tainted-output ./tmp/taintedSources.txt

Full script run with a file already created with terraform understanding:
./run_security_pipeline.sh \
--code-path /Users/arunsoni/SecurityReview/yoctogram-app-main \
--deployment-override /Users/arunsoni/SecurityReview/deployment_understanding/yoctogram-gpt-5.json


To run generate_sources:
OPENAI_API_KEY=YOUR_KEY uv run --with pydantic --with pydantic-ai --with openai \
            python3 generate_sources/analyze.py \
            --target /Users/arunsoni/SecurityReview/yoctogram-app-main \
            --deployment-model /Users/arunsoni/SecurityReview/deployment_understanding/yoctogram-gpt-5.json \
            --debug-deployment --max-findings 100 \
            --format jsonl --output taintedSources.txt

To run Trace:
OPENAI_API_KEY=YOUR_KEY npm start