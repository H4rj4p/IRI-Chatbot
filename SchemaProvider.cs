using Microsoft.Data.SqlClient;

public class SchemaProvider
{
    private readonly string? _connectionString;
    private string? _cachedCustomersTable;

    public SchemaProvider(string? connectionString)
    {
        _connectionString = connectionString;
    }

    public async Task<string> GetSchemaTextAsync()
    {
        string fileSchema = LoadSchemaFile();
        string? liveTable = await GetCustomersTableNameAsync();

        if (!string.IsNullOrWhiteSpace(fileSchema) && !string.IsNullOrWhiteSpace(liveTable))
        {
            return fileSchema.Replace("Customers", liveTable, StringComparison.Ordinal);
        }

        if (!string.IsNullOrWhiteSpace(fileSchema))
            return fileSchema;

        return await LoadSchemaFromDatabaseAsync();
    }

    public async Task<string?> GetCustomersTableNameAsync()
    {
        if (!string.IsNullOrWhiteSpace(_cachedCustomersTable))
            return _cachedCustomersTable;

        if (string.IsNullOrWhiteSpace(_connectionString))
            return null;

        const string sql = """
            SELECT TOP 1 TABLE_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_CATALOG = DB_NAME()
              AND COLUMN_NAME IN (N'Surname', N'CreditScore', N'CustomerId')
            GROUP BY TABLE_NAME
            HAVING SUM(CASE WHEN COLUMN_NAME = N'Surname' THEN 1 ELSE 0 END) > 0
            ORDER BY TABLE_NAME
            """;

        try
        {
            await using var connection = new SqlConnection(_connectionString);
            await connection.OpenAsync();
            await using var command = new SqlCommand(sql, connection);
            var result = await command.ExecuteScalarAsync();
            _cachedCustomersTable = result?.ToString();
            return _cachedCustomersTable;
        }
        catch
        {
            return null;
        }
    }

    public async Task<List<string>> ListTablesAsync()
    {
        var tables = new List<string>();
        if (string.IsNullOrWhiteSpace(_connectionString))
            return tables;

        const string sql = """
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_CATALOG = DB_NAME()
              AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
            """;

        await using var connection = new SqlConnection(_connectionString);
        await connection.OpenAsync();
        await using var command = new SqlCommand(sql, connection);
        await using var reader = await command.ExecuteReaderAsync();
        while (await reader.ReadAsync())
            tables.Add(reader.GetString(0));

        return tables;
    }

    private static string LoadSchemaFile()
    {
        string path = Path.Combine(AppContext.BaseDirectory, "schema.sql");
        if (!File.Exists(path))
            return "";

        string content = File.ReadAllText(path).Trim();
        bool hasTableDefinition = content.Contains("CREATE TABLE", StringComparison.OrdinalIgnoreCase);
        return hasTableDefinition ? content : "";
    }

    private async Task<string> LoadSchemaFromDatabaseAsync()
    {
        if (string.IsNullOrWhiteSpace(_connectionString))
            return "-- No schema file and SqlConnectionString is not configured.";

        const string sql = """
            SELECT
                c.TABLE_NAME,
                c.COLUMN_NAME,
                c.DATA_TYPE,
                c.IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS c
            INNER JOIN INFORMATION_SCHEMA.TABLES t
                ON c.TABLE_CATALOG = t.TABLE_CATALOG
               AND c.TABLE_SCHEMA = t.TABLE_SCHEMA
               AND c.TABLE_NAME = t.TABLE_NAME
            WHERE t.TABLE_TYPE = 'BASE TABLE'
              AND c.TABLE_CATALOG = DB_NAME()
            ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION
            """;

        var lines = new List<string> { "-- Auto-generated from INFORMATION_SCHEMA" };
        await using var connection = new SqlConnection(_connectionString);
        await connection.OpenAsync();

        await using var command = new SqlCommand(sql, connection);
        await using var reader = await command.ExecuteReaderAsync();

        string? currentTable = null;
        while (await reader.ReadAsync())
        {
            string table = reader["TABLE_NAME"]?.ToString() ?? "";
            string column = reader["COLUMN_NAME"]?.ToString() ?? "";
            string dataType = reader["DATA_TYPE"]?.ToString() ?? "";
            string nullable = reader["IS_NULLABLE"]?.ToString() ?? "";

            if (table != currentTable)
            {
                if (currentTable != null)
                    lines.Add(");");
                lines.Add($"CREATE TABLE [{table}] (");
                currentTable = table;
            }

            lines.Add($"  [{column}] {dataType} NULL={nullable},");
        }

        if (currentTable != null)
            lines.Add(");");

        return string.Join(Environment.NewLine, lines);
    }

    public static string LoadTextFile(string fileName)
    {
        string path = Path.Combine(AppContext.BaseDirectory, fileName);
        return File.Exists(path) ? File.ReadAllText(path) : "";
    }
}
