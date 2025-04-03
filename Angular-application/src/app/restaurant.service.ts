import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../environments/environment';

interface Restaurant {
  id: number;
  name: string;
  cuisine: string;
  rating: number;
}

@Injectable({
  providedIn: 'root',
})
export class RestaurantService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getRestaurants(): Observable<Restaurant[]> {
    return this.http.get<Restaurant[]>(`${this.apiUrl}/restaurants/`);
  }
}
