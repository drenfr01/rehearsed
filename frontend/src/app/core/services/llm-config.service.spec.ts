import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { LlmConfigService } from './llm-config.service';
import { AgentLlmConfig } from '../models/llm-config.model';
import { environment } from '../../../environments/environment';

describe('LlmConfigService', () => {
  let service: LlmConfigService;
  let httpTesting: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    service = TestBed.inject(LlmConfigService);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('getLlmModels', () => {
    it('should GET /api/v1/llm-models', () => {
      const mockModels = [
        { id: 1, name: 'gemini-3.1-pro-preview' },
        { id: 2, name: 'gemini-3-flash-preview' },
      ];

      service.getLlmModels().subscribe((models) => {
        expect(models).toEqual(mockModels);
      });

      const req = httpTesting.expectOne(`${environment.baseUrl}/api/v1/llm-models`);
      expect(req.request.method).toBe('GET');
      req.flush(mockModels);
    });
  });

  describe('getAgentLlmConfigs', () => {
    it('should GET /api/v1/llm-config', () => {
      const mockConfigs: AgentLlmConfig[] = [
        { agent_type: 'student_agent', llm_model_id: 1, llm_model_name: 'gemini-3.1-pro-preview' },
      ];

      service.getAgentLlmConfigs().subscribe((configs) => {
        expect(configs).toEqual(mockConfigs);
      });

      const req = httpTesting.expectOne(`${environment.baseUrl}/api/v1/llm-config`);
      expect(req.request.method).toBe('GET');
      req.flush(mockConfigs);
    });
  });

  describe('updateAgentLlmConfig', () => {
    it('should POST /api/v1/llm-config', () => {
      const update = { agent_type: 'student_agent' as const, llm_model_id: 2 };
      const mockResponse: AgentLlmConfig = {
        agent_type: 'student_agent',
        llm_model_id: 2,
        llm_model_name: 'gemini-3-flash-preview',
      };

      service.updateAgentLlmConfig(update).subscribe((config) => {
        expect(config).toEqual(mockResponse);
      });

      const req = httpTesting.expectOne(`${environment.baseUrl}/api/v1/llm-config`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(update);
      req.flush(mockResponse);
    });
  });
});
