using System.Text.RegularExpressions;

public static class ChartRequestDetector
{
    private static readonly Regex ChartPattern = new(
        @"\b(graph|graphs|chart|charts|plot|plots|visual|visuali[sz]e|diagram|" +
        @"pie\s*chart|bar\s*chart|line\s*chart|show\s+me\s+a\s+(graph|chart|plot))\b",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    public static bool WantsChart(string question) =>
        !string.IsNullOrWhiteSpace(question) && ChartPattern.IsMatch(question);
}
