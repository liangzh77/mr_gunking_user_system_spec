using System;
using System.Text.Json.Serialization;

namespace MrGaming.SDK.Models
{
    /// <summary>
    /// API响应基类
    /// </summary>
    /// <typeparam name="T">响应数据类型</typeparam>
    public class ApiResponse<T>
    {
        [JsonPropertyName("success")]
        public bool Success { get; set; }

        [JsonPropertyName("data")]
        public T? Data { get; set; }

        [JsonPropertyName("message")]
        public string? Message { get; set; }

        [JsonPropertyName("error")]
        public string? Error { get; set; }

        [JsonPropertyName("code")]
        public int? Code { get; set; }

        public bool IsSuccess => Success && Data != null;
    }

    /// <summary>
    /// 分页响应基类
    /// </summary>
    /// <typeparam name="T">数据项类型</typeparam>
    public class PagedResponse<T>
    {
        [JsonPropertyName("items")]
        public List<T> Items { get; set; } = new List<T>();

        [JsonPropertyName("total")]
        public int Total { get; set; }

        [JsonPropertyName("page")]
        public int Page { get; set; }

        [JsonPropertyName("page_size")]
        public int PageSize { get; set; }

        [JsonPropertyName("total_pages")]
        public int TotalPages { get; set; }
    }

    /// <summary>
    /// 错误详情
    /// </summary>
    public class ErrorDetail
    {
        [JsonPropertyName("code")]
        public string Code { get; set; } = string.Empty;

        [JsonPropertyName("message")]
        public string Message { get; set; } = string.Empty;

        [JsonPropertyName("field")]
        public string? Field { get; set; }
    }
}