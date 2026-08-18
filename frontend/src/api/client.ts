import axios from "axios";
import type { IngestPayload, Item, QueryResponse } from "../types";
import { normalizeApiError } from "../utils/normalizeApiError";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(normalizeApiError(error))
);

export const ingestItem = (payload: IngestPayload) =>
  apiClient.post<Item>("/ingest", payload).then((r) => r.data);

export const listItems = () => apiClient.get<Item[]>("/items").then((r) => r.data);

export const askQuestion = (question: string) =>
  apiClient.post<QueryResponse>("/query", { question }).then((r) => r.data);

export const deleteItem = (id: number) => apiClient.delete(`/items/${id}`).then(() => undefined);
