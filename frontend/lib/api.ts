import axios from "axios";
import { env } from "./env";
import { toast } from "@/components/toast";

const baseURL = env.apiBaseUrl || "http://localhost:8000";

export const api = axios.create({
  baseURL,
});

api.interceptors.response.use(
  (res) => res,
  (error) => {
    const message = error.response?.data?.detail || error.message;
    toast.error(message || "Unexpected error");
    return Promise.reject(error);
  }
);
