using System.Text.RegularExpressions;

public static class SqlSafety
{
    private static readonly string[] BlockedKeywords =
    {
        "INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER",
        "CREATE", "EXEC", "EXECUTE", "MERGE", "GRANT", "REVOKE"
    };

    public static bool TryValidateSelectQuery(string sql, out string error)
    {
        error = "";

        if (string.IsNullOrWhiteSpace(sql))
        {
            error = "Query is empty.";
            return false;
        }

        sql = StripComments(sql.Trim().TrimEnd(';'));

        if (sql.Contains(';'))
        {
            error = "Multiple SQL statements are not allowed.";
            return false;
        }

        foreach (var keyword in BlockedKeywords)
        {
            if (Regex.IsMatch(sql, $@"\b{keyword}\b", RegexOptions.IgnoreCase))
            {
                error = $"Blocked keyword detected: {keyword}.";
                return false;
            }
        }

        if (Regex.IsMatch(sql, @"\bSELECT\b.+\bINTO\b", RegexOptions.IgnoreCase))
        {
            error = "SELECT INTO is not allowed.";
            return false;
        }

        if (StartsWithSelect(sql))
            return true;

        if (StartsWithWithClause(sql))
        {
            if (!Regex.IsMatch(sql, @"\bSELECT\b", RegexOptions.IgnoreCase))
            {
                error = "Common table expressions must include a SELECT.";
                return false;
            }

            return true;
        }

        error = "Only read-only SELECT queries are allowed.";
        return false;
    }

    private static bool StartsWithSelect(string sql) =>
        sql.StartsWith("SELECT", StringComparison.OrdinalIgnoreCase);

    private static bool StartsWithWithClause(string sql) =>
        sql.StartsWith("WITH", StringComparison.OrdinalIgnoreCase);

    private static string StripComments(string sql)
    {
        sql = Regex.Replace(sql, @"--[^\r\n]*", "");
        sql = Regex.Replace(sql, @"/\*.*?\*/", "", RegexOptions.Singleline);
        return sql.Trim();
    }

    public static string CleanSql(string sql, string actualTableName = "Customers")
    {
        if (string.IsNullOrWhiteSpace(sql)) return "NA";

        sql = sql
            .Replace("```json", "", StringComparison.OrdinalIgnoreCase)
            .Replace("```sql", "", StringComparison.OrdinalIgnoreCase)
            .Replace("```", "")
            .Trim()
            .TrimEnd(';');

        return FixSurnamePrefixMatch(FixCustomersSchema(sql, actualTableName));
    }

    public static string FixSurnamePrefixMatch(string sql)
    {
        sql = Regex.Replace(
            sql,
            @"(\bSurname\b)\s+LIKE\s+(['""])%([^'""%]+)%\2",
            "$1 LIKE $2$3%$2",
            RegexOptions.IgnoreCase);

        sql = Regex.Replace(
            sql,
            @"(\bSurname\b)\s+LIKE\s+(['""])%([^'""%]+)\2",
            "$1 LIKE $2$3%$2",
            RegexOptions.IgnoreCase);

        return sql;
    }

    public static string FixCustomersSchema(string sql, string actualTableName)
    {
        if (string.IsNullOrWhiteSpace(actualTableName))
            actualTableName = "Customers";

        sql = Regex.Replace(
            sql,
            @"(`?)(?:bank_data\.)?customers(`?)",
            $"$1{actualTableName}$2",
            RegexOptions.IgnoreCase);

        (string pattern, string replacement)[] columns =
        {
            ("customerid", "CustomerId"),
            ("surname", "Surname"),
            ("creditscore", "CreditScore"),
            ("geography", "Geography"),
            ("gender", "Gender"),
            ("age", "Age"),
            ("tenure", "Tenure"),
            ("balance", "Balance"),
            ("numofproducts", "NumOfProducts"),
            ("hascrcard", "HasCrCard"),
            ("isactivemember", "IsActiveMember"),
            ("estimatedsalary", "EstimatedSalary"),
            ("exited", "Exited"),
            ("rownumber", "RowNumber")
        };

        foreach (var (pattern, replacement) in columns)
        {
            sql = Regex.Replace(
                sql,
                $@"\b{pattern}\b",
                replacement,
                RegexOptions.IgnoreCase);
        }

        return sql;
    }
}
