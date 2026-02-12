import { type Envelope, WrapperClient } from '../../sdk/client';
import { chatCompletion, isLlmConfigured } from '../../sdk/llm-client';

const orchestratorUrl = process.env.ORCHESTRATOR_URL ?? 'ws://localhost:9100';
const wrapperId = 'backend-api-1';

type StatusValue = 'IDLE' | 'THINKING' | 'WORKING' | 'BLOCKED';

let currentStatus: StatusValue = 'IDLE';

/**
 * Emit a STATUS_UPDATE event so the orchestrator (and UI) can display the
 * current state of the backend-api wrapper.
 */
function emitStatus(client: WrapperClient, status: StatusValue): void {
	currentStatus = status;
	client.send({
		type: 'EVENT',
		src: wrapperId,
		ts: Date.now(),
		payload: { kind: 'STATUS_UPDATE', status },
	});
}

interface CodeArtifact {
	filename: string;
	language: string;
	code: string;
}

/** System prompt for generating an Express/Hono-style API route file. */
const API_CODEGEN_PROMPT = `You are a senior backend engineer.
Given a feature request, generate a complete API route file.

RULES:
1. Output ONLY valid JSON — no markdown, no fences, no explanation.
2. JSON schema:
   {
     "filename": "api-users.ts",
     "language": "typescript",
     "code": "...full route source..."
   }
3. Write a self-contained TypeScript module that exports route handlers.
4. Use plain functions (no framework imports needed) — the preview will display the code.
5. Include realistic mock data and typed interfaces.
6. Include GET, POST, PUT, DELETE handlers where appropriate.
7. Add JSDoc comments on each handler.
8. Keep it under 120 lines.`;

/** System prompt for generating a SQL schema file. */
const SCHEMA_CODEGEN_PROMPT = `You are a senior database architect.
Given a feature request, generate a complete SQL schema file.

RULES:
1. Output ONLY valid JSON — no markdown, no fences, no explanation.
2. JSON schema:
   {
     "filename": "schema-users.sql",
     "language": "sql",
     "code": "...full SQL source..."
   }
3. Use PostgreSQL syntax.
4. Include CREATE TABLE, indexes, and constraints.
5. Add comments explaining each table.
6. Include realistic column types and defaults.
7. Keep it under 80 lines.`;

/**
 * Extract a JSON object from LLM output that may contain markdown fences,
 * preamble text, backtick-wrapped values, or unescaped newlines.
 */
function extractJson(raw: string): string {
	let text = raw;
	const fenceMatch = raw.match(/```(?:json)?\s*([\s\S]*?)```/);
	const fenceGroup = fenceMatch?.[1];
	if (fenceGroup) text = fenceGroup.trim();

	const start = text.indexOf('{');
	const end = text.lastIndexOf('}');
	if (start === -1 || end <= start) return text.trim();

	let json = text.slice(start, end + 1);

	// Fix backtick-wrapped values
	json = json.replace(
		/:\s*`([\s\S]*?)`(\s*[,}])/g,
		(_match, content: string, trailing: string) => {
			const escaped = content
				.replace(/\\/g, '\\\\')
				.replace(/"/g, '\\"')
				.replace(/\n/g, '\\n')
				.replace(/\r/g, '\\r')
				.replace(/\t/g, '\\t');
			return `: "${escaped}"${trailing}`;
		},
	);

	// Fix unescaped newlines inside double-quoted strings
	let result = '';
	let inString = false;
	let escaped = false;
	for (let i = 0; i < json.length; i++) {
		const ch = json[i];
		if (escaped) { result += ch; escaped = false; continue; }
		if (ch === '\\' && inString) { escaped = true; result += ch; continue; }
		if (ch === '"') { inString = !inString; result += ch; continue; }
		if (inString && ch === '\n') { result += '\\n'; continue; }
		if (inString && ch === '\r') { result += '\\r'; continue; }
		if (inString && ch === '\t') { result += '\\t'; continue; }
		result += ch;
	}

	return result;
}

/** Sanitize a resource string into a valid identifier. */
function toIdentifier(resource: string): string {
	return resource
		.replace(/[^a-zA-Z0-9 ]/g, '')
		.split(/\s+/)
		.map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
		.join('')
		.slice(0, 30) || 'Item';
}

/** Sanitize a resource string into a kebab-case filename. */
function toFilename(resource: string): string {
	return resource
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-|-$/g, '')
		.slice(0, 40) || 'items';
}

/**
 * Generate an API route file — uses LLM when configured, otherwise mock.
 */
async function generateApiCode(payload: Record<string, unknown>): Promise<CodeArtifact> {
	const resource = String(payload.resource ?? 'items');

	if (isLlmConfigured('specialist')) {
		try {
			const raw = await chatCompletion(
				[
					{ role: 'system', content: API_CODEGEN_PROMPT },
					{ role: 'user', content: resource },
				],
				{ tier: 'specialist', temperature: 0.5, maxTokens: 2048 },
			);
			const jsonStr = extractJson(raw);
			const parsed = JSON.parse(jsonStr) as CodeArtifact;
			if (!parsed.code || !parsed.filename) throw new Error('Missing code/filename');
			return parsed;
		} catch (err) {
			console.warn('[backend-api] LLM codegen failed, using mock:', err);
		}
	}

	const name = toIdentifier(resource);
	const file = toFilename(resource);

	return {
		filename: `api-${file}.ts`,
		language: 'typescript',
		code: `/** Auto-generated CRUD handlers for ${name} */

interface ${name} {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
}

const store: ${name}[] = [];

/** GET /api/${file} */
export function list() {
  return { data: store, total: store.length };
}

/** POST /api/${file} */
export function create(body: Partial<${name}>) {
  const item = { ...body, id: crypto.randomUUID(), createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() } as ${name};
  store.push(item);
  return item;
}
`,
	};
}

/**
 * Generate a SQL schema file — uses LLM when configured, otherwise mock.
 */
async function generateSchemaCode(payload: Record<string, unknown>): Promise<CodeArtifact> {
	const table = String(payload.table ?? payload.resource ?? 'items');

	if (isLlmConfigured('specialist')) {
		try {
			const raw = await chatCompletion(
				[
					{ role: 'system', content: SCHEMA_CODEGEN_PROMPT },
					{ role: 'user', content: table },
				],
				{ tier: 'specialist', temperature: 0.4, maxTokens: 1024 },
			);
			const jsonStr = extractJson(raw);
			const parsed = JSON.parse(jsonStr) as CodeArtifact;
			if (!parsed.code || !parsed.filename) throw new Error('Missing code/filename');
			return parsed;
		} catch (err) {
			console.warn('[backend-api] LLM schema codegen failed, using mock:', err);
		}
	}

	const file = toFilename(table);
	return {
		filename: `schema-${file}.sql`,
		language: 'sql',
		code: `-- Auto-generated schema for ${table}
CREATE TABLE IF NOT EXISTS ${file.replace(/-/g, '_')} (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  data JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_${file.replace(/-/g, '_')}_created_at ON ${file.replace(/-/g, '_')}(created_at DESC);
`,
	};
}

/**
 * Entry point for the Backend API wrapper.
 * Now generates actual code files instead of endpoint specs.
 */
async function main(): Promise<void> {
	const client = new WrapperClient(
		orchestratorUrl,
		{ name: 'Backend API', type: 'backend-api', drones: 2 },
		(env: Envelope<unknown>) => {
			const payload = (env.payload as Record<string, unknown>) ?? {};

			if (env.type === 'API_BRIEF') {
				emitStatus(client, 'THINKING');
				generateApiCode(payload).then((artifact) => {
					emitStatus(client, 'WORKING');
					client.send({
						type: 'EVENT',
						src: wrapperId,
						dst: env.src,
						ts: Date.now(),
						payload: {
							kind: 'CODE_ARTIFACT',
							messageId: payload.messageId,
							artifact: {
								filename: artifact.filename,
								language: artifact.language,
								code: artifact.code,
								type: 'api-route',
								wrapper: wrapperId,
							},
						},
					});
					// Legacy compat
					client.send({
						type: 'EVENT',
						src: wrapperId,
						dst: env.src,
						ts: Date.now(),
						payload: {
							kind: 'API_DRAFT',
							spec: {
								method: 'CRUD',
								path: `/api/${artifact.filename}`,
								description: `Generated ${artifact.filename}`,
								generatedAt: Date.now(),
							},
						},
					});
					emitStatus(client, 'IDLE');
				}).catch((err) => {
					console.error('[backend-api] error:', err);
					emitStatus(client, 'IDLE');
				});
				return;
			}

			if (env.type === 'SCHEMA_BRIEF') {
				emitStatus(client, 'WORKING');
				generateSchemaCode(payload).then((artifact) => {
					client.send({
						type: 'EVENT',
						src: wrapperId,
						dst: env.src,
						ts: Date.now(),
						payload: {
							kind: 'CODE_ARTIFACT',
							messageId: payload.messageId,
							artifact: {
								filename: artifact.filename,
								language: artifact.language,
								code: artifact.code,
								type: 'schema',
								wrapper: wrapperId,
							},
						},
					});
					// Legacy compat
					client.send({
						type: 'EVENT',
						src: wrapperId,
						dst: env.src,
						ts: Date.now(),
						payload: {
							kind: 'SCHEMA_DRAFT',
							schema: {
								table: artifact.filename,
								columns: ['auto-generated'],
								generatedAt: Date.now(),
							},
						},
					});
					emitStatus(client, 'IDLE');
				}).catch((err) => {
					console.error('[backend-api] schema error:', err);
					emitStatus(client, 'IDLE');
				});
				return;
			}

			if (env.type === 'PING') {
				client.send({
					type: 'EVENT',
					src: wrapperId,
					dst: env.src,
					ts: Date.now(),
					payload: { pong: true },
				});
				return;
			}

			console.log('[backend-api] event', env.type, payload);
		},
	);

	await client.connect();
	await client.register(wrapperId);
	emitStatus(client, 'IDLE');

	const statusInterval = setInterval(() => emitStatus(client, currentStatus), 10_000);

	process.on('SIGINT', () => {
		clearInterval(statusInterval);
		console.log('shutting down backend-api wrapper');
		client.send({ type: 'SHUTDOWN', src: wrapperId, ts: Date.now() });
		client.close();
		process.exit(0);
	});
}

main().catch((error: unknown) => {
	console.error('backend-api wrapper failed', error);
	process.exit(1);
});
