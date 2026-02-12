/**
 * Shared LLM client for all Griffin wrappers.
 *
 * Uses the OpenAI-compatible chat completions endpoint so it works with
 * OpenAI, Azure OpenAI, Anthropic (via proxy), Ollama, LM Studio, etc.
 *
 * Environment variables (read from process.env):
 *   LLM_API_KEY             – primary API key (used by PM)
 *   LLM_SPECIALIST_API_KEY  – optional separate key for specialist wrappers
 *   LLM_PM_MODEL            – model name for PM (default: gpt-4o)
 *   LLM_SPECIALIST_MODEL    – model name for specialists (default: gpt-4o-mini)
 *   LLM_BASE_URL            – base URL override (default: https://api.openai.com/v1)
 */

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface ChatMessage {
	role: 'system' | 'user' | 'assistant';
	content: string;
}

export interface LlmConfig {
	/** Which API key to use – 'pm' reads LLM_API_KEY, 'specialist' prefers LLM_SPECIALIST_API_KEY then falls back. */
	tier: 'pm' | 'specialist';
	/** Override model for this call. Falls back to env-based default. */
	model?: string;
	/** Sampling temperature (0-2). */
	temperature?: number;
	/** Max tokens to generate. */
	maxTokens?: number;
}

interface CompletionChoice {
	message: { role: string; content: string };
}

interface CompletionResponse {
	choices: CompletionChoice[];
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/** Resolve the API key for a given tier. */
function resolveApiKey(tier: 'pm' | 'specialist'): string {
	if (tier === 'specialist') {
		const specialist = process.env.LLM_SPECIALIST_API_KEY;
		if (specialist && specialist.length > 0) return specialist;
	}
	return process.env.LLM_API_KEY ?? '';
}

/** Resolve the model name for a given tier. */
function resolveModel(tier: 'pm' | 'specialist', override?: string): string {
	if (override) return override;
	if (tier === 'pm') return process.env.LLM_PM_MODEL ?? 'gpt-4o';
	return process.env.LLM_SPECIALIST_MODEL ?? 'gpt-4o-mini';
}

/** Get the base URL (no trailing slash). */
function resolveBaseUrl(): string {
	const base = process.env.LLM_BASE_URL ?? 'https://api.openai.com/v1';
	return base.replace(/\/+$/, '');
}

/* ------------------------------------------------------------------ */
/*  Public API                                                         */
/* ------------------------------------------------------------------ */

/**
 * Send a chat completion request and return the assistant's reply text.
 * Throws if the key is missing or the API returns an error.
 */
export async function chatCompletion(
	messages: ChatMessage[],
	config: LlmConfig,
): Promise<string> {
	const apiKey = resolveApiKey(config.tier);
	const model = resolveModel(config.tier, config.model);
	const baseUrl = resolveBaseUrl();

	if (!apiKey) {
		console.warn(`[llm] No API key configured for tier "${config.tier}" — returning mock response.`);
		return `[mock] LLM response placeholder (no API key set for ${config.tier})`;
	}

	const body = {
		model,
		messages,
		temperature: config.temperature ?? 0.7,
		max_tokens: config.maxTokens ?? 1024,
	};

	const res = await fetch(`${baseUrl}/chat/completions`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${apiKey}`,
		},
		body: JSON.stringify(body),
	});

	if (!res.ok) {
		const text = await res.text().catch(() => 'unknown');
		throw new Error(`[llm] API error ${res.status}: ${text}`);
	}

	const data = (await res.json()) as CompletionResponse;
	return data.choices?.[0]?.message?.content ?? '';
}

/**
 * Convenience: check whether an API key is actually configured.
 * Useful for wrappers to decide between LLM path and mock path.
 */
export function isLlmConfigured(tier: 'pm' | 'specialist' = 'pm'): boolean {
	return resolveApiKey(tier).length > 0;
}
