import WebSocket from 'ws';

export interface Envelope<TPayload = unknown> {
  type: string;
  id?: string;
  src?: string;
  dst?: string;
  ts?: number;
  payload?: TPayload;
}

export interface WrapperMeta {
  name: string;
  type: string;
  drones?: number;
  [key: string]: unknown;
}

export type EventHandler = (env: Envelope<unknown>) => void;

export class WrapperClient {
  private ws?: WebSocket;
  private readonly url: string;
  private id?: string;
  private readonly meta: WrapperMeta;
  private hbTimer?: ReturnType<typeof setInterval>;
  private readonly onEvent?: EventHandler;

  constructor(url: string, meta: WrapperMeta, onEvent?: EventHandler) {
    this.url = url;
    this.meta = meta;
    this.onEvent = onEvent;
  }

  /**
   * Establish a WebSocket connection to the orchestrator.
   */
  connect(): Promise<void> {
    return new Promise<void>((resolve) => {
      this.ws = new WebSocket(this.url);
      this.ws.on('open', () => {
        resolve();
      });

      this.ws.on('message', (data: WebSocket.RawData) => this.onMessage(String(data)));
      this.ws.on('error', (error: Error) => console.error('ws error', error));
      this.ws.on('close', () => {
        console.log('ws closed');
        if (this.hbTimer) clearInterval(this.hbTimer);
      });
    });
  }

  /**
   * Register this wrapper instance with the orchestrator and start heartbeats.
   */
  async register(id?: string): Promise<void> {
    this.id = id;
    this.send({ type: 'REGISTER', id, payload: this.meta, ts: Date.now() });
    // start heartbeat
    this.hbTimer = setInterval(() => this.heartbeat(), 2000);
  }

  private heartbeat(): void {
    if (!this.id) return;
    this.send({ type: 'HEARTBEAT', src: this.id, ts: Date.now() });
  }

  /**
   * Send an envelope to the orchestrator.
   */
  send(env: Envelope<unknown>): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify(env));
  }

  private onMessage(raw: string): void {
    let env: Envelope<unknown>;
    try {
      env = JSON.parse(raw) as Envelope<unknown>;
    } catch (error) {
      console.warn('invalid envelope', raw);
      return;
    }

    switch (env.type) {
      case 'REGISTER_ACK':
        if (typeof env.payload === 'object' && env.payload && 'id' in env.payload) {
          const payload = env.payload as { id: string };
          this.id = payload.id;
        }
        console.log('registered as', this.id);
        break;
      case 'HEARTBEAT_ACK':
        break;
      default:
        this.handleEvent(env);
    }
  }

  /**
   * Delegate incoming events to the registered handler, if present.
   */
  private handleEvent(env: Envelope<unknown>): void {
    if (this.onEvent) {
      this.onEvent(env);
      return;
    }

    console.log('event recv', env.type, env.payload);
  }

  /**
   * Close the WebSocket connection and stop heartbeats.
   */
  close(): void {
    if (this.ws) this.ws.close();
    if (this.hbTimer) clearInterval(this.hbTimer);
  }
}
