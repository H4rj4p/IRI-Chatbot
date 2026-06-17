using System.Text.Json;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;

LoadLocalSettings();

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://localhost:7179");

builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
    {
        policy.AllowAnyOrigin().AllowAnyMethod().AllowAnyHeader();
    });
});

var app = builder.Build();

app.UseCors();

// Chat UI endpoint
app.MapGet("/api/Chat", async (HttpContext context) =>
{
    string path = Path.Combine(AppContext.BaseDirectory, "chat.html");
    string html = File.Exists(path)
        ? await File.ReadAllTextAsync(path)
        : "<h1>chat.html not found</h1>";
    context.Response.ContentType = "text/html; charset=utf-8";
    await context.Response.WriteAsync(html);
});

// Ask Question endpoint
app.MapPost("/api/AskQuestion", async (HttpContext context) =>
{
    var function = new IriChatQueryFunction();
    var body = await new StreamReader(context.Request.Body).ReadToEndAsync();
    
    try
    {
        var result = await function.ProcessAsync(body);
        context.Response.ContentType = "application/json";
        await context.Response.WriteAsJsonAsync(result);
    }
    catch (Exception ex)
    {
        context.Response.StatusCode = 500;
        context.Response.ContentType = "application/json";
        await context.Response.WriteAsJsonAsync(new { error = ex.Message });
    }
});

// Database Schema endpoint
app.MapGet("/api/GetDatabaseSchema", async (HttpContext context) =>
{
    var function = new IriSchemaFunction();
    var result = await function.ProcessAsync();
    context.Response.ContentType = "application/json";
    await context.Response.WriteAsJsonAsync(result);
});

// SQL Test endpoint
app.MapGet("/api/TestSqlConnection", async (HttpContext context) =>
{
    var function = new IriSqlTestFunction();
    var result = await function.ProcessAsync();
    context.Response.ContentType = "application/json";
    await context.Response.WriteAsJsonAsync(result);
});

app.MapPost("/api/TestSqlConnection", async (HttpContext context) =>
{
    var function = new IriSqlTestFunction();
    var result = await function.ProcessAsync();
    context.Response.ContentType = "application/json";
    await context.Response.WriteAsJsonAsync(result);
});

Console.WriteLine("Starting IRI Chatbot on http://localhost:7179/api/Chat");
app.Run();

static void LoadLocalSettings()
{
    string baseDir = AppContext.BaseDirectory;
    string[] paths =
    {
        Path.Combine(baseDir, "local.settings.json"),
        Path.Combine(Directory.GetCurrentDirectory(), "local.settings.json"),
        Path.Combine(baseDir, "..", "..", "..", "local.settings.json")
    };

    string? settingsPath = paths.FirstOrDefault(File.Exists);
    if (settingsPath == null)
        return;

    using var doc = JsonDocument.Parse(File.ReadAllText(settingsPath));
    if (!doc.RootElement.TryGetProperty("Values", out var values))
        return;

    foreach (var item in values.EnumerateObject())
    {
        string? value = item.Value.GetString();
        if (string.IsNullOrEmpty(value))
            continue;

        Environment.SetEnvironmentVariable(item.Name, value);
    }
}
