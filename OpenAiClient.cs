using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

public class OpenAiClient
{
    private static readonly HttpClient Http = new();
    private readonly string? _apiKey;
    private readonly string _model;

    public OpenAiClient(string? apiKey, string? model)
    {
        _apiKey = apiKey;
        _model = string.IsNullOrWhiteSpace(model) ? "gpt-4o-mini" : model;
    }

    public async Task<string> GetCompletionAsync(string systemPrompt, string userPrompt)
    {
        if (string.IsNullOrWhiteSpace(_apiKey))
            throw new InvalidOperationException("OpenAIApiKey is not set in local.settings.json.");

        var payload = new
        {
            model = _model,
            temperature = 0,
            messages = new[]
            {
                new { role = "system", content = systemPrompt },
                new { role = "user", content = userPrompt }
            }
        };

        using var request = new HttpRequestMessage(HttpMethod.Post, "https://api.openai.com/v1/chat/completions");
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _apiKey);
        request.Content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");

        using var response = await Http.SendAsync(request);
        string body = await response.Content.ReadAsStringAsync();

        if (!response.IsSuccessStatusCode)
        {
            string message = TryExtractOpenAiError(body) ?? body;
            throw new InvalidOperationException($"OpenAI request failed: {message}");
        }

        using var doc = JsonDocument.Parse(body);
        return doc.RootElement
            .GetProperty("choices")[0]
            .GetProperty("message")
            .GetProperty("content")
            .GetString() ?? "";
    }

    private static string? TryExtractOpenAiError(string body)
    {
        try
        {
            using var doc = JsonDocument.Parse(body);
            if (doc.RootElement.TryGetProperty("error", out var error) &&
                error.TryGetProperty("message", out var message))
            {
                return message.GetString();
            }
        }
        catch
        {
        }

        return null;
    }
}
