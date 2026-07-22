#!/usr/bin/env sh
set -eu

python3 -m unittest discover -s module_01_identity_fundamentals -p 'test_*.py' -q
python3 -m unittest discover -s module_05_agent_to_agent_trust -p 'test_*.py' -q
python3 -m unittest discover -s docs -p 'test_*.py' -q

python3 docs/validate_provider_mapping.py module_07_aws_bedrock_agentcore_identity/provider-mapping.json
python3 docs/validate_provider_mapping.py module_08_microsoft_entra_agent_id/provider-mapping.json
python3 docs/validate_provider_mapping.py module_09_google_cloud_vertex_ai_iam/provider-mapping.json

mvn -q test
