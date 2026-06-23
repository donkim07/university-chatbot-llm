import { Component, OnInit, signal, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { NgClass } from '@angular/common';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  category?: string;
  rag_used?: boolean;
  matched_faq?: string;
  rating?: 'Good' | 'Average' | 'Poor';
}

interface HealthInfo {
  status: string;
  backend: string;
  llm_connected: boolean;
  llm_message: string;
  model_configured: string;
}

@Component({
  selector: 'app-root',
  imports: [FormsModule, NgClass],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnInit {
  private readonly http = inject(HttpClient);

  // Signals for state management
  protected readonly backendUrl = 'http://localhost:8000';
  protected readonly messages = signal<Message[]>([]);
  protected readonly userQuery = signal('');
  protected readonly isLoading = signal(false);
  protected readonly systemStatus = signal<'online' | 'degraded' | 'offline'>('offline');
  protected readonly healthDetails = signal<HealthInfo | null>(null);

  ngOnInit() {
    this.checkSystemHealth();
  }

  protected checkSystemHealth() {
    this.http.get<HealthInfo>(`${this.backendUrl}/health`).subscribe({
      next: (data) => {
        this.healthDetails.set(data);
        if (data.status === 'healthy') {
          this.systemStatus.set('online');
        } else {
          this.systemStatus.set('degraded');
        }
      },
      error: (err) => {
        console.error('Backend health check failed:', err);
        this.systemStatus.set('offline');
        this.healthDetails.set(null);
      }
    });
  }

  protected sendMessage() {
    const query = this.userQuery().trim();
    if (!query) {
      return;
    }

    // Add user query to chat history
    const userMsg: Message = {
      role: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    this.messages.update(msgs => [...msgs, userMsg]);
    this.userQuery.set('');
    
    // Set loading state
    this.isLoading.set(true);

    // Call backend API
    this.http.post<any>(`${this.backendUrl}/ask`, { question: query }).subscribe({
      next: (data) => {
        this.isLoading.set(false);
        const assistantMsg: Message = {
          role: 'assistant',
          content: data.answer,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          category: data.category,
          rag_used: data.rag_used,
          matched_faq: data.matched_faq
        };
        this.messages.update(msgs => [...msgs, assistantMsg]);
      },
      error: (err) => {
        this.isLoading.set(false);
        const errorDetail = err.error?.detail || 'Failed to communicate with the server. Please try again.';
        const errorMsg: Message = {
          role: 'assistant',
          content: `Error: ${errorDetail}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          category: 'Error'
        };
        this.messages.update(msgs => [...msgs, errorMsg]);
      }
    });
  }

  protected rateMessage(index: number, rating: 'Good' | 'Average' | 'Poor') {
    const msgs = this.messages();
    const msg = msgs[index];
    if (msg.role !== 'assistant') return;

    // Find the corresponding user question (usually the preceding message)
    let userQuestion = '';
    for (let i = index - 1; i >= 0; i--) {
      if (msgs[i].role === 'user') {
        userQuestion = msgs[i].content;
        break;
      }
    }

    // Set rating locally to update UI
    msg.rating = rating;
    this.messages.set([...msgs]);

    // Send rating to backend
    this.http.post(`${this.backendUrl}/feedback`, {
      question: userQuestion || 'N/A',
      answer: msg.content,
      rating: rating
    }).subscribe({
      next: () => console.log('Feedback submitted successfully'),
      error: (err) => console.error('Failed to submit feedback', err)
    });
  }
}
