/**
 * End-to-end test: send a CHAT_MESSAGE to the PM wrapper via the orchestrator
 * and print every reply we receive. This simulates exactly what the frontend
 * chat-page does.
 *
 * Usage:  bun run backend/sdk/test-e2e-chat.ts
 */
import WebSocket from 'ws';

const ORCH_URL = process.env.ORCHESTRATOR_URL ?? 'ws://localhost:9100';
const CLIENT_ID = 'test-client-1';

const ws = new WebSocket(ORCH_URL);

ws.on('open', () => {
	console.log(`Connected to orchestrator at ${ORCH_URL}`);

	// 1. Register as a test client so we can receive replies
	ws.send(JSON.stringify({
		type: 'REGISTER',
		id: CLIENT_ID,
		ts: Date.now(),
		payload: { name: 'Test Client', type: 'test' },
	}));
});

ws.on('message', (data) => {
	const env = JSON.parse(String(data));

	if (env.type === 'REGISTER_ACK') {
		console.log('Registered as', env.payload?.id);
		console.log('\nSending chat message: "Build me a dashboard with user analytics"\n');

		// 2. Send a CHAT_MESSAGE addressed to the PM wrapper
		ws.send(JSON.stringify({
			type: 'CHAT_MESSAGE',
			src: CLIENT_ID,
			dst: 'pm-1',
			ts: Date.now(),
			payload: { text: 'Build me a dashboard with user analytics' },
		}));
		return;
	}

	// 3. Print every envelope we receive back
	const ts = new Date(env.ts).toLocaleTimeString();
	console.log(`[${ts}] ${env.type} from ${env.src ?? '?'}:`);

	if (env.payload) {
		const preview = JSON.stringify(env.payload).slice(0, 500);
		console.log(`  ${preview}`);
	}
	console.log();
});

// Auto-close after 30s so the script doesn't hang forever
setTimeout(() => {
	console.log('\n--- 30s timeout reached, closing ---');
	ws.close();
	process.exit(0);
}, 30_000);
