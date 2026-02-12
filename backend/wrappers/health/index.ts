import { type Envelope, WrapperClient } from '../../sdk/client';

const orchestratorUrl = process.env.ORCHESTRATOR_URL ?? 'ws://localhost:9100';
const wrapperId = 'health-1';

/**
 * Entry point for the health wrapper. Connects to the orchestrator,
 * registers itself, sends heartbeats, and logs/responds to events.
 */
async function main(): Promise<void> {
	const client = new WrapperClient(
		orchestratorUrl,
		{ name: 'health', type: 'health', drones: 1 },
		(env: Envelope<unknown>) => {
			console.log('[health wrapper] event', env.type, env.payload ?? null);
			if (env.type === 'PING') {
				client.send({
					type: 'EVENT',
					src: wrapperId,
					dst: env.src,
					ts: Date.now(),
					payload: { pong: true },
				});
			}
		}
	);

	await client.connect();
	await client.register(wrapperId);

	process.on('SIGINT', () => {
		console.log('shutting down health wrapper');
		client.send({ type: 'SHUTDOWN', src: wrapperId, ts: Date.now() });
		client.close();
		process.exit(0);
	});
}

main().catch((error: unknown) => {
	console.error('health wrapper failed', error);
	process.exit(1);
});
