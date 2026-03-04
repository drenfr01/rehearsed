import { TestBed } from '@angular/core/testing';
import { GeminiLiveService } from './gemini-live.service';

describe('GeminiLiveService', () => {
  let service: GeminiLiveService;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({});
    service = TestBed.inject(GeminiLiveService);
  });

  afterEach(() => {
    service.disconnect();
    localStorage.clear();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('initial state', () => {
    it('should start disconnected', () => {
      expect(service.connectionState()).toBe('disconnected');
    });

    it('should start with empty transcript', () => {
      expect(service.transcript()).toEqual([]);
    });

    it('should start not recording', () => {
      expect(service.isRecording()).toBeFalse();
    });

    it('should start with no error', () => {
      expect(service.error()).toBe('');
    });
  });

  describe('connect', () => {
    it('should set error when no token in localStorage', async () => {
      localStorage.removeItem('token');
      await service.connect(1, 'agent-1').catch(() => {});
      expect(service.error()).toBe('Not authenticated');
      expect(service.connectionState()).toBe('error');
    });
  });

  describe('sendText', () => {
    it('should not throw when ws is null', () => {
      expect(() => service.sendText('hello')).not.toThrow();
    });
  });

  describe('stopRecording', () => {
    it('should set isRecording to false', () => {
      service.stopRecording();
      expect(service.isRecording()).toBeFalse();
    });

    it('should be safe to call multiple times', () => {
      service.stopRecording();
      service.stopRecording();
      expect(service.isRecording()).toBeFalse();
    });
  });

  describe('disconnect', () => {
    it('should set state to disconnected', () => {
      service.disconnect();
      expect(service.connectionState()).toBe('disconnected');
    });

    it('should set isRecording to false', () => {
      service.disconnect();
      expect(service.isRecording()).toBeFalse();
    });

    it('should be safe to call when already disconnected', () => {
      service.disconnect();
      service.disconnect();
      expect(service.connectionState()).toBe('disconnected');
    });
  });
});
