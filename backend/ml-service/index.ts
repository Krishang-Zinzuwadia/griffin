import { spawn } from 'child_process';
import { createServer } from 'http';
import WebSocket, { WebSocketServer } from 'ws';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const PORT = Number(process.env.ML_SERVICE_PORT ?? '9100');

interface Message {
	type: 'prompt' | 'progress' | 'complete' | 'error';
	data: string;
	githubUrl?: string;
	projectName?: string;
}

const httpServer = createServer((req, res) => {
	res.writeHead(200, { 'Content-Type': 'text/plain', 'Access-Control-Allow-Origin': '*' });
	res.end('ML Service Running');
});

const wss = new WebSocketServer({ server: httpServer });

console.log(`ML Service starting on ws://0.0.0.0:${PORT}`);

wss.on('connection', (ws: WebSocket) => {
	console.log('Frontend connected');

	ws.on('message', (data: WebSocket.RawData) => {
		let msg: Message;
		try {
			msg = JSON.parse(String(data));
		} catch {
			console.warn('Invalid message:', String(data));
			return;
		}

		if (msg.type === 'prompt') {
			const prompt = msg.data;
			console.log(`Received prompt: "${prompt}"`);

			// Send acknowledgment
			ws.send(JSON.stringify({
				type: 'progress',
				data: `Starting ML pipeline for: "${prompt}"\n\nThis will take 30-60 seconds...`,
			}));

			// Execute Python ML pipeline
			const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

			// Project root is 2 directories up from backend/ml-service
			const projectRoot = resolve(__dirname, '..', '..');

			console.log(`Running from: ${projectRoot}`);

			const mlProcess = spawn(pythonCmd, ['-m', 'ML.main', prompt], {
				cwd: projectRoot,
				env: { ...process.env },
				shell: true,
				windowsHide: true, // Hide console window on Windows
			});

			let stdoutBuffer = '';
			let stderrBuffer = '';
			let processExited = false;

			mlProcess.stdout.on('data', (chunk: Buffer) => {
				const text = chunk.toString('utf-8');
				stdoutBuffer += text;

				// Send all output to terminal
				const lines = text.split('\n').filter((line) => line.trim());
				for (const line of lines) {
					const cleanLine = line.replace(/\x1b\[[0-9;]*m/g, ''); // Strip ANSI

					// Structured live events from the pipeline (office status, etc.)
					if (cleanLine.startsWith('@@GRIFFIN_EVENT ')) {
						try {
							const evt = JSON.parse(cleanLine.slice('@@GRIFFIN_EVENT '.length));
							if (evt && evt.kind === 'office_status') {
								ws.send(JSON.stringify({ type: 'office_status', data: evt }));
							}
						} catch {
							// Ignore malformed event lines
						}
						continue; // Do not echo the raw marker to the terminal
					}

					// Send to terminal
					ws.send(JSON.stringify({ type: 'terminal', data: cleanLine }));

					// Also send important lines as progress
					if (line.includes('OFFICE') || line.includes('✅') || line.includes('⏳')) {
						ws.send(JSON.stringify({ type: 'progress', data: cleanLine }));
					}

					// Forward cost/token data from Cost Optimizer office
					if (line.includes('COST OPTIMIZER') || line.includes('Token usage:') || line.includes('💰') || line.includes('💵')) {
						ws.send(JSON.stringify({ type: 'cost_update', data: cleanLine }));
					}

					// Detect per-call token usage lines from the tracker
					if (line.includes('Token usage:') && line.includes('cost=$')) {
						const tokenMatch = cleanLine.match(/\[([^\]]+)\] Token usage: in=(\d+), out=(\d+), cost=\$([0-9.]+), latency=([0-9.]+)s/);
						if (tokenMatch) {
							ws.send(JSON.stringify({
								type: 'token_usage',
								data: {
									office: tokenMatch[1] ?? 'unknown',
									input_tokens: parseInt(tokenMatch[2] ?? '0', 10),
									output_tokens: parseInt(tokenMatch[3] ?? '0', 10),
									cost_usd: parseFloat(tokenMatch[4] ?? '0'),
									latency_s: parseFloat(tokenMatch[5] ?? '0'),
								},
							}));
						}
					}
				}
			});

			mlProcess.stderr.on('data', (chunk: Buffer) => {
				const text = chunk.toString('utf-8');
				stderrBuffer += text;

				// Send stderr to terminal as well
				const lines = text.split('\n').filter((line) => line.trim());
				for (const line of lines) {
					const cleanLine = line.replace(/\x1b\[[0-9;]*m/g, '');
					ws.send(JSON.stringify({ type: 'terminal', data: `[ERROR] ${cleanLine}` }));
				}
			});

			mlProcess.on('close', (code) => {
				if (processExited) return; // Prevent double execution
				processExited = true;

				// Clean up process references to avoid Windows handle errors
				try {
					mlProcess.stdout?.removeAllListeners();
					mlProcess.stderr?.removeAllListeners();
					mlProcess.removeAllListeners();
					mlProcess.kill(); // Ensure process is terminated
				} catch (err) {
					// Ignore cleanup errors
				}

				if (code === 0) {
					// Extract GitHub URL
					const githubMatch = stdoutBuffer.match(/GitHub URL: (https:\/\/github\.com\/[^\s]+)/);
					const githubUrl = githubMatch?.[1] ?? null;

					// Extract project name
					const nameMatch = stdoutBuffer.match(/Project Name:\s*([^\n]+)/);
					const projectName = nameMatch?.[1]?.trim() ?? 'Generated Project';

					// Extract file count
					const filesMatch = stdoutBuffer.match(/Files created:\s*(\d+)/);
					const fileCount = filesMatch?.[1] ? parseInt(filesMatch[1], 10) : 0;

					// Extract file list from output (look for "Wrote {filename}" lines)
					const fileMatches = stdoutBuffer.matchAll(/\[DEVOPS\] Wrote (.+)/g);
					const files: string[] = [];
					for (const match of fileMatches) {
						if (match[1]) {
							files.push(match[1]);
						}
					}

					// Send file artifacts for workstation
					files.forEach((filepath) => {
						const ext = filepath.split('.').pop() || 'txt';
						const langMap: Record<string, string> = {
							'js': 'javascript',
							'ts': 'typescript',
							'tsx': 'typescript',
							'jsx': 'javascript',
							'py': 'python',
							'html': 'html',
							'css': 'css',
							'json': 'json',
							'md': 'markdown',
						};

						ws.send(JSON.stringify({
							type: 'file',
							data: {
								filename: filepath,
								language: langMap[ext] || 'plaintext',
								path: filepath,
							},
						}));
					});

					const successMsg = githubUrl
						? `Project complete! **${projectName}** deployed with ${fileCount} files.\n\n[View on GitHub](${githubUrl})`
						: `Project complete! **${projectName}** generated with ${fileCount} files. Check ML/sandbox/`;

					ws.send(JSON.stringify({
						type: 'complete',
						data: successMsg,
						githubUrl: githubUrl || undefined,
						projectName,
						files,
					}));

					console.log(`Pipeline complete: ${projectName}`);
				} else {
					const errorMsg = stderrBuffer || 'ML pipeline failed with unknown error';
					ws.send(JSON.stringify({
						type: 'error',
						data: `ML pipeline failed: ${errorMsg.slice(0, 200)}`,
					}));
					console.error(`Pipeline failed:`, errorMsg);
				}
			});

			mlProcess.on('error', (err) => {
				if (processExited) return;
				processExited = true;

				ws.send(JSON.stringify({
					type: 'error',
					data: `Failed to start ML pipeline: ${err.message}. Make sure Python is installed.`,
				}));
				console.error('Spawn error:', err);

				// Clean up
				try {
					mlProcess.kill();
				} catch { }
			});
		}
	});

	ws.on('close', () => {
		console.log('Frontend disconnected');
	});

	ws.on('error', (err) => {
		console.error('WebSocket error:', err);
	});
});

httpServer.listen(PORT, () => {
	console.log(`ML Service ready on ws://0.0.0.0:${PORT}`);
});
