import { type Envelope, WrapperClient } from '../../sdk/client';
import { chatCompletion, isLlmConfigured } from '../../sdk/llm-client';

const orchestratorUrl = process.env.ORCHESTRATOR_URL ?? 'ws://localhost:9100';
const wrapperId = 'frontend-design-1';

type StatusValue = 'IDLE' | 'THINKING' | 'WORKING' | 'BLOCKED';

let currentStatus: StatusValue = 'IDLE';

/**
 * Emit a status update event so the orchestrator (and UI) can display the latest state.
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

/** System prompt that instructs the LLM to output a complete React component. */
const CODEGEN_SYSTEM_PROMPT = `You are a senior React engineer at a design agency.
Given a feature request, generate a COMPLETE, SELF-CONTAINED React component using JSX.

RULES:
1. Output ONLY valid JSON — no markdown fences, no backticks around the response, no explanation.
2. JSON schema:
   {
     "filename": "dashboard.jsx",
     "language": "jsx",
     "componentName": "Dashboard",
     "code": "...full component source..."
   }
3. The "code" field must be a single default-export React component function.
4. Use ONLY inline styles (style={{ ... }}) — do NOT use template literals or backticks in the code.
5. Do NOT import React — it is provided globally in the preview runtime.
6. Do NOT import external packages. Use built-in browser APIs only.
7. For charts/data-viz, use simple colored divs as bar charts or inline SVG.
8. Include realistic mock data arrays so the component renders something useful.
9. Keep the component under 120 lines. Focus on visual impact.
10. The component must be a default export: export default function ComponentName() { ... }
11. Use regular string concatenation or string literals with double quotes — NEVER use backtick template strings.
12. Make sure all JSON string values are properly escaped (especially newlines and quotes).`;

/** Fallback mock component when LLM is unavailable. */
function mockComponent(title: string): CodeArtifact {
	const name = title.replace(/[^a-zA-Z0-9]/g, '').slice(0, 30) || 'Component';
	return {
		filename: `${name.toLowerCase()}.jsx`,
		language: 'jsx',
		componentName: name,
		code: `export default function ${name}() {
  return (
    <div style={{ padding: '2rem', fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '1rem' }}>
        ${title}
      </h1>
      <p style={{ color: '#6b7280' }}>
        Component placeholder — connect an LLM API key to generate real code.
      </p>
    </div>
  );
}`,
	};
}

interface CodeArtifact {
	filename: string;
	language: string;
	componentName: string;
	code: string;
}

/**
 * Generate a React component — uses LLM when configured, otherwise returns mock.
 */
async function generateComponent(payload: Record<string, unknown>): Promise<CodeArtifact> {
	const title = String(payload.title ?? 'Untitled Feature');

	if (isLlmConfigured('specialist')) {
		try {
			const raw = await chatCompletion(
				[
					{ role: 'system', content: CODEGEN_SYSTEM_PROMPT },
					{ role: 'user', content: title },
				],
				{ tier: 'specialist', temperature: 0.6, maxTokens: 2048 },
			);

			const jsonStr = extractJson(raw);
			const parsed = JSON.parse(jsonStr) as CodeArtifact;
			console.log('[frontend-design] LLM codegen returned', parsed.filename, `(${String(parsed.code).length} chars)`);
			if (!parsed.code || !parsed.filename) throw new Error('Missing code/filename');
			return parsed;
		} catch (err) {
			console.warn('[frontend-design] LLM codegen failed, using mock:', err);
		}
	}

	return mockComponent(title);
}

/**
 * Extract a JSON object from LLM output that may contain markdown fences,
 * preamble text, or trailing explanation.
 *
 * Also handles common LLM quirks:
 * - Backtick-wrapped string values instead of double-quoted
 * - Unescaped newlines inside double-quoted JSON strings
 */
function extractJson(raw: string): string {
	// 1. Try stripping markdown code fences
	let text = raw;
	const fenceMatch = raw.match(/```(?:json)?\s*([\s\S]*?)```/);
	const fenceGroup = fenceMatch?.[1];
	if (fenceGroup) text = fenceGroup.trim();

	// 2. Find the first { and last } to isolate the JSON object
	const start = text.indexOf('{');
	const end = text.lastIndexOf('}');
	if (start === -1 || end <= start) return text.trim();

	let json = text.slice(start, end + 1);

	// 3. Fix backtick-wrapped values: `...` → "..."
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

	// 4. Fix unescaped newlines inside double-quoted strings.
	//    Walk char-by-char: when inside a string, replace literal \n with \\n.
	let result = '';
	let inString = false;
	let escaped = false;
	for (let i = 0; i < json.length; i++) {
		const ch = json[i];
		if (escaped) {
			result += ch;
			escaped = false;
			continue;
		}
		if (ch === '\\' && inString) {
			escaped = true;
			result += ch;
			continue;
		}
		if (ch === '"') {
			inString = !inString;
			result += ch;
			continue;
		}
		if (inString && ch === '\n') {
			result += '\\n';
			continue;
		}
		if (inString && ch === '\r') {
			result += '\\r';
			continue;
		}
		if (inString && ch === '\t') {
			result += '\\t';
			continue;
		}
		result += ch;
	}

	return result;
}

/**
 * Entry point for the Frontend Design wrapper.
 * Now generates actual React component code instead of text plans.
 */
async function main(): Promise<void> {
	const client = new WrapperClient(
		orchestratorUrl,
		{ name: 'Frontend Design', type: 'frontend-design', drones: 2 },
		(env: Envelope<unknown>) => {
			if (env.type === 'DESIGN_BRIEF') {
				emitStatus(client, 'THINKING');
				const payload = (env.payload as Record<string, unknown>) ?? {};

				generateComponent(payload).then((artifact) => {
					emitStatus(client, 'WORKING');

					// Send the generated code as a CODE_ARTIFACT event
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
								componentName: artifact.componentName,
								code: artifact.code,
								type: 'component',
								wrapper: wrapperId,
							},
						},
					});

					// Also send a legacy DESIGN_DRAFT for backward compat
					client.send({
						type: 'EVENT',
						src: wrapperId,
						dst: env.src,
						ts: Date.now(),
						payload: {
							kind: 'DESIGN_DRAFT',
							draft: {
								title: artifact.componentName,
								decisions: ['code-generated'],
								components: [artifact.filename],
								notes: `Generated ${artifact.filename} (${artifact.code.length} chars)`,
							},
						},
					});

					emitStatus(client, 'IDLE');
				}).catch((err) => {
					console.error('[frontend-design] error:', err);
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

			console.log('[frontend-design] event', env.type, env.payload ?? null);
		},
	);

	await client.connect();
	await client.register(wrapperId);
	emitStatus(client, 'IDLE');

	const statusInterval = setInterval(() => emitStatus(client, currentStatus), 10_000);

	process.on('SIGINT', () => {
		clearInterval(statusInterval);
		console.log('shutting down frontend-design wrapper');
		client.send({ type: 'SHUTDOWN', src: wrapperId, ts: Date.now() });
		client.close();
		process.exit(0);
	});
}

main().catch((error: unknown) => {
	console.error('frontend-design wrapper failed', error);
	process.exit(1);
});
