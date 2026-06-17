CREATE TABLE Customers (
    RowNumber INT,
    CustomerId BIGINT PRIMARY KEY,
    Surname VARCHAR(100),
    CreditScore INT,
    Geography VARCHAR(50),
    Gender VARCHAR(20),
    Age INT,
    Tenure INT,
    Balance DECIMAL(18,2),
    NumOfProducts INT,
    HasCrCard BIT,
    IsActiveMember BIT,
    EstimatedSalary DECIMAL(18,2),
    Exited BIT
);
