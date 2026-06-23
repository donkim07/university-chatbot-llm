import { Component, inject, OnInit } from '@angular/core';
import { NgClass } from '@angular/common';
import { Router, RouterOutlet } from '@angular/router';
import { ChatService } from './services/chat.service';

@Component({
  selector: 'app-root',
  imports: [NgClass, RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnInit {
  protected readonly chatService = inject(ChatService);
  private readonly router = inject(Router);

  // Expose signals to the template
  protected readonly sessions = this.chatService.sessions;
  protected readonly currentSessionId = this.chatService.currentSessionId;
  protected readonly systemStatus = this.chatService.systemStatus;
  protected readonly healthDetails = this.chatService.healthDetails;

  ngOnInit() {
    this.checkSystemHealth();
  }

  protected checkSystemHealth() {
    this.chatService.checkSystemHealth();
  }

  protected startNewChat() {
    this.chatService.currentSessionId.set(null);
    this.router.navigate(['/']);
  }

  protected selectSession(sessionId: string) {
    this.router.navigate(['/chat', sessionId]);
  }

  protected deleteSession(sessionId: string, event: MouseEvent) {
    event.stopPropagation(); // Prevent selecting the session when clicking delete

    if (confirm('Are you sure you want to delete this chat conversation?')) {
      this.chatService.deleteSession(sessionId).subscribe({
        next: () => {
          if (this.currentSessionId() === sessionId) {
            this.startNewChat();
          }
        },
        error: (err) => console.error('Failed to delete session:', err),
      });
    }
  }
}
