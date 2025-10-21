using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using MrGaming.SDK.Exceptions;
using MrGaming.SDK.Models;

namespace MrGaming.SDK.Http
{
    /// <summary>
    /// HTTP客户端配置
    /// </summary>
    public class HttpClientConfig
    {
        public string BaseUrl { get; set; } = string.Empty;
        public TimeSpan Timeout { get; set; } = TimeSpan.FromSeconds(30);
        public int RetryCount { get; set; } = 3;
        public TimeSpan RetryDelay { get; set; } = TimeSpan.FromSeconds(1);
        public Dictionary<string, string> DefaultHeaders { get; set; } = new Dictionary<string, string>();
    }

    /// <summary>
    /// HTTP客户端
    /// </summary>
    public class HttpClient : IDisposable
    {
        private readonly System.Net.Http.HttpClient _httpClient;
        private readonly HttpClientConfig _config;
        private readonly ILogger<HttpClient>? _logger;
        private string? _authToken;
        private bool _disposed;

        public HttpClient(HttpClientConfig config, ILogger<HttpClient>? logger = null)
        {
            _config = config ?? throw new ArgumentNullException(nameof(config));
            _logger = logger;

            _httpClient = new System.Net.Http.HttpClient
            {
                Timeout = config.Timeout,
                BaseAddress = new Uri(config.BaseUrl)
            };

            // 设置默认请求头
            _httpClient.DefaultRequestHeaders.Add("User-Agent", "MrGaming.SDK.CSharp/1.0.0");
            _httpClient.DefaultRequestHeaders.Add("X-SDK-Version", "1.0.0");
            _httpClient.DefaultRequestHeaders.Add("X-SDK-Platform", "C#");

            foreach (var header in config.DefaultHeaders)
            {
                _httpClient.DefaultRequestHeaders.TryAddWithoutValidation(header.Key, header.Value);
            }
        }

        /// <summary>
        /// 设置认证令牌
        /// </summary>
        public void SetAuthToken(string token)
        {
            if (string.IsNullOrWhiteSpace(token))
            {
                throw new ArgumentException("认证令牌不能为空", nameof(token));
            }

            _authToken = token.Trim();
            _httpClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", _authToken);
        }

        /// <summary>
        /// 清除认证令牌
        /// </summary>
        public void ClearAuthToken()
        {
            _authToken = null;
            _httpClient.DefaultRequestHeaders.Authorization = null;
        }

        /// <summary>
        /// 设置自定义请求头
        /// </summary>
        public void SetHeader(string name, string value)
        {
            if (string.IsNullOrWhiteSpace(name))
            {
                throw new ArgumentException("请求头名称不能为空", nameof(name));
            }

            if (string.IsNullOrWhiteSpace(value))
            {
                _httpClient.DefaultRequestHeaders.Remove(name);
            }
            else
            {
                _httpClient.DefaultRequestHeaders.TryAddWithoutValidation(name, value);
            }
        }

        /// <summary>
        /// GET请求
        /// </summary>
        public async Task<ApiResponse<T>> GetAsync<T>(string endpoint, Dictionary<string, string>? parameters = null, CancellationToken cancellationToken = default)
        {
            var url = BuildUrl(endpoint, parameters);
            return await ExecuteRequestAsync<ApiResponse<T>>(HttpMethod.Get, url, null, cancellationToken);
        }

        /// <summary>
        /// POST请求
        /// </summary>
        public async Task<ApiResponse<T>> PostAsync<T>(string endpoint, object? data = null, CancellationToken cancellationToken = default)
        {
            return await ExecuteRequestAsync<ApiResponse<T>>(HttpMethod.Post, endpoint, data, cancellationToken);
        }

        /// <summary>
        /// PUT请求
        /// </summary>
        public async Task<ApiResponse<T>> PutAsync<T>(string endpoint, object? data = null, CancellationToken cancellationToken = default)
        {
            return await ExecuteRequestAsync<ApiResponse<T>>(HttpMethod.Put, endpoint, data, cancellationToken);
        }

        /// <summary>
        /// PATCH请求
        /// </summary>
        public async Task<ApiResponse<T>> PatchAsync<T>(string endpoint, object? data = null, CancellationToken cancellationToken = default)
        {
            return await ExecuteRequestAsync<ApiResponse<T>>(HttpMethod.Patch, endpoint, data, cancellationToken);
        }

        /// <summary>
        /// DELETE请求
        /// </summary>
        public async Task<ApiResponse<T>> DeleteAsync<T>(string endpoint, CancellationToken cancellationToken = default)
        {
            return await ExecuteRequestAsync<ApiResponse<T>>(HttpMethod.Delete, endpoint, null, cancellationToken);
        }

        /// <summary>
        /// 执行HTTP请求
        /// </summary>
        private async Task<TResponse> ExecuteRequestAsync<TResponse>(HttpMethod method, string endpoint, object? data, CancellationToken cancellationToken)
        {
            var attempt = 0;
            Exception? lastException = null;

            while (attempt < _config.RetryCount)
            {
                attempt++;
                try
                {
                    return await ExecuteSingleRequestAsync<TResponse>(method, endpoint, data, cancellationToken);
                }
                catch (Exception ex) when (ShouldRetry(ex) && attempt < _config.RetryCount)
                {
                    lastException = ex;
                    _logger?.LogWarning(ex, "请求失败，{delay}ms后进行第{attempt}次重试: {url}",
                        _config.RetryDelay.TotalMilliseconds, attempt + 1, endpoint);

                    await Task.Delay(_config.RetryDelay, cancellationToken);
                }
            }

            throw lastException ?? new InvalidOperationException("未知错误");
        }

        /// <summary>
        /// 执行单次HTTP请求
        /// </summary>
        private async Task<TResponse> ExecuteSingleRequestAsync<TResponse>(HttpMethod method, string endpoint, object? data, CancellationToken cancellationToken)
        {
            using var request = new HttpRequestMessage(method, endpoint);

            if (data != null)
            {
                var json = JsonSerializer.Serialize(data, new JsonSerializerOptions
                {
                    PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
                    DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull
                });

                request.Content = new StringContent(json, Encoding.UTF8, "application/json");
            }

            _logger?.LogDebug("发送HTTP请求: {method} {url}", method.Method, endpoint);
            if (data != null)
            {
                _logger?.LogDebug("请求内容: {content}", await request.Content!.ReadAsStringAsync(cancellationToken));
            }

            using var response = await _httpClient.SendAsync(request, cancellationToken);
            var responseContent = await response.Content.ReadAsStringAsync(cancellationToken);

            _logger?.LogDebug("收到HTTP响应: {status} {url}", response.StatusCode, endpoint);
            _logger?.LogDebug("响应内容: {content}", responseContent);

            if (!response.IsSuccessStatusCode)
            {
                throw CreateApiException(response, responseContent);
            }

            try
            {
                var result = JsonSerializer.Deserialize<TResponse>(responseContent, new JsonSerializerOptions
                {
                    PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
                    PropertyNameCaseInsensitive = true
                });

                return result ?? throw new InvalidOperationException("响应反序列化失败");
            }
            catch (JsonException ex)
            {
                _logger?.LogError(ex, "响应反序列化失败: {content}", responseContent);
                throw new ApiException("响应格式错误", (int)response.StatusCode, responseContent);
            }
        }

        /// <summary>
        /// 判断是否应该重试
        /// </summary>
        private bool ShouldRetry(Exception exception)
        {
            return exception is NetworkException ||
                   (exception is ApiException apiEx && IsRetryableStatusCode(apiEx.StatusCode));
        }

        /// <summary>
        /// 判断状态码是否可重试
        /// </summary>
        private static bool IsRetryableStatusCode(int? statusCode)
        {
            if (!statusCode.HasValue) return false;

            var retryableStatusCodes = new[]
            {
                408, // Request Timeout
                429, // Too Many Requests
                500, // Internal Server Error
                502, // Bad Gateway
                503, // Service Unavailable
                504, // Gateway Timeout
                520, // Unknown Error
                521, // Web Server Is Down
                522, // Connection Timed Out
                523, // Origin Is Unreachable
                524  // A Timeout Occurred
            };

            return retryableStatusCodes.Contains(statusCode.Value);
        }

        /// <summary>
        /// 创建API异常
        /// </summary>
        private ApiException CreateApiException(HttpResponseMessage response, string content)
        {
            var statusCode = (int)response.StatusCode;
            var message = $"HTTP {statusCode}: {response.ReasonPhrase}";

            try
            {
                var errorResponse = JsonSerializer.Deserialize<Dictionary<string, object>>(content);
                if (errorResponse?.ContainsKey("message") == true)
                {
                    message = errorResponse["message"].ToString() ?? message;
                }
            }
            catch
            {
                // 忽略JSON解析错误
            }

            return new ApiException(message, statusCode, content);
        }

        /// <summary>
        /// 构建URL
        /// </summary>
        private static string BuildUrl(string endpoint, Dictionary<string, string>? parameters)
        {
            if (parameters == null || parameters.Count == 0)
            {
                return endpoint;
            }

            var queryString = string.Join("&",
                parameters.Select(kvp => $"{Uri.EscapeDataString(kvp.Key)}={Uri.EscapeDataString(kvp.Value)}"));

            return string.IsNullOrEmpty(queryString) ? endpoint : $"{endpoint}?{queryString}";
        }

        /// <summary>
        /// 释放资源
        /// </summary>
        public void Dispose()
        {
            if (!_disposed)
            {
                _httpClient?.Dispose();
                _disposed = true;
            }
        }
    }
}