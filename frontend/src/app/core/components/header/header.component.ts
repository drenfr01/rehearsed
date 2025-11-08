import { Component, DestroyRef, inject } from '@angular/core';
import { AuthService } from '../../services/auth.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-header',
  imports: [],
  templateUrl: './header.html',
  styleUrl: './header.css',
})
export class Header {
  private authService = inject(AuthService);
  private destroyRef = inject(DestroyRef);
  private router = inject(Router);

  logout() {
    this.authService.logout();
  }

  createNewSession() {
    const subscription = this.authService.createSession().subscribe({
      next: () => {
        this.router.navigate(['/app/scenario-selection'], { replaceUrl: true });
      },
      error: (error: Error) => {
        console.log(error.message);
      },
    });
    this.destroyRef.onDestroy(() => {
      subscription.unsubscribe();
    });
  }

}
