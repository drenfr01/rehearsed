import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { ChatOrchestrator } from './chat-orchestrator.service';
import { MessageStore } from './message-store.service';
import { InlineFeedbackService } from './inline-feedback.service';
import { TtsAudioService } from './tts-audio.service';
import { environment } from '../../../environments/environment';
import { ChatRequest, ChatResponse } from '../models/chat-graph.model';

describe('ChatOrchestrator', () => {
  let orchestrator: ChatOrchestrator;
  let messageStore: MessageStore;
  let feedbackService: InlineFeedbackService;
  let httpTesting: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    orchestrator = TestBed.inject(ChatOrchestrator);
    messageStore = TestBed.inject(MessageStore);
    feedbackService = TestBed.inject(InlineFeedbackService);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
    localStorage.clear();
  });

  it('should be created', () => {
    expect(orchestrator).toBeTruthy();
  });

  it('should start with empty messages', () => {
    expect(messageStore.all()).toEqual([]);
  });

  it('should start with empty summary feedback', () => {
    expect(orchestrator.summaryFeedback()).toBe('');
  });

  describe('resetSession', () => {
    it('should clear messages and feedback', () => {
      orchestrator.resetSession();
      expect(messageStore.all()).toEqual([]);
      expect(feedbackService.history()).toEqual([]);
    });
  });

  describe('sendChatRequest', () => {
    const mockResponse: ChatResponse = {
      messages: [],
      interrupt_task: '',
      interrupt_value: '',
      interrupt_value_type: 'text',
      student_responses: [],
      inline_feedback: [],
      feedback_request_id: 'test-feedback-id',
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

      orchestrator.sendChatRequest(chatRequest, true).subscribe();

      const req = httpTesting.expectOne(`${environment.baseUrl}/api/v1/chatbot/chat`);
      expect(req.request.method).toBe('POST');
      req.flush(mockResponse);
    });

    it('should add user messages for initial request', () => {
      const chatRequest: ChatRequest = {
        messages: [{ role: 'user', content: 'Hello' }],
        is_resumption: false,
        resumption_text: '',
        resumption_approved: false,
      };

      orchestrator.sendChatRequest(chatRequest, true).subscribe();

      const messages = messageStore.all();
      expect(messages.length).toBe(1);
      expect(messages[0].content).toBe('Hello');
      expect(messages[0].turnId).toBeTruthy();

      httpTesting.expectOne(`${environment.baseUrl}/api/v1/chatbot/chat`).flush(mockResponse);
    });

    it('should add resumption message with turnId for non-initial request', () => {
      const chatRequest: ChatRequest = {
        messages: [],
        is_resumption: true,
        resumption_text: 'Continue',
        resumption_approved: true,
      };

      orchestrator.sendChatRequest(chatRequest, false).subscribe();

      const messages = messageStore.all();
      expect(messages.length).toBe(1);
      expect(messages[0].role).toBe('user');
      expect(messages[0].content).toBe('Continue');
      expect(messages[0].turnId).toBeTruthy();

      httpTesting.expectOne(`${environment.baseUrl}/api/v1/chatbot/chat`).flush(mockResponse);
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

      orchestrator.sendChatRequest(chatRequest, true).subscribe();
      httpTesting.expectOne(`${environment.baseUrl}/api/v1/chatbot/chat`).flush(responseWithInterrupt);

      const messages = messageStore.all();
      const assistantMsg = messages.find(m => m.role === 'assistant');
      expect(assistantMsg).toBeTruthy();
      expect(assistantMsg!.content).toBe('Student answer');
      expect(assistantMsg!.student_name).toBe('Alice');
    });
  });
});

describe('MessageStore', () => {
  let store: MessageStore;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({});
    store = TestBed.inject(MessageStore);
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('should be created', () => {
    expect(store).toBeTruthy();
  });

  it('should start with empty messages', () => {
    expect(store.all()).toEqual([]);
  });

  it('should append user messages', () => {
    store.appendUser({ role: 'user', content: 'test', turnId: 'abc' });
    expect(store.all().length).toBe(1);
    expect(store.all()[0].content).toBe('test');
  });

  it('should reset messages and clear localStorage', () => {
    store.appendUser({ role: 'user', content: 'test' });
    store.reset();
    expect(store.all()).toEqual([]);
    expect(localStorage.getItem('chat_graph_messages')).toBeNull();
  });

  it('should update content by turnId', () => {
    store.appendUser({ role: 'user', content: 'original', turnId: 'abc' });
    store.updateContent('abc', 'updated');
    expect(store.all()[0].content).toBe('updated');
  });

  it('should load from localStorage on construction', () => {
    const storedMessages = [{ role: 'user' as const, content: 'stored' }];
    localStorage.setItem('chat_graph_messages', JSON.stringify(storedMessages));

    TestBed.resetTestingModule();
    TestBed.configureTestingModule({});
    const freshStore = TestBed.inject(MessageStore);
    expect(freshStore.all()).toEqual(storedMessages);
  });

  it('should handle corrupted localStorage gracefully', () => {
    localStorage.setItem('chat_graph_messages', 'not-json');

    TestBed.resetTestingModule();
    TestBed.configureTestingModule({});
    const freshStore = TestBed.inject(MessageStore);
    expect(freshStore.all()).toEqual([]);
  });
});
