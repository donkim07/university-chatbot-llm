import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { ChatService } from './chat.service';

describe('ChatService', () => {
  let service: ChatService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        ChatService,
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    });
    service = TestBed.inject(ChatService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    // Expect the automatic HTTP requests made in the constructor
    const reqHealth = httpMock.expectOne('http://localhost:8000/health');
    expect(reqHealth.request.method).toBe('GET');
    reqHealth.flush({
      status: 'healthy',
      backend: 'FastAPI',
      llm_connected: true,
      llm_message: 'OK',
      model_configured: 'llama3'
    });

    const reqSessions = httpMock.expectOne('http://localhost:8000/sessions');
    expect(reqSessions.request.method).toBe('GET');
    reqSessions.flush([]);

    expect(service).toBeTruthy();
  });
});
