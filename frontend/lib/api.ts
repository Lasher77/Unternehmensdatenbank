import axios from "axios";
import { env } from "./env";
import { toast } from "@/components/toast";

export const api = axios.create({
  baseURL: env.apiBaseUrl
});

api.interceptors.response.use(
  (res) => res,
  (error) => {
    const message = error.response?.data?.detail || error.message;
    toast.error(message || "Unexpected error");
    return Promise.reject(error);
  }
);
