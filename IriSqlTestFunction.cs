using System.Net;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Azure.Functions.Worker.Http;
using MySqlConnector;

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

        if (string.IsNullOrWhiteSpace(_sqlConnectionString))
        {
            await response.WriteAsJsonAsync(new
            {
                success = false,
                message = "SqlConnectionString is not set in local.settings.json (Values section)."
            });
            return response;
        }

        string? configError = AppConfig.GetConfigError();
        if (configError != null)
        {
            await response.WriteAsJsonAsync(new
            {
                success = false,
                message = "Database config needs to be updated.",
                error = configError
            });
            return response;
        }

        try
        {
            await using var connection = new MySqlConnection(_sqlConnectionString);
            await connection.OpenAsync();

            await using var command = new MySqlCommand(
                "SELECT VERSION() AS ServerVersion, DATABASE() AS DatabaseName",
                connection);
            await using var reader = await command.ExecuteReaderAsync();

            string serverVersion = "";
            string databaseName = "";

            if (await reader.ReadAsync())
            {
                serverVersion = reader["ServerVersion"]?.ToString() ?? "";
                databaseName = reader["DatabaseName"]?.ToString() ?? "";
            }

            await response.WriteAsJsonAsync(new
            {
                success = true,
                message = "Connected to MySQL successfully.",
                server = connection.DataSource,
                database = databaseName,
                serverVersion
            });
        }
        catch (Exception ex)
        {
            response.StatusCode = HttpStatusCode.OK;
            await response.WriteAsJsonAsync(new
            {
                success = false,
                message = "Failed to connect to MySQL.",
                error = ex.Message,
                hint = "Connection refused usually means: wrong MySqlHost IP, MySQL not allowing remote connections, or Windows firewall blocking port 3306."
            });
        }

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
            await using var connection = new MySqlConnection(_sqlConnectionString);
            await connection.OpenAsync();

            await using var command = new MySqlCommand(
                "SELECT VERSION() AS ServerVersion, DATABASE() AS DatabaseName",
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
                message = "Connected to MySQL successfully.",
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
                message = "Failed to connect to MySQL.",
                error = ex.Message,
                hint = "Connection refused usually means: wrong MySqlHost IP, MySQL not allowing remote connections, or Windows firewall blocking port 3306."
            };
        }
    }
}
