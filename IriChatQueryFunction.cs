using System.Net;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Azure.Functions.Worker.Http;
using Microsoft.Data.SqlClient;

public class IriChatQueryFunction
{
    private const int MaxRows = 100;

    private readonly string? _sqlConnectionString;
    private readonly OpenAiClient _openAi;
    private readonly SchemaProvider _schemaProvider;

    public IriChatQueryFunction()
    {
        _sqlConnectionString = AppConfig.GetSqlConnectionString();
        _openAi = new OpenAiClient(
            Environment.GetEnvironmentVariable("OpenAIApiKey"),
            Environment.GetEnvironmentVariable("OpenAIModel"));
        _schemaProvider = new SchemaProvider(_sqlConnectionString);
    }

    [Function("AskQuestion")]
    public async Task<HttpResponseData> Run(
        [HttpTrigger(AuthorizationLevel.Anonymous, "post")] HttpRequestData req)
    {
        var response = req.CreateResponse(HttpStatusCode.OK);
        HttpCors.Apply(response);

        var body = await new StreamReader(req.Body).ReadToEndAsync();
        var result = await ProcessAsync(body);
        await response.WriteAsJsonAsync(result);
        return response;
    }

    public async Task<object> ProcessAsync(string body)
    {
        var (question, history, confirmedSurname, confirmedCustomerId) = ChatHistoryParser.ParseRequest(body);

        if (string.IsNullOrWhiteSpace(question))
        {
            return new { error = "Send JSON like { \"message\": \"your question\", \"history\": [] }." };
        }

        if (string.IsNullOrWhiteSpace(_sqlConnectionString))
        {
            return new { error = "SqlConnectionString is not configured." };
        }

        if (string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable("OpenAIApiKey")))
        {
            return new
            {
                answer = "Chat is not set up yet. Add your OpenAI API key to local.settings.json when you're ready."
            };
        }

        try
        {
            string? customersTable = await _schemaProvider.GetCustomersTableNameAsync();
            if (string.IsNullOrWhiteSpace(customersTable))
            {
                var tables = await _schemaProvider.ListTablesAsync();
                return new
                {
                    answer = "I can't find a Customers table in bank_data. Create/import your data first, then try again.",
                    error = tables.Count == 0
                        ? "No tables found in bank_data."
                        : $"Tables found: {string.Join(", ", tables)}"
                };
            }

            string sqlQuery = await GenerateSqlAsync(question, history, customersTable, confirmedSurname, confirmedCustomerId);
            sqlQuery = SqlSafety.CleanSql(sqlQuery, customersTable);

            if (sqlQuery.Equals("NA", StringComparison.OrdinalIgnoreCase))
            {
                return new
                {
                    query = "NA",
                    answer = "I couldn't map that question to your bank_data tables. Open /api/GetDatabaseSchema to see table and column names, then ask using those names — for example: \"What is the credit score for customers named Hill?\"",
                    data = Array.Empty<object>(),
                    chart_type = "table"
                };
            }

            if (!SqlSafety.TryValidateSelectQuery(sqlQuery, out string validationError))
            {
                return new
                {
                    query = sqlQuery,
                    answer = $"Query blocked for safety: {validationError}",
                    data = Array.Empty<object>(),
                    chart_type = "table"
                };
            }

            var results = await ExecuteSqlAsync(sqlQuery);
            var candidates = SurnameDisambiguation.GetCandidates(results);

            if (SurnameDisambiguation.ShouldConfirm(candidates, question, confirmedCustomerId))
            {
                return new
                {
                    query = sqlQuery,
                    answer = $"I found {candidates.Count} matching customers. Which one did you mean?",
                    needs_confirmation = true,
                    candidates = candidates.Select(c => new
                    {
                        customer_id = c.CustomerId,
                        surname = c.Surname
                    }),
                    data = results,
                    chart_type = "table"
                };
            }

            var (answer, chartType) = await GenerateAnswerAsync(
                question, history, results, confirmedSurname, confirmedCustomerId);
            chartType = ChartRecommender.Recommend(results, chartType, question);

            return new
            {
                query = sqlQuery,
                answer,
                data = results,
                chart_type = chartType
            };
        }
        catch (SqlException ex)
        {
            return new
            {
                answer = "I couldn't run the database query. The table or column name may be wrong for your bank_data database.",
                error = ex.Message
            };
        }
        catch (Exception ex)
        {
            return new
            {
                error = ex.Message,
                answer = ex.Message.Contains("OpenAI", StringComparison.OrdinalIgnoreCase)
                    ? "ChatGPT request failed. Check your API key, billing, and restart the app after updating local.settings.json."
                    : $"Something went wrong: {ex.Message}"
            };
        }
    }

    private static string ExtractSqlQuery(string raw)
    {
        raw = raw
            .Replace("```json", "", StringComparison.OrdinalIgnoreCase)
            .Replace("```sql", "", StringComparison.OrdinalIgnoreCase)
            .Replace("```", "")
            .Trim();

        try
        {
            using var doc = JsonDocument.Parse(raw);
            foreach (var propertyName in new[] { "query", "Query", "sql", "SQL" })
            {
                if (doc.RootElement.TryGetProperty(propertyName, out var queryProp))
                    return queryProp.GetString() ?? "NA";
            }
        }
        catch
        {
            Console.WriteLine("[WARN] Could not parse SQL JSON response.");
        }

        var sqlMatch = Regex.Match(
            raw,
            @"\bSELECT\b[\s\S]+",
            RegexOptions.IgnoreCase);

        if (sqlMatch.Success)
            return sqlMatch.Value.Trim().TrimEnd(';');

        return raw;
    }

    private async Task<string> GenerateSqlAsync(
        string question,
        List<ChatMessage> history,
        string customersTable,
        string? confirmedSurname,
        string? confirmedCustomerId)
    {
        string schemaText = await _schemaProvider.GetSchemaTextAsync();
        string instructionsText = SchemaProvider.LoadTextFile("instructions.txt");
        string samplesText = SchemaProvider.LoadTextFile("sample_queries.txt");
        string enhancedQuestion = MultiPartQuestions.EnhanceForSql(question);

        return ExtractSqlQuery(await _openAi.GetCompletionAsync(
            systemPrompt: $"{instructionsText}\n\nDatabase Schema:\n{schemaText}\n\nExample Queries:\n{samplesText}",
            userPrompt: enhancedQuestion));
    }

    private async Task<List<Dictionary<string, object?>>> ExecuteSqlAsync(string sqlQuery)
    {
        var results = new List<Dictionary<string, object?>>();

        await using var connection = new SqlConnection(_sqlConnectionString);
        await connection.OpenAsync();
        await using var command = new SqlCommand(sqlQuery, connection);
        await using var reader = await command.ExecuteReaderAsync();

        var columnNames = Enumerable.Range(0, reader.FieldCount)
            .Select(i => reader.GetName(i))
            .ToList();

        int rowCount = 0;
        while (await reader.ReadAsync() && rowCount < MaxRows)
        {
            var row = new Dictionary<string, object?>();
            foreach (var columnName in columnNames)
                row[columnName] = reader[columnName];

            results.Add(row);
            rowCount++;
        }

        return results;
    }

    private async Task<(string answer, string chartType)> GenerateAnswerAsync(
        string question,
        List<ChatMessage> history,
        List<Dictionary<string, object?>> results,
        string? confirmedSurname,
        string? confirmedCustomerId)
    {
        string enhancedQuestion = MultiPartQuestions.EnhanceForAnswer(question);
        string rawAnswer = await _openAi.GetCompletionAsync(
            systemPrompt: "You are a helpful data analyst. Summarize query results as a clear, concise answer. Include notable insights. Your response will be shown in a web chat interface.",
            userPrompt: $"{enhancedQuestion}\n\nData: {JsonSerializer.Serialize(results)}");

        string chartType = ChartRecommender.Recommend(results, "table", question);

        return (rawAnswer, chartType);
    }
}
