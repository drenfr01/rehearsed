import { Injectable, signal, effect } from '@angular/core';
import { Message } from '../models/chat-graph.model';

@Injectable({ providedIn: 'root' })
export class MessageStore {
  private readonly STORAGE_KEY = 'chat_graph_messages';

  private messages = signal<Message[]>(this.loadFromStorage());

  readonly all = this.messages.asReadonly();

  constructor() {
    effect(() => {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.messages()));
    });
  }

  appendUser(message: Message): void {
    this.messages.set([...this.messages(), message]);
  }

  appendAssistant(message: Message): void {
    this.messages.set([...this.messages(), message]);
  }

  appendAll(messages: Message[]): void {
    this.messages.set([...this.messages(), ...messages]);
  }

  updateContent(turnId: string, content: string): void {
    const msgs = this.messages();
    const idx = msgs.findIndex(m => m.turnId === turnId);
    if (idx === -1) return;
    const updated = [...msgs];
    updated[idx] = { ...updated[idx], content };
    this.messages.set(updated);
  }

  updateLastUserContent(content: string): void {
    const msgs = this.messages();
    const lastUserIndex = msgs.map(m => m.role).lastIndexOf('user');
    if (lastUserIndex === -1) return;
    const updated = [...msgs];
    updated[lastUserIndex] = { ...updated[lastUserIndex], content };
    this.messages.set(updated);
  }

  patchAudio(audioId: string, audioBase64: string): void {
    const updated = this.messages().map(m =>
      m.audio_id === audioId ? { ...m, audio_base64: audioBase64 } : m,
    );
    this.messages.set(updated);
  }

  reset(): void {
    this.messages.set([]);
    localStorage.removeItem(this.STORAGE_KEY);
  }

  private loadFromStorage(): Message[] {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  }
}
