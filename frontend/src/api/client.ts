import axios from 'axios';

const apiClient = axios.create({
  baseURL: '',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

export default apiClient;
