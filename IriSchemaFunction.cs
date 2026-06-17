using System.Net;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Azure.Functions.Worker.Http;

public class IriSchemaFunction
{
    private readonly SchemaProvider _schemaProvider;

    public IriSchemaFunction()
    {
        _schemaProvider = new SchemaProvider(AppConfig.GetSqlConnectionString());
    }

    [Function("GetDatabaseSchema")]
    public async Task<HttpResponseData> Run(
        [HttpTrigger(AuthorizationLevel.Anonymous, "get")] HttpRequestData req)
    {
        var response = req.CreateResponse(HttpStatusCode.OK);
        HttpCors.Apply(response);

        try
        {
            string schema = await _schemaProvider.GetSchemaTextAsync();
            await response.WriteAsJsonAsync(new
            {
                success = true,
                schema,
                hint = "Copy useful parts into schema.sql and sample_queries.txt for better answers."
            });
        }
        catch (Exception ex)
        {
            await response.WriteAsJsonAsync(new
            {
                success = false,
                error = ex.Message
            });
        }

        return response;
    }

    public async Task<object> ProcessAsync()
    {
        try
        {
            string schema = await _schemaProvider.GetSchemaTextAsync();
            return new
            {
                success = true,
                schema,
                hint = "Copy useful parts into schema.sql and sample_queries.txt for better answers."
            };
        }
        catch (Exception ex)
        {
            return new
            {
                success = false,
                error = ex.Message
            };
        }
    }
}
