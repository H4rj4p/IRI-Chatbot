using MySqlConnector;

public static class AppConfig
{
    private static readonly string[] PlaceholderHosts =
    {
        "YOUR_WINDOWS_IP", "YOUR_SERVER", "localhost"
    };

    public static string? GetSqlConnectionString()
    {
        string? connectionString = Environment.GetEnvironmentVariable("SqlConnectionString");
        string? hostOverride = Environment.GetEnvironmentVariable("MySqlHost");

        if (string.IsNullOrWhiteSpace(connectionString))
            return null;

        if (string.IsNullOrWhiteSpace(hostOverride))
            return connectionString;

        hostOverride = hostOverride.Trim();
        var builder = new MySqlConnectionStringBuilder(connectionString)
        {
            Server = hostOverride,
            ConnectionTimeout = 30
        };

        return builder.ConnectionString;
    }

    public static string? GetConfigError()
    {
        string? host = Environment.GetEnvironmentVariable("MySqlHost")?.Trim();

        // Empty MySqlHost = use Server from SqlConnectionString (e.g. localhost on Windows)
        if (string.IsNullOrWhiteSpace(host))
            return null;

        if (PlaceholderHosts.Contains(host, StringComparer.OrdinalIgnoreCase))
            return $"MySqlHost is still '{host}'. Replace it with your Windows IPv4 address from ipconfig on Windows.";

        if (!System.Net.IPAddress.TryParse(host, out _))
            return $"MySqlHost '{host}' does not look like an IP address. Use the IPv4 from ipconfig, e.g. 192.168.1.105.";

        return null;
    }
}
