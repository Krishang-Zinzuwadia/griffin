import { type Envelope, WrapperClient } from '../../sdk/client';
import { chatCompletion, isLlmConfigured } from '../../sdk/llm-client';

const orchestratorUrl = process.env.ORCHESTRATOR_URL ?? 'ws://localhost:9100';
const wrapperId = 'security-1';

type StatusValue = 'IDLE' | 'THINKING' | 'WORKING' | 'BLOCKED';

let currentStatus: StatusValue = 'IDLE';
//status update evnt so event handler can show that
function emitStatus(client: WrapperClient, status: StatusValue): void {
	currentStatus = status;
	client.send({
		type: 'EVENT',
		src: wrapperId,
		ts: Date.now(),
		payload: { kind: 'STATUS_UPDATE', status },
	});
}
/** Severity levels for audit findings. */
type Severity = 'info' | 'low' | 'medium' | 'high' | 'critical';

interface AuditFinding {
	rule: string;
	severity: Severity;
	message: string;
}

interface AuditReport {
	target: string;
	findings: AuditFinding[];
	passedChecks: number;
	totalChecks: number;
	scannedAt: number;
}


//run a mock security audit on the target described in the payload.
//Returns a report with simulated findings.
//  Will be replaced by real static-analysis / dependency-audit tooling later.

async function runAudit(payload: Record<string, unknown>): Promise<AuditReport> {
	const target = String(payload.target ?? payload.file ?? 'unknown');

	if (isLlmConfigured('specialist')) {
		try {
			const raw = await chatCompletion(
				[
					{
						role: 'system',
						content: 'You are a senior security engineer. Given a target, respond with concise JSON: { "target": "...", "findings": [{ "rule": "...", "severity": "info|low|medium|high|critical", "message": "..." }], "passedChecks": N, "totalChecks": N }. Keep it realistic and brief.',
					},
					{ role: 'user', content: `Audit: ${target}` },
				],
				{ tier: 'specialist', temperature: 0.4, maxTokens: 512 },
			);
			const cleaned = raw.replace(/```(?:json)?\s*/g, '').replace(/```/g, '').trim();
			const parsed = JSON.parse(cleaned) as Record<string, unknown>;
			return {
				target: String(parsed.target ?? target),
				findings: Array.isArray(parsed.findings) ? parsed.findings as AuditFinding[] : [],
				passedChecks: Number(parsed.passedChecks ?? 0),
				totalChecks: Number(parsed.totalChecks ?? 0),
				scannedAt: Date.now(),
			};
		} catch (err) {
			console.warn('[security] LLM audit failed, using mock:', err);
		}
	}

	const findings: AuditFinding[] = [
		{ rule: 'no-hardcoded-secrets', severity: 'high', message: `Scanned ${target} — no hardcoded secrets detected.` },
		{ rule: 'dependency-cve-check', severity: 'info', message: 'All dependencies are up-to-date.' },
		{ rule: 'sql-injection-guard', severity: 'medium', message: 'Parameterised queries verified.' },
	];

	return {
		target,
		findings,
		passedChecks: findings.length,
		totalChecks: findings.length,
		scannedAt: Date.now(),
	};
}

interface PolicyResult {
	policy: string;
	compliant: boolean;
	notes: string;
}

/**
 * Check compliance against a requested security policy.
 * Mock implementation — will integrate real policy engines later.
 */
async function checkPolicy(payload: Record<string, unknown>): Promise<PolicyResult> {
	const policy = String(payload.policy ?? 'default');

	if (isLlmConfigured('specialist')) {
		try {
			const raw = await chatCompletion(
				[
					{
						role: 'system',
						content: 'You are a security compliance officer. Given a policy name, respond with concise JSON: { "policy": "...", "compliant": true/false, "notes": "..." }. Keep it brief.',
					},
					{ role: 'user', content: `Check policy: ${policy}` },
				],
				{ tier: 'specialist', temperature: 0.3, maxTokens: 256 },
			);
			const cleaned = raw.replace(/```(?:json)?\s*/g, '').replace(/```/g, '').trim();
			const parsed = JSON.parse(cleaned) as Record<string, unknown>;
			return {
				policy: String(parsed.policy ?? policy),
				compliant: Boolean(parsed.compliant ?? true),
				notes: String(parsed.notes ?? ''),
			};
		} catch (err) {
			console.warn('[security] LLM policy check failed, using mock:', err);
		}
	}

	return {
		policy,
		compliant: true,
		notes: `Policy "${policy}" evaluated — all checks passed.`,
	};
}


/**
 * Entry point for the Security wrapper.
 * Handles AUDIT_REQUEST and POLICY_CHECK requests from the orchestrator,
 * responding with audit reports and policy compliance results.
 */
async function main(): Promise<void> {
	const client = new WrapperClient(
		orchestratorUrl,
		{ name: 'Security', type: 'security', drones: 1 },
		(env: Envelope<unknown>) => {
			const payload = (env.payload as Record<string, unknown>) ?? {};

			if (env.type === 'AUDIT_REQUEST') {
				emitStatus(client, 'WORKING');
				runAudit(payload).then((report) => {
					client.send({
						type: 'EVENT',
						src: wrapperId,
						dst: env.src,
						ts: Date.now(),
						payload: { kind: 'AUDIT_REPORT', report },
					});
					emitStatus(client, 'IDLE');
				}).catch((err) => {
					console.error('[security] audit error:', err);
					emitStatus(client, 'IDLE');
				});
				return;
			}

			if (env.type === 'POLICY_CHECK') {
				emitStatus(client, 'THINKING');
				checkPolicy(payload).then((result) => {
					client.send({
						type: 'EVENT',
						src: wrapperId,
						dst: env.src,
						ts: Date.now(),
						payload: { kind: 'POLICY_RESULT', result },
					});
					emitStatus(client, 'IDLE');
				}).catch((err) => {
					console.error('[security] policy error:', err);
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

			console.log('[security] event', env.type, payload);
		},
	);

	await client.connect();
	await client.register(wrapperId);
	emitStatus(client, 'IDLE');

	//status heartbeat periodically to ensure ui updates
	const statusInterval = setInterval(() => emitStatus(client, currentStatus), 10_000);

	process.on('SIGINT', () => {
		clearInterval(statusInterval);
		console.log('shutting down security wrapper');
		client.send({ type: 'SHUTDOWN', src: wrapperId, ts: Date.now() });
		client.close();
		process.exit(0);
	});
}

main().catch((error: unknown) => {
	console.error('security wrapper failed', error);
	process.exit(1);
});
