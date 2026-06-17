using System.Text.RegularExpressions;

public record CustomerCandidate(object? CustomerId, string Surname);

public static class SurnameDisambiguation
{
    private static readonly Regex ComparisonPattern = new(
        @"\b(or|vs|versus|compare|between|compared\s+to)\b",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    public static bool IsComparisonQuestion(string question) =>
        ComparisonPattern.IsMatch(question);

    public static List<CustomerCandidate> GetCandidates(List<Dictionary<string, object?>> results)
    {
        if (results.Count == 0)
            return new List<CustomerCandidate>();

        string? surnameKey = results
            .SelectMany(r => r.Keys)
            .FirstOrDefault(k => k.Equals("Surname", StringComparison.OrdinalIgnoreCase));

        if (surnameKey == null)
            return new List<CustomerCandidate>();

        string? customerIdKey = results
            .SelectMany(r => r.Keys)
            .FirstOrDefault(k => k.Equals("CustomerId", StringComparison.OrdinalIgnoreCase));

        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var candidates = new List<CustomerCandidate>();

        foreach (var row in results)
        {
            string? surname = row[surnameKey]?.ToString();
            if (string.IsNullOrWhiteSpace(surname))
                continue;

            object? customerId = customerIdKey != null && row.TryGetValue(customerIdKey, out var id)
                ? id
                : null;

            string dedupeKey = customerId?.ToString() ?? surname;
            if (!seen.Add(dedupeKey))
                continue;

            candidates.Add(new CustomerCandidate(customerId, surname));
        }

        return candidates
            .OrderBy(c => c.Surname, StringComparer.OrdinalIgnoreCase)
            .ThenBy(c => c.CustomerId?.ToString(), StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    public static bool ShouldConfirm(
        List<CustomerCandidate> candidates,
        string question,
        string? confirmedCustomerId)
    {
        if (!string.IsNullOrWhiteSpace(confirmedCustomerId))
            return false;

        if (candidates.Count <= 1)
            return false;

        if (IsComparisonQuestion(question))
            return false;

        return true;
    }
}
