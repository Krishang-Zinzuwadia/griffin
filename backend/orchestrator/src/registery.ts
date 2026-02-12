import type WebSocket from 'ws';
import type { RegistryRecord, WrapperMeta, WrapperStatus } from './types';

const registry = new Map<string, RegistryRecord>();

/**
 * Upsert a wrapper entry in the registry.
 */
export function upsertWrapper(id: string, meta: WrapperMeta, socket: WebSocket): RegistryRecord {
  const existing = registry.get(id);
  const record: RegistryRecord = {
    id,
    type: meta.type,
    status: existing?.status ?? 'IDLE',
    lastSeen: Date.now(),
    socket,
    meta,
  };

  registry.set(id, record);
  return record;
}

/**
 * Mark a heartbeat for a wrapper, updating its status and lastSeen.
 */
export function markHeartbeat(id: string, status: WrapperStatus = 'WORKING'): void {
  const record = registry.get(id);
  if (!record) return;

  record.lastSeen = Date.now();
  record.status = status;
}

/**
 * Remove a wrapper from the registry and close its socket.
 */
export function removeWrapper(id: string): void {
  const record = registry.get(id);
  if (!record) return;
  try {
    record.socket.close();
  } catch {
    // ignore
  }
  registry.delete(id);
}

/**
 * Get a snapshot array of all registered wrappers.
 */
export function listWrappers(): RegistryRecord[] {
  return Array.from(registry.values());
}

/**
 * Find a single wrapper by id.
 */
export function findWrapper(id: string): RegistryRecord | undefined {
  return registry.get(id);
}

/**
 * Remove wrappers that have not sent a heartbeat within the timeout.
 */
export function pruneStaleWrappers(timeoutMs: number): string[] {
  const now = Date.now();
  const removed: string[] = [];

  for (const [id, record] of registry.entries()) {
    if (now - record.lastSeen > timeoutMs) {
      removeWrapper(id);
      removed.push(id);
    }
  }

  return removed;
}


