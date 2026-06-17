using System.Text.RegularExpressions;

public static class MultiPartQuestions
{
    private static readonly Regex MultiPartPattern = new(
        @"\b(and|also|plus|as\s+well\s+as)\b" +
        @"|\?[^?]*\?" +
        @"|,\s*(how|what|who|where|when|why|show|give|tell|list|count|average|total)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    public static bool IsMultiPart(string question) =>
        !string.IsNullOrWhiteSpace(question) && MultiPartPattern.IsMatch(question);

    public static string EnhanceForSql(string question)
    {
        if (!IsMultiPart(question))
            return question;

        return question + Environment.NewLine + Environment.NewLine +
            "IMPORTANT: This message asks MULTIPLE things at once. " +
            "Return exactly ONE SELECT statement (no semicolons) that answers EVERY part. " +
            "Combine results using multiple columns, aggregates, CASE/SUM, and subqueries in the same query.";
    }

    public static string EnhanceForAnswer(string question)
    {
        if (!IsMultiPart(question))
            return question;

        return question + Environment.NewLine + Environment.NewLine +
            "IMPORTANT: Answer every part in 1-2 short lines total. Be terse.";
    }
}
