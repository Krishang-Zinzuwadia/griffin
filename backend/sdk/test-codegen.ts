/**
 * End-to-end test: send a chat message and verify CODE_ARTIFACT events arrive.
 * Usage: bun run --env-file=.env backend/sdk/test-codegen.ts
 */

const ORCH_URL = process.env.ORCHESTRATOR_URL ?? 'ws://localhost:9100';

const ws = new WebSocket(ORCH_URL);
let registered = false;
const artifacts: Array<{ filename: string; language: string; type: string; codeLength: number }> = [];

ws.onopen = () => {
	console.log('[test] connected to orchestrator');
	ws.send(JSON.stringify({
		type: 'REGISTER',
		id: 'test-codegen-1',
		payload: { name: 'CodeGen Test', type: 'test' },
		ts: Date.now(),
	}));
};

ws.onmessage = (event: MessageEvent) => {
	const env = JSON.parse(String(event.data)) as Record<string, unknown>;
	const payload = env.payload as Record<string, unknown> | undefined;

	if (env.type === 'REGISTER_ACK') {
		registered = true;
		console.log('[test] registered. Sending chat message…');

		// Send a design request via the PM
		ws.send(JSON.stringify({
			type: 'EVENT',
			src: 'test-codegen-1',
			dst: 'pm-1',
			ts: Date.now(),
			payload: {
				kind: 'CHAT_MESSAGE',
				text: 'Create a seller dashboard for a shopping app with sales charts and recent orders table',
				messageId: `test-${Date.now()}`,
			},
		}));
		return;
	}

	if (env.type !== 'EVENT' || !payload) return;

	const kind = String(payload.kind ?? '');

	if (kind === 'CHAT_RESPONSE') {
		console.log('\n[PM Reply]', String(payload.text ?? '').slice(0, 200));
	}

	if (kind === 'CODE_ARTIFACT') {
		const art = payload.artifact as Record<string, unknown> | undefined;
		if (art) {
			const code = String(art.code ?? '');
			artifacts.push({
				filename: String(art.filename ?? 'unknown'),
				language: String(art.language ?? 'unknown'),
				type: String(art.type ?? 'unknown'),
				codeLength: code.length,
			});
			console.log(`\n[CODE_ARTIFACT] ${art.filename} (${art.language}, ${code.length} chars, type: ${art.type})`);
			console.log('--- first 300 chars ---');
			console.log(code.slice(0, 300));
			console.log('--- end ---\n');
		}
	}

	if (kind === 'AGENT_MESSAGE') {
		console.log(`[Agent: ${payload.agent}]`, String(payload.text ?? '').slice(0, 200));
	}
};

ws.onerror = (err) => {
	console.error('[test] WS error:', err);
};

ws.onclose = () => {
	console.log('[test] disconnected');
};

// Quit after 30 seconds
setTimeout(() => {
	console.log('\n=== SUMMARY ===');
	console.log(`Received ${artifacts.length} code artifact(s):`);
	for (const a of artifacts) {
		console.log(`  - ${a.filename} (${a.language}, ${a.type}, ${a.codeLength} chars)`);
	}
	console.log(artifacts.length > 0 ? '\n Code generation pipeline working!' : '\n❌ No code artifacts received.');
	ws.close();
	process.exit(artifacts.length > 0 ? 0 : 1);
}, 30_000);
