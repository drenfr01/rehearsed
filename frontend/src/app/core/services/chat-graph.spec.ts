import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { ChatGraphService } from './chat-graph.service';
import { environment } from '../../../environments/environment';
import { ChatRequest, ChatResponse } from '../models/chat-graph.model';

describe('ChatGraphService', () => {
  let service: ChatGraphService;
  let httpTesting: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(ChatGraphService);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
    localStorage.clear();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should start with empty graph messages', () => {
    expect(service.loadedGraphMessages()).toEqual([]);
  });

  it('should start with empty inline feedback', () => {
    expect(service.loadedInlineFeedback()).toEqual([]);
  });

  it('should start with empty summary feedback', () => {
    expect(service.loadedSummaryFeedback()).toBe('');
  });

  it('should start with null feedback status', () => {
    expect(service.loadedFeedbackStatus()).toBeNull();
  });

  describe('resetGraphMessages', () => {
    it('should clear messages and inline feedback', () => {
      service.resetGraphMessages();
      expect(service.loadedGraphMessages()).toEqual([]);
      expect(service.loadedInlineFeedback()).toEqual([]);
    });

    it('should remove localStorage entries', () => {
      localStorage.setItem('chat_graph_messages', JSON.stringify([{ role: 'user', content: 'hi' }]));
      localStorage.setItem('chat_inline_feedback', JSON.stringify(['good']));
      service.resetGraphMessages();
      expect(localStorage.getItem('chat_graph_messages')).toBeNull();
      expect(localStorage.getItem('chat_inline_feedback')).toBeNull();
    });
  });

  describe('getTtsStatus', () => {
    it('should return undefined for unknown audio id', () => {
      expect(service.getTtsStatus('unknown')).toBeUndefined();
    });

    it('should return undefined when audioId is undefined', () => {
      expect(service.getTtsStatus(undefined)).toBeUndefined();
    });
  });

  describe('sendGraphRequest', () => {
    const mockResponse: ChatResponse = {
      messages: [],
      interrupt_task: '',
      interrupt_value: '',
      interrupt_value_type: 'text',
      student_responses: [],
      inline_feedback: ['Good job'],
      feedback_request_id: '',
      summary_feedback: '',
      summary: '',
      answering_student: 0,
      appropriate_response: true,
      appropriate_explanation: '',
      learning_goals_achieved: false,
      transcribed_text: '',
      interrupt: [],
    };

    it('should send a POST request to the chat endpoint', () => {
      const chatRequest: ChatRequest = {
        messages: [{ role: 'user', content: 'Hello' }],
        is_resumption: false,
        resumption_text: '',
        resumption_approved: false,
      };

      service.sendGraphRequest(chatRequest, true).subscribe();

      const req = httpTesting.expectOne(`${environment.baseUrl}/api/v1/chatbot/chat`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(chatRequest);
      req.flush(mockResponse);
    });

    it('should add user messages for initial request', () => {
      const chatRequest: ChatRequest = {
        messages: [{ role: 'user', content: 'Hello' }],
        is_resumption: false,
        resumption_text: '',
        resumption_approved: false,
      };

      service.sendGraphRequest(chatRequest, true).subscribe();

      const messages = service.loadedGraphMessages();
      expect(messages.length).toBe(1);
      expect(messages[0].content).toBe('Hello');

      httpTesting.expectOne(`${environment.baseUrl}/api/v1/chatbot/chat`).flush(mockResponse);
    });

    it('should add resumption message for non-initial request', () => {
      const chatRequest: ChatRequest = {
        messages: [],
        is_resumption: true,
        resumption_text: 'Continue',
        resumption_approved: true,
      };

      service.sendGraphRequest(chatRequest, false).subscribe();

      const messages = service.loadedGraphMessages();
      expect(messages.length).toBe(1);
      expect(messages[0].role).toBe('user');
      expect(messages[0].content).toBe('Continue');

      httpTesting.expectOne(`${environment.baseUrl}/api/v1/chatbot/chat`).flush(mockResponse);
    });

    it('should set inline feedback from response', () => {
      const chatRequest: ChatRequest = {
        messages: [{ role: 'user', content: 'Hello' }],
        is_resumption: false,
        resumption_text: '',
        resumption_approved: false,
      };

      service.sendGraphRequest(chatRequest, true).subscribe();

      const req = httpTesting.expectOne(`${environment.baseUrl}/api/v1/chatbot/chat`);
      req.flush(mockResponse);

      expect(service.loadedInlineFeedback()).toEqual(['Good job']);
      expect(service.loadedFeedbackStatus()).toBe('ready');
    });

    it('should handle interrupt with student responses', () => {
      const responseWithInterrupt: ChatResponse = {
        ...mockResponse,
        interrupt_task: 'student_response',
        interrupt_value: 'Student answer',
        interrupt_value_type: 'text',
        student_responses: [{
          student_response: 'Answer',
          student_details: { id: 'a1', name: 'Alice', objective: '', instructions: '', constraints: '' },
          student_personality: { id: '1', name: 'Curious', personality_description: '' },
          audio_base64: '',
        }],
      };

      const chatRequest: ChatRequest = {
        messages: [{ role: 'user', content: 'Hello' }],
        is_resumption: false,
        resumption_text: '',
        resumption_approved: false,
      };

      service.sendGraphRequest(chatRequest, true).subscribe();
      httpTesting.expectOne(`${environment.baseUrl}/api/v1/chatbot/chat`).flush(responseWithInterrupt);

      const messages = service.loadedGraphMessages();
      const assistantMsg = messages.find(m => m.role === 'assistant');
      expect(assistantMsg).toBeTruthy();
      expect(assistantMsg!.content).toBe('Student answer');
      expect(assistantMsg!.student_name).toBe('Alice');
    });
  });

  describe('localStorage persistence', () => {
    it('should load graph messages from localStorage on construction', () => {
      const storedMessages = [{ role: 'user' as const, content: 'stored' }];
      localStorage.setItem('chat_graph_messages', JSON.stringify(storedMessages));

      TestBed.resetTestingModule();
      TestBed.configureTestingModule({
        providers: [provideHttpClient(), provideHttpClientTesting()],
      });
      const freshService = TestBed.inject(ChatGraphService);

      expect(freshService.loadedGraphMessages()).toEqual(storedMessages);
    });

    it('should handle corrupted localStorage gracefully', () => {
      localStorage.setItem('chat_graph_messages', 'not-json');

      TestBed.resetTestingModule();
      TestBed.configureTestingModule({
        providers: [provideHttpClient(), provideHttpClientTesting()],
      });
      const freshService = TestBed.inject(ChatGraphService);

      expect(freshService.loadedGraphMessages()).toEqual([]);
    });
  });
});
