import axios, {
  AxiosInstance,
  AxiosError,
  InternalAxiosRequestConfig,
  AxiosResponse,
  AxiosRequestConfig,
} from "axios";
import { API_CONFIG } from "./constants";
import { useAuthStore } from "@store/authStore";

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_CONFIG.BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      // Don't set default Content-Type - let Axios handle it automatically
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor
    this.client.interceptors.request.use(
      (
        config: InternalAxiosRequestConfig & {
          _coldStartTimer?: ReturnType<typeof setTimeout>;
        },
      ) => {
        // Token is injected from authStore state
        const token = useAuthStore.getState().token;

        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }

        // Set Content-Type based on data type
        if (config.data instanceof FormData) {
          delete config.headers["Content-Type"];
        } else if (config.data && typeof config.data === "object") {
          config.headers["Content-Type"] = "application/json";
        }

        // If request takes > 5 seconds, notify user of cold start
        config._coldStartTimer = setTimeout(() => {
          import("sonner").then(({ toast }) => {
            toast.info(
              "Starting AI services... This usually takes less than a minute on the first request.",
              { id: "backend-cold-start-toast", duration: 15000 },
            );
          });
        }, 5000);

        return config;
      },
      (error: AxiosError) => {
        return Promise.reject(error);
      },
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (
        response: AxiosResponse & {
          config: InternalAxiosRequestConfig & {
            _coldStartTimer?: ReturnType<typeof setTimeout>;
          };
        },
      ) => {
        if (response.config._coldStartTimer) {
          clearTimeout(response.config._coldStartTimer);
        }
        import("sonner").then(({ toast }) => {
          toast.dismiss("backend-cold-start-toast");
        });
        return response;
      },
      (
        error: AxiosError & {
          config?: InternalAxiosRequestConfig & {
            _coldStartTimer?: ReturnType<typeof setTimeout>;
          };
        },
      ) => {
        if (error.config?._coldStartTimer) {
          clearTimeout(error.config._coldStartTimer);
        }
        import("sonner").then(({ toast }) => {
          toast.dismiss("backend-cold-start-toast");
        });

        if (error.response?.status === 401) {
          useAuthStore.getState().logout();
          error.name = "AuthenticationError";
        }
        return Promise.reject(error);
      },
    );
  }

  public get<T = unknown>(url: string, config?: AxiosRequestConfig) {
    return this.client.get<T>(url, config);
  }

  public post<T = unknown>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig,
  ) {
    return this.client.post<T>(url, data, config);
  }

  public put<T = unknown>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig,
  ) {
    return this.client.put<T>(url, data, config);
  }

  public delete<T = unknown>(url: string, config?: AxiosRequestConfig) {
    return this.client.delete<T>(url, config);
  }

  public patch<T = unknown>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig,
  ) {
    return this.client.patch<T>(url, data, config);
  }
}

export const apiClient = new ApiClient();
