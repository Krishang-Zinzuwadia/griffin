/**
 * Quick smoke test — proves Groq LLM integration works end-to-end.
 * Run: bun run backend/sdk/test-llm.ts
 */
import { chatCompletion, isLlmConfigured } from './llm-client';

async function main() {
  console.log('--- Griffin LLM Smoke Test ---\n');

  /* ---- 1. Check env vars ---- */
  console.log('LLM_BASE_URL  :', process.env.LLM_BASE_URL);
  console.log('LLM_PM_MODEL  :', process.env.LLM_PM_MODEL);
  console.log('LLM_SPEC_MODEL:', process.env.LLM_SPECIALIST_MODEL);
  console.log('PM key set?    :', isLlmConfigured('pm'));
  console.log('Spec key set?  :', isLlmConfigured('specialist'));
  console.log();

  /* ---- 2. PM tier call (llama3-70b) ---- */
  console.log('[PM] Sending test prompt to Groq (llama3-70b-8192) ...');
  try {
    const pmReply = await chatCompletion(
      [
        { role: 'system', content: 'You are Griffin, an autonomous AI software studio. Respond in one concise sentence.' },
        { role: 'user', content: 'Describe what a Project Manager wrapper does in the Griffin system.' },
      ],
      { tier: 'pm', temperature: 0.4, maxTokens: 150 },
    );
    console.log('[PM] ✅ Response:', pmReply);
  } catch (err) {
    console.error('[PM] ❌ Error:', err);
  }

  console.log();

  /* ---- 3. Specialist tier call (llama3-8b) ---- */
  console.log('[Specialist] Sending test prompt to Groq (llama3-8b-8192) ...');
  try {
    const specReply = await chatCompletion(
      [
        { role: 'system', content: 'You are a frontend design specialist AI. Respond in one concise sentence.' },
        { role: 'user', content: 'What would you generate for a dashboard layout request?' },
      ],
      { tier: 'specialist', temperature: 0.4, maxTokens: 150 },
    );
    console.log('[Specialist] ✅ Response:', specReply);
  } catch (err) {
    console.error('[Specialist] ❌ Error:', err);
  }

  console.log('\n--- Done ---');
}

main();
