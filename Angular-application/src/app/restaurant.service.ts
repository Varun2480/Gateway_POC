import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

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
  private apiUrl = '/restaurants'; // Assuming proxy is configured for /restaurants

  constructor(private http: HttpClient) {}

  getRestaurants(): Observable<Restaurant[]> {
    return this.http.get<Restaurant[]>(this.apiUrl);
  }
}