using Microsoft.Data.SqlClient;

public static class AppConfig
{
    private static readonly string[] PlaceholderHosts =
    {
        "YOUR_WINDOWS_IP", "YOUR_SERVER"
    };

    private static readonly string[] PlaceholderTokens =
    {
        "YOUR_SERVER", "YOUR_DATABASE", "YOUR_USER", "YOUR_PASSWORD", "YOUR_OPENAI_API_KEY", "sk-your-openai"
    };

    public static string? GetSqlConnectionString()
    {
        string? connectionString =
            Environment.GetEnvironmentVariable("SqlConnectionString")
            ?? Environment.GetEnvironmentVariable("SQLCONNSTR_SqlConnectionString")
            ?? Environment.GetEnvironmentVariable("CUSTOMCONNSTR_SqlConnectionString");

        string? hostOverride = Environment.GetEnvironmentVariable("SqlServerHost");

        if (string.IsNullOrWhiteSpace(connectionString))
            return null;

        if (string.IsNullOrWhiteSpace(hostOverride))
            return connectionString;

        hostOverride = hostOverride.Trim();
        var builder = new SqlConnectionStringBuilder(connectionString)
        {
            DataSource = hostOverride,
            ConnectTimeout = 30
        };

        return builder.ConnectionString;
    }

    public static string? GetConfigError()
    {
        string? connectionString = GetSqlConnectionString();
        if (string.IsNullOrWhiteSpace(connectionString))
            return "SqlConnectionString is not set. Add it to local.settings.json (Values section).";

        foreach (var token in PlaceholderTokens)
        {
            if (connectionString.Contains(token, StringComparison.OrdinalIgnoreCase))
                return $"SqlConnectionString still contains '{token}'. Replace the placeholders with your SQL Server details.";
        }

        string? host = Environment.GetEnvironmentVariable("SqlServerHost")?.Trim();

        // Empty SqlServerHost = use Server from SqlConnectionString
        if (string.IsNullOrWhiteSpace(host))
            return null;

        if (PlaceholderHosts.Contains(host, StringComparer.OrdinalIgnoreCase))
            return $"SqlServerHost is still '{host}'. Replace it with your SQL Server host, or leave it blank to use SqlConnectionString.";

        return null;
    }
}
