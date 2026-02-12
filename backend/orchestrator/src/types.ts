import type WebSocket from 'ws';

export type WrapperStatus = 'IDLE' | 'THINKING' | 'WORKING' | 'BLOCKED';

/**
 * Base envelope used for all orchestrator <-> wrapper messages.
 */
export interface Envelope<TPayload = unknown> {
	type: string;
	id?: string;
	src?: string;
	dst?: string;
	ts?: number;
	payload?: TPayload;
}

/**
 * Metadata describing a single wrapper instance.
 */
export interface WrapperMeta {
	name: string;
	type: string;
	drones?: number;
	[key: string]: unknown;
}

/**
 * A single wrapper entry tracked by the orchestrator registry.
 */
export interface RegistryRecord {
	id: string;
	type: string;
	status: WrapperStatus;
	lastSeen: number;
	socket: WebSocket;
	meta: WrapperMeta;
}
