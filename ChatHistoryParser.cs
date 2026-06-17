using System.Text.Json;

public record ChatMessage(string Role, string Content);

public static class ChatHistoryParser
{
    public static (string message, List<ChatMessage> history, string? confirmedSurname, string? confirmedCustomerId) ParseRequest(string body)
    {
        using var doc = JsonDocument.Parse(body);
        string message = doc.RootElement.TryGetProperty("message", out var msg)
            ? msg.GetString() ?? ""
            : "";

        string? confirmedSurname = doc.RootElement.TryGetProperty("confirmed_surname", out var surnameEl)
            ? surnameEl.GetString()
            : null;

        string? confirmedCustomerId = doc.RootElement.TryGetProperty("confirmed_customer_id", out var customerIdEl)
            ? customerIdEl.GetString()
            : null;

        var history = new List<ChatMessage>();
        if (doc.RootElement.TryGetProperty("history", out var historyEl) &&
            historyEl.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in historyEl.EnumerateArray())
            {
                string role = item.TryGetProperty("role", out var r) ? r.GetString() ?? "" : "";
                string content = item.TryGetProperty("content", out var c) ? c.GetString() ?? "" : "";
                if (!string.IsNullOrWhiteSpace(role) && !string.IsNullOrWhiteSpace(content))
                    history.Add(new ChatMessage(role, content));
            }
        }

        return (message, history, confirmedSurname, confirmedCustomerId);
    }

    public static string FormatForPrompt(
        string question,
        List<ChatMessage> history,
        string? confirmedSurname = null,
        string? confirmedCustomerId = null)
    {
        if (history.Count == 0)
            return question;

        var lines = new List<string> { "Conversation so far:" };
        foreach (var item in history.TakeLast(8))
        {
            string speaker = item.Role.Equals("user", StringComparison.OrdinalIgnoreCase) ? "User" : "Assistant";
            lines.Add($"{speaker}: {item.Content}");
        }

        lines.Add($"Current question: {question}");

        if (!string.IsNullOrWhiteSpace(confirmedCustomerId))
        {
            lines.Add(
                $"The user confirmed they mean CustomerId exactly: {confirmedCustomerId}. " +
                "Use WHERE CustomerId = that exact value.");
        }
        else if (!string.IsNullOrWhiteSpace(confirmedSurname))
        {
            lines.Add(
                $"The user confirmed they mean customer with Surname exactly: {confirmedSurname}. " +
                "Use WHERE Surname = that exact value (not LIKE).");
        }

        return string.Join(Environment.NewLine, lines);
    }
}
