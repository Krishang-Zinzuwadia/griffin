import { type Envelope, WrapperClient } from '../../sdk/client';
import { chatCompletion, isLlmConfigured, type ChatMessage as LlmMessage } from '../../sdk/llm-client';
import { createProject, type ProjectArtifact } from '../../sandbox/git-manager';

const orchestratorUrl = process.env.ORCHESTRATOR_URL ?? 'ws://localhost:9100';
const wrapperId = 'pm-1';

type StatusValue = 'IDLE' | 'THINKING' | 'WORKING' | 'BLOCKED';

let currentStatus: StatusValue = 'IDLE';

/**
 * Emit a STATUS_UPDATE event so the orchestrator (and UI) can display the
 * current state of the PM wrapper.
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


interface TaskPlan {
	wrapper: string;
	briefType: string;
	briefPayload: Record<string, unknown>;
}

/** Map wrapper IDs to human-friendly display names. */
const WRAPPER_NAMES: Record<string, string> = {
	'frontend-design-1': 'Frontend Design',
	'backend-api-1': 'Backend API',
	'security-1': 'Security',
	'health-1': 'Health Monitor',
};

/**
 * Keyword-based fallback router used when no LLM key is configured.
 */
function planTasksFallback(text: string): TaskPlan[] {
	const lower = text.toLowerCase();
	const tasks: TaskPlan[] = [];

	if (/frontend|ui|design|component|page|layout|dashboard|chart|button|form|style|css/.test(lower)) {
		tasks.push({
			wrapper: 'frontend-design-1',
			briefType: 'DESIGN_BRIEF',
			briefPayload: { title: text, source: 'pm' },
		});
	}

	if (/backend|api|endpoint|database|schema|server|data|crud|auth|route/.test(lower)) {
		tasks.push({
			wrapper: 'backend-api-1',
			briefType: 'API_BRIEF',
			briefPayload: { resource: text, source: 'pm' },
		});
	}

	if (/security|audit|vulnerability|policy|compliance|encryption|ssl|penetration/.test(lower)) {
		tasks.push({
			wrapper: 'security-1',
			briefType: 'AUDIT_REQUEST',
			briefPayload: { target: text, source: 'pm' },
		});
	}

	if (tasks.length === 0) {
		tasks.push(
			{ wrapper: 'frontend-design-1', briefType: 'DESIGN_BRIEF', briefPayload: { title: text, source: 'pm' } },
			{ wrapper: 'backend-api-1', briefType: 'API_BRIEF', briefPayload: { resource: text, source: 'pm' } },
		);
	}

	return tasks;
}

const PLANNER_SYSTEM_PROMPT = `You are Griffin's Project Manager AI. Given a user request, decide which specialist wrappers to dispatch work to.

Available wrappers:
- frontend-design-1 (brief type: DESIGN_BRIEF) — UI/UX, components, pages, styling
- backend-api-1    (brief type: API_BRIEF)     — API endpoints, database schemas, server logic
- security-1       (brief type: AUDIT_REQUEST)  — Security audits, policy checks, vulnerability scans

Respond ONLY with valid JSON — an array of objects like:
[{ "wrapper": "frontend-design-1", "briefType": "DESIGN_BRIEF", "description": "short task description" }]

Rules:
1. Always dispatch to at least one wrapper.
2. If the request is ambiguous, dispatch to both frontend-design-1 and backend-api-1.
3. Include security-1 if the request mentions security, auth, or compliance.
4. Keep descriptions concise (one sentence).`;

/**
 * Use the LLM to plan task delegation. Falls back to keyword router on error.
 */
async function planTasks(text: string): Promise<TaskPlan[]> {
	if (!isLlmConfigured('pm')) {
		return planTasksFallback(text);
	}

	try {
		const messages: LlmMessage[] = [
			{ role: 'system', content: PLANNER_SYSTEM_PROMPT },
			{ role: 'user', content: text },
		];

		const raw = await chatCompletion(messages, {
			tier: 'pm',
			temperature: 0.3,
			maxTokens: 512,
		});

		// Strip markdown fences if present
		const cleaned = raw.replace(/```(?:json)?\s*/g, '').replace(/```/g, '').trim();
		const parsed = JSON.parse(cleaned) as Array<{
			wrapper: string;
			briefType: string;
			description?: string;
		}>;

		if (!Array.isArray(parsed) || parsed.length === 0) {
			return planTasksFallback(text);
		}

		return parsed.map((p) => {
			const briefPayload: Record<string, unknown> = { source: 'pm' };
			if (p.briefType === 'DESIGN_BRIEF') briefPayload.title = p.description ?? text;
			if (p.briefType === 'API_BRIEF') briefPayload.resource = p.description ?? text;
			if (p.briefType === 'AUDIT_REQUEST') briefPayload.target = p.description ?? text;
			return { wrapper: p.wrapper, briefType: p.briefType, briefPayload };
		});
	} catch (err) {
		console.warn('[pm] LLM planner failed, falling back to keywords:', err);
		return planTasksFallback(text);
	}
}

/*
 * Convert a wrapper response payload into a human-readable chat summary.
 */
function summariseResponse(kind: string, payload: Record<string, unknown>, agentName: string): string | null {
	switch (kind) {
		case 'CODE_ARTIFACT': {
			const artifact = payload.artifact as Record<string, unknown> | undefined;
			const filename = String(artifact?.filename ?? 'unknown');
			const lang = String(artifact?.language ?? 'unknown');
			const codeLen = String(artifact?.code ?? '').length;
			return `Code generated: **${filename}** (${lang}, ${codeLen} chars). Check the Workstation tab for live preview.`;
		}
		case 'DESIGN_DRAFT': {
			const draft = payload.draft as Record<string, unknown> | undefined;
			const title = String(draft?.title ?? 'Untitled');
			const decisions = (draft?.decisions as string[]) ?? [];
			return `Design draft ready: "${title}". Decisions: ${decisions.join(', ') || 'pending'}.`;
		}
		case 'API_DRAFT': {
			const spec = payload.spec as Record<string, unknown> | undefined;
			return `API endpoint generated: ${spec?.method ?? 'GET'} ${spec?.path ?? '/api/unknown'} — ${spec?.description ?? ''}`;
		}
		case 'SCHEMA_DRAFT': {
			const schema = payload.schema as Record<string, unknown> | undefined;
			const cols = (schema?.columns as string[]) ?? [];
			return `Database schema created: table "${schema?.table ?? 'unknown'}" with columns [${cols.join(', ')}].`;
		}
		case 'AUDIT_REPORT': {
			const report = payload.report as Record<string, unknown> | undefined;
			return `Security audit complete: ${report?.passedChecks ?? 0}/${report?.totalChecks ?? 0} checks passed on "${report?.target ?? 'unknown'}".`;
		}
		case 'POLICY_RESULT': {
			const result = payload.result as Record<string, unknown> | undefined;
			const status = result?.compliant ? 'Compliant ✓' : 'Non-compliant ✗';
			return `Policy check: "${result?.policy ?? 'default'}" — ${status}. ${result?.notes ?? ''}`;
		}
		case 'STATUS_UPDATE':
			return null; // Ignore wrapper heartbeat status changes
		default:
			return `${agentName} completed task: ${kind || 'unknown'}`;
	}
}


/**
 * Pending project — collects artifacts from specialist wrappers for one user prompt.
 * When all expected artifacts arrive (or timeout), the PM finalises the project
 * by creating a git repo + pushing to GitHub.
 */
interface PendingProject {
	messageId: string;
	name: string;
	expectedCount: number;
	artifacts: ProjectArtifact[];
	timer: ReturnType<typeof setTimeout>;
}

/** Active projects keyed by messageId. */
const pendingProjects = new Map<string, PendingProject>();

/** Timeout (ms) before we finalise a project even if not all artifacts arrived. */
const PROJECT_TIMEOUT_MS = 45_000;

/**
 * Finalise a pending project — write files, git init, create GitHub repo, push.
 * Sends a PROJECT_READY event to the UI with the GitHub URL.
 */
async function finalizeProject(messageId: string, client: WrapperClient): Promise<void> {
	const project = pendingProjects.get(messageId);
	if (!project || project.artifacts.length === 0) {
		pendingProjects.delete(messageId);
		return;
	}
	pendingProjects.delete(messageId);

	try {
		console.log(`[pm] finalising project "${project.name}" (${project.artifacts.length} artifacts)`);
		const result = await createProject(project.name, project.artifacts);

		// Notify the frontend with the GitHub URL
		client.send({
			type: 'EVENT',
			src: wrapperId,
			ts: Date.now(),
			payload: {
				kind: 'PROJECT_READY',
				projectName: project.name,
				githubUrl: result.githubUrl,
				localPath: result.projectPath,
				repoName: result.repoName,
				artifactCount: project.artifacts.length,
			},
		});

		// Also send a chat message so the user sees it in the conversation
		const linkText = result.githubUrl
			? `Your project **${project.name}** is ready! [View on GitHub](${result.githubUrl})`
			: `Your project **${project.name}** has been committed locally (set GITHUB_TOKEN to auto-push).`;

		client.send({
			type: 'EVENT',
			src: wrapperId,
			ts: Date.now(),
			payload: { kind: 'CHAT_RESPONSE', messageId, text: linkText },
		});
	} catch (err) {
		console.error('[pm] project finalisation failed:', err);
		client.send({
			type: 'EVENT',
			src: wrapperId,
			ts: Date.now(),
			payload: {
				kind: 'CHAT_RESPONSE',
				messageId,
				text: `Project git setup failed: ${String(err)}. Code is still visible in the Workstation.`,
			},
		});
	}
}


//PM entry point
async function main(): Promise<void> {
	const client = new WrapperClient(
		orchestratorUrl,
		{ name: 'Project Manager', type: 'pm', drones: 1 },
		(env: Envelope<unknown>) => {
			const payload = (env.payload as Record<string, unknown>) ?? {};

			/* ---- Handle incoming chat messages from the UI ---- */
			const isChatEvent = env.type === 'EVENT' && payload.kind === 'CHAT_MESSAGE';
			const isChatDirect = env.type === 'CHAT_MESSAGE';
			if (isChatEvent || isChatDirect) {
				const text = String(payload.text ?? '');
				const messageId = String(payload.messageId ?? Date.now());

				emitStatus(client, 'THINKING');

				// Run async planning + response in background
				(async () => {
					try {
						// 1. Plan which wrappers to dispatch to
						const tasks = await planTasks(text);
						const names = tasks.map((t) => WRAPPER_NAMES[t.wrapper] ?? t.wrapper);

						// 2. Generate PM reply (LLM or fallback)
						let replyText: string;
						if (isLlmConfigured('pm')) {
							try {
								replyText = await chatCompletion(
									[
										{
											role: 'system',
											content: `You are Griffin's Project Manager. Briefly acknowledge the user's request and explain which teams you're dispatching: ${names.join(', ')}. Be concise (2-3 sentences). Professional but friendly.`,
										},
										{ role: 'user', content: text },
									],
									{ tier: 'pm', temperature: 0.5, maxTokens: 256 },
								);
							} catch {
								replyText = `Analysing your request. Dispatching to: ${names.join(', ')}. Stand by for results.`;
							}
						} else {
							replyText = `Analysing your request. Dispatching to: ${names.join(', ')}. Stand by for results.`;
						}

						// 3. Send reply to UI
						client.send({
							type: 'EVENT',
							src: wrapperId,
							ts: Date.now(),
							payload: { kind: 'CHAT_RESPONSE', messageId, text: replyText },
						});

						// 4. Dispatch task briefs to each specialist wrapper
						for (const task of tasks) {
							client.send({
								type: task.briefType,
								src: wrapperId,
								dst: task.wrapper,
								ts: Date.now(),
								payload: { ...task.briefPayload, messageId },
							});
						}

						// 5. Start tracking this prompt as a pending project
						pendingProjects.set(messageId, {
							messageId,
							name: text.slice(0, 80),
							expectedCount: tasks.length,
							artifacts: [],
							timer: setTimeout(() => finalizeProject(messageId, client), PROJECT_TIMEOUT_MS),
						});

						emitStatus(client, 'WORKING');
					} catch (err) {
						console.error('[pm] chat handling error:', err);
						client.send({
							type: 'EVENT',
							src: wrapperId,
							ts: Date.now(),
							payload: {
								kind: 'CHAT_RESPONSE',
								messageId,
								text: 'Sorry, I hit an error while processing your request. Please try again.',
							},
						});
						emitStatus(client, 'IDLE');
					}
				})();
				return;
			}

			/* ---- Handle responses from specialist wrappers ---- */
			if (env.type === 'EVENT' && env.src && env.src !== wrapperId) {
				const kind = String(payload.kind ?? '');
				const agentName = WRAPPER_NAMES[env.src] ?? env.src;

				// Forward CODE_ARTIFACT directly to the UI so workstation can render it
				if (kind === 'CODE_ARTIFACT') {
					const artifactData = payload.artifact as Record<string, unknown> | undefined;
					const artMessageId = String(payload.messageId ?? '');

					// Collect artifact into the pending project for git commit
					if (artMessageId && artifactData?.code) {
						const project = pendingProjects.get(artMessageId);
						if (project) {
							project.artifacts.push({
								filename: String(artifactData.filename ?? 'untitled'),
								code: String(artifactData.code),
								language: String(artifactData.language ?? 'unknown'),
								type: String(artifactData.type ?? 'component'),
							});
							console.log(`[pm] collected artifact ${project.artifacts.length}/${project.expectedCount} for project "${project.name}"`);

							// If all expected artifacts are in, finalise immediately
							if (project.artifacts.length >= project.expectedCount) {
								clearTimeout(project.timer);
								finalizeProject(artMessageId, client);
							}
						}
					}

					client.send({
						type: 'EVENT',
						src: wrapperId,
						ts: Date.now(),
						payload: {
							kind: 'CODE_ARTIFACT',
							artifact: payload.artifact,
							agent: agentName,
							agentId: env.src,
						},
					});
				}

				const summary = summariseResponse(kind, payload, agentName);

				if (summary) {
					client.send({
						type: 'EVENT',
						src: wrapperId,
						ts: Date.now(),
						payload: {
							kind: 'AGENT_MESSAGE',
							agent: agentName,
							agentId: env.src,
							text: summary,
							originalKind: kind,
						},
					});
					emitStatus(client, 'IDLE');
				}
				return;
			}

			/* ---- Standard handlers ---- */
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

			console.log('[pm] event', env.type, payload);
		},
	);

	await client.connect();
	await client.register(wrapperId);
	emitStatus(client, 'IDLE');

	/** Periodic status heartbeat so the UI stays up-to-date. */
	const statusInterval = setInterval(() => emitStatus(client, currentStatus), 10_000);

	process.on('SIGINT', () => {
		clearInterval(statusInterval);
		console.log('shutting down pm wrapper');
		client.send({ type: 'SHUTDOWN', src: wrapperId, ts: Date.now() });
		client.close();
		process.exit(0);
	});
}

main().catch((error: unknown) => {
	console.error('pm wrapper failed', error);
	process.exit(1);
});
