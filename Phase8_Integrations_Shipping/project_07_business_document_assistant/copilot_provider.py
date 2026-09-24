"""Optional direct Copilot integration. No model tools or external publication."""
import asyncio
import importlib.util
import json
import os
import shutil
import tempfile
from domain import copilot_brief, generate


class CopilotUnavailable(ValueError):
    pass


def settings():
    executable = os.environ.get('BDA_COPILOT_CLI', '')
    model = os.environ.get('BDA_COPILOT_MODEL', '')
    enabled = os.environ.get('BDA_COPILOT_ENABLED') == '1'
    ready = bool(enabled and model and executable and shutil.which(executable)
                 and importlib.util.find_spec('copilot'))
    return {'configured': ready, 'model': model if ready else None,
            'message': ('Copilot SDK configured; authentication is checked when generating.' if ready else
                        'Copilot is not configured on this server. Use the fictional offline demo or ask the administrator to connect Copilot.')}


async def _generate(request):
    from copilot import CopilotClient
    from copilot.client import RuntimeConnection
    from copilot.rpc import PermissionDecisionReject
    # An empty workspace prevents project instructions from entering the prompt.
    with tempfile.TemporaryDirectory(prefix='bda-copilot-') as work:
        async with CopilotClient(
            connection=RuntimeConnection.for_stdio(path=os.environ['BDA_COPILOT_CLI']),
            working_directory=work, base_directory=work,
            mode='empty', use_logged_in_user=True,
        ) as client:
            async with await client.create_session(
                model=os.environ['BDA_COPILOT_MODEL'], available_tools=[], tools=[],
                skip_custom_instructions=True, custom_agents_local_only=True,
                on_permission_request=lambda *_: PermissionDecisionReject(feedback='Document drafting has no tool permissions.'),
            ) as session:
                event = await session.send_and_wait(copilot_brief(request), timeout=120)
                content = event.data.content if event else None
                if not isinstance(content, str) or len(content) > 300000:
                    raise ValueError('Missing or oversized Copilot response.')
                result = json.loads(content)
                if not isinstance(result, dict) or set(result) != {'sections'} or not isinstance(result['sections'], list):
                    raise ValueError('Invalid document response.')
                doc = generate(request, result['sections'])
                doc.update(provider='copilot-sdk', model=os.environ['BDA_COPILOT_MODEL'])
                return doc


def draft(request):
    if not settings()['configured']:
        raise CopilotUnavailable(settings()['message'])
    async def bounded():
        return await asyncio.wait_for(_generate(request), timeout=150)
    return asyncio.run(bounded())
