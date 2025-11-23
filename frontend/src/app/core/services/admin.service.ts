import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { User, UserCreate } from '../models/user.model';

@Injectable({
  providedIn: 'root',
})
export class AdminService {
  private httpClient = inject(HttpClient);
  private baseUrl = `${environment.baseUrl}/api/v1/admin`;

  /**
   * Get all users in the system
   */
  getAllUsers(): Observable<User[]> {
    return this.httpClient.get<User[]>(`${this.baseUrl}/users`);
  }

  /**
   * Get a specific user by ID
   */
  getUser(userId: number): Observable<User> {
    return this.httpClient.get<User>(`${this.baseUrl}/users/${userId}`);
  }

  /**
   * Create a new user
   */
  createUser(userData: UserCreate): Observable<User> {
    return this.httpClient.post<User>(`${this.baseUrl}/users`, userData);
  }

  /**
   * Update a user
   */
  updateUser(userId: number, email?: string, isAdmin?: boolean): Observable<User> {
    let params = new HttpParams();
    if (email !== undefined) {
      params = params.set('email', email);
    }
    if (isAdmin !== undefined) {
      params = params.set('is_admin', isAdmin.toString());
    }
    return this.httpClient.put<User>(`${this.baseUrl}/users/${userId}`, null, { params });
  }

  /**
   * Delete a user
   */
  deleteUser(userId: number): Observable<{ message: string }> {
    return this.httpClient.delete<{ message: string }>(`${this.baseUrl}/users/${userId}`);
  }
}

