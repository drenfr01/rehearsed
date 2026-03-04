import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, ActivatedRoute } from '@angular/router';
import { provideAnimations } from '@angular/platform-browser/animations';
import { of } from 'rxjs';
import { OneOnOneConversation } from './one-on-one-conversation';
import { GeminiLiveService } from '../../core/services/gemini-live.service';

describe('OneOnOneConversation', () => {
  let component: OneOnOneConversation;
  let fixture: ComponentFixture<OneOnOneConversation>;

  beforeEach(async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({
      imports: [OneOnOneConversation],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimations(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: {
              queryParams: { scenarioId: '1', agentId: 'agent-1' },
            },
          },
        },
      ],
    }).compileComponents();

    const geminiService = TestBed.inject(GeminiLiveService);
    spyOn(geminiService, 'connect').and.returnValue(Promise.resolve());

    fixture = TestBed.createComponent(OneOnOneConversation);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => localStorage.clear());

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should expose connection state from GeminiLiveService', () => {
    expect(['disconnected', 'connecting', 'connected', 'error']).toContain(
      component['connectionState']()
    );
  });

  describe('getAgentAvatarUrl', () => {
    it('should return empty string when no agent', () => {
      expect(component.getAgentAvatarUrl()).toBe('');
    });
  });
});
