public static class ChartRecommender
{
    private static readonly HashSet<string> IdColumns = new(StringComparer.OrdinalIgnoreCase)
    {
        "CustomerId", "RowNumber", "Id"
    };

    private static readonly HashSet<string> CategoryColumns = new(StringComparer.OrdinalIgnoreCase)
    {
        "Geography", "Gender", "Surname"
    };

    public static string Recommend(
        List<Dictionary<string, object?>> data,
        string? llmChartType,
        string question)
    {
        if (!ChartRequestDetector.WantsChart(question))
            return "table";

        if (data.Count == 0)
            return "table";

        var first = data[0];
        var numericCols = GetNumericColumns(first);
        var labelCol = FindLabelColumn(first);

        if (data.Count == 1)
        {
            if (numericCols.Count >= 2 && labelCol == null)
                return PreferPieForParts(numericCols) ? "pie" : "bar";

            return "table";
        }

        if (labelCol != null && numericCols.Count > 0)
        {
            if (data.Count <= 6 && CategoryColumns.Contains(labelCol))
                return "pie";

            if (data.Count <= 25)
                return "bar";
        }

        if (IsValidChartType(llmChartType))
            return llmChartType!;

        if (data.Count >= 2 && numericCols.Count > 0)
            return "bar";

        return "table";
    }

    private static bool PreferPieForParts(List<string> numericCols)
    {
        if (numericCols.Count > 6)
            return false;

        return numericCols.Any(c =>
            c.Contains("count", StringComparison.OrdinalIgnoreCase) ||
            c.Contains("male", StringComparison.OrdinalIgnoreCase) ||
            c.Contains("female", StringComparison.OrdinalIgnoreCase) ||
            c.Contains("total", StringComparison.OrdinalIgnoreCase));
    }

    private static bool IsValidChartType(string? chartType) =>
        chartType is "bar" or "line" or "pie" or "table";

    private static List<string> GetNumericColumns(Dictionary<string, object?> row)
    {
        return row
            .Where(kv => !IdColumns.Contains(kv.Key) && IsNumeric(kv.Value))
            .Select(kv => kv.Key)
            .ToList();
    }

    private static string? FindLabelColumn(Dictionary<string, object?> row)
    {
        foreach (string col in row.Keys)
        {
            if (CategoryColumns.Contains(col))
                return col;
        }

        return row.Keys.FirstOrDefault(c =>
            !IdColumns.Contains(c) && row[c] is string);
    }

    private static bool IsNumeric(object? value)
    {
        if (value == null) return false;
        if (value is byte or sbyte or short or ushort or int or uint or long or ulong
            or float or double or decimal)
            return true;

        return decimal.TryParse(value.ToString(), out _);
    }
}
