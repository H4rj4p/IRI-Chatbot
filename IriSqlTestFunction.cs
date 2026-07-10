using System.Net;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Azure.Functions.Worker.Http;
using Microsoft.Data.SqlClient;

public class IriSqlTestFunction
{
    private readonly string? _sqlConnectionString;

    public IriSqlTestFunction()
    {
        _sqlConnectionString = AppConfig.GetSqlConnectionString();
    }

    [Function("TestSqlConnection")]
    public async Task<HttpResponseData> Run(
        [HttpTrigger(AuthorizationLevel.Anonymous, "get", "post")] HttpRequestData req)
    {
        var response = req.CreateResponse(HttpStatusCode.OK);
        HttpCors.Apply(response);
        await response.WriteAsJsonAsync(await ProcessAsync());
        return response;
    }

    public async Task<object> ProcessAsync()
    {
        if (string.IsNullOrWhiteSpace(_sqlConnectionString))
        {
            return new
            {
                success = false,
                message = "SqlConnectionString is not set in local.settings.json (Values section)."
            };
        }

        string? configError = AppConfig.GetConfigError();
        if (configError != null)
        {
            return new
            {
                success = false,
                message = "Database config needs to be updated.",
                error = configError
            };
        }

        try
        {
            await using var connection = new SqlConnection(_sqlConnectionString);
            await connection.OpenAsync();

            await using var command = new SqlCommand(
                "SELECT @@VERSION AS ServerVersion, DB_NAME() AS DatabaseName",
                connection);
            await using var reader = await command.ExecuteReaderAsync();

            string serverVersion = "";
            string databaseName = "";

            if (await reader.ReadAsync())
            {
                serverVersion = reader["ServerVersion"]?.ToString() ?? "";
                databaseName = reader["DatabaseName"]?.ToString() ?? "";
            }

            return new
            {
                success = true,
                message = "Connected to SQL Server successfully.",
                server = connection.DataSource,
                database = databaseName,
                serverVersion
            };
        }
        catch (Exception ex)
        {
            return new
            {
                success = false,
                message = "Failed to connect to SQL Server.",
                error = ex.Message,
                hint = "Connection refused usually means: wrong Server/host, SQL Server not allowing remote TCP connections, or firewall blocking port 1433."
            };
        }
    }
}
