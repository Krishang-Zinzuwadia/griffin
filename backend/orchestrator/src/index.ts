import { createServer } from 'http';
import { createConnection } from 'net';
import WebSocket, { WebSocketServer } from 'ws';
import type { Envelope } from './types';
import { findWrapper, listWrappers, markHeartbeat, pruneStaleWrappers, removeWrapper, upsertWrapper } from './registery';

const basePort = Number(process.env.ORCHESTRATOR_PORT ?? '9100');
const MAX_BIND_ATTEMPTS = 10;

/**
 * Check whether a TCP port is already in use.
 * Resolves true if something is listening, false if available.
 */
function isPortInUse(port: number): Promise<boolean> {
	return new Promise((resolve) => {
		const sock = createConnection({ port, host: '127.0.0.1' });
		sock.once('connect', () => {
			sock.destroy();
			resolve(true);
		});
		sock.once('error', () => {
			resolve(false);
		});
	});
}

/**
 * Find the first free port starting from `basePort`.
 */
async function findFreePort(start: number, attempts: number): Promise<number> {
	for (let i = 0; i < attempts; i++) {
		const port = start + i;
		const inUse = await isPortInUse(port);
		if (!inUse) return port;
		console.warn(`Port ${port} is in use — trying ${port + 1} (attempt ${i + 1}/${attempts})`);
	}
	throw new Error(`No free port found in range ${start}–${start + attempts - 1}. Free a port or set ORCHESTRATOR_PORT.`);
}

/** Boot the orchestrator on the first available port. */
async function boot(): Promise<void> {
	const port = await findFreePort(basePort, MAX_BIND_ATTEMPTS);

	/** HTTP server so we can expose /status alongside the WS upgrade. */
	const httpServer = createServer((req, res) => {
		if (req.url === '/status') {
			const snapshot = listWrappers().map((r) => ({
				id: r.id,
				type: r.type,
				status: r.status,
				lastSeen: r.lastSeen,
				meta: r.meta,
			}));
			res.writeHead(200, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' });
			res.end(JSON.stringify({ wrappers: snapshot }));
			return;
		}
		res.writeHead(404);
		res.end();
	});

	const wss = new WebSocketServer({ server: httpServer });

	httpServer.listen(port, () => {
		console.log(`Orchestrator running on ws://0.0.0.0:${port}  (HTTP /status also available)`);
	});

	/**
	 * Safely send an envelope over a WebSocket connection.
	 */
	function send(ws: WebSocket, msg: Envelope<unknown>): void {
		try {
			ws.send(JSON.stringify(msg));
		} catch (error) {
			console.error('send error', error);
		}
	}

	wss.on('connection', (ws: WebSocket) => {
		let entryId: string | undefined;

		ws.on('message', (data: WebSocket.RawData) => {
			let env: Envelope<unknown>;
			try {
				env = JSON.parse(String(data)) as Envelope<unknown>;
			} catch (error) {
				console.warn('invalid message', String(data));
				return;
			}

			switch (env.type) {
				case 'REGISTER': {
					const id = env.id || `w-${Math.random().toString(36).slice(2, 9)}`;
					entryId = id;
					const meta = (env.payload ?? { name: 'unknown', type: 'unknown' }) as Record<string, unknown>;
					upsertWrapper(id, { name: String(meta.name ?? id), type: String(meta.type ?? 'unknown') }, ws);
					console.log(`REGISTER: ${id}`, env.payload ?? {});
					send(ws, { type: 'REGISTER_ACK', id, ts: Date.now(), payload: { id } });
					break;
				}
				case 'HEARTBEAT': {
					const id = env.src;
					if (id) {
						markHeartbeat(id);
						send(ws, { type: 'HEARTBEAT_ACK', src: 'orchestrator', dst: id, ts: Date.now() });
					}
					break;
				}
				case 'EVENT': {
					if (env.dst) {
						const target = findWrapper(env.dst);
						if (target) send(target.socket, env);
					} else {
						for (const record of broadcastTargets()) {
							if (record.id === env.src) continue;
							send(record.socket, env);
						}
					}
					break;
				}
				case 'SHUTDOWN': {
					if (entryId) {
						removeWrapper(entryId);
						ws.close();
					}
					break;
				}
				default: {
					// Route dst-targeted messages of any type (e.g. DESIGN_BRIEF, API_BRIEF)
					if (env.dst) {
						const target = findWrapper(env.dst);
						if (target) send(target.socket, env);
					} else {
						console.log('recv', env.type, env);
					}
				}
			}
		});

		ws.on('close', () => {
			if (entryId) {
				console.log('disconnected', entryId);
			}
		});
	});

	/**
	 * Return all live wrappers (pruning stale ones as a side-effect).
	 */
	function broadcastTargets(): ReturnType<typeof listWrappers> {
		pruneStaleWrappers(30_000);
		return listWrappers();
	}

	// periodic stale-check (30s timeout to match heartbeat every 2s).
	setInterval(() => {
		const removed = pruneStaleWrappers(30_000);
		if (removed.length > 0) {
			console.log('stale heartbeat, removing', removed.join(', '));
		}
	}, 10_000);
}

boot().catch((err) => {
	console.error(err);
	process.exit(1);
});
