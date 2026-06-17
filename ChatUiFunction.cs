using System.Net;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Azure.Functions.Worker.Http;

public class ChatUiFunction
{
    [Function("Chat")]
    public async Task<HttpResponseData> Run(
        [HttpTrigger(AuthorizationLevel.Anonymous, "get")] HttpRequestData req)
    {
        var response = req.CreateResponse(HttpStatusCode.OK);
        HttpCors.Apply(response);
        response.Headers.Add("Content-Type", "text/html; charset=utf-8");

        string path = Path.Combine(AppContext.BaseDirectory, "chat.html");
        string html = File.Exists(path)
            ? await File.ReadAllTextAsync(path)
            : "<h1>chat.html not found</h1>";

        await response.WriteStringAsync(html);
        return response;
    }
}
