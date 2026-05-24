/* =====================================================================
   DỰ ÁN: CUSTOMER CHURN PREDICTION DATA WAREHOUSE
   Hệ quản trị CSDL: Microsoft SQL Server
   Mục tiêu: Thiết lập hạ tầng lưu trữ, xử lý ETL và Feature Engineering
   ===================================================================== */

USE ChurnDW;
GO

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

-- =====================================================================
-- KHIÁ CẠNH 1: KHỞI TẠO KHÔNG GIAN TÊN (SCHEMAS)
-- =====================================================================
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'stg') EXEC('CREATE SCHEMA stg');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'dw') EXEC('CREATE SCHEMA dw');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'cfg') EXEC('CREATE SCHEMA cfg');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'audit') EXEC('CREATE SCHEMA audit');
GO

PRINT N'Phân vùng Schema (stg, dw, cfg, audit) đã sẵn sàng.';
GO

-- =====================================================================
-- KHÍA CẠNH 2: KHỞI TẠO CẤU TRÚC BẢNG VẬT LÝ (STAR SCHEMA)
-- =====================================================================

-- 1. Bảng chiều Sản phẩm (DimProduct)
IF OBJECT_ID('dw.DimProduct', 'U') IS NULL
BEGIN
    CREATE TABLE dw.DimProduct (
        ProductKey INT IDENTITY(1,1) PRIMARY KEY,
        ProductLine NVARCHAR(100) NOT NULL
    );
    PRINT N'  -> Khởi tạo bảng dw.DimProduct thành công.';
END;
GO

-- 2. Bảng chiều Khách hàng (DimCustomer)
IF OBJECT_ID('dw.DimCustomer', 'U') IS NULL
BEGIN
    CREATE TABLE dw.DimCustomer (
        CustomerKey INT IDENTITY(1,1) PRIMARY KEY,
        LoyaltyNumber BIGINT NOT NULL,
        CustomerName NVARCHAR(200),
        Country NVARCHAR(100),
        Gender NVARCHAR(20),
        Education NVARCHAR(100),
        Income DECIMAL(18,2),
        MaritalStatus NVARCHAR(50),
        LoyaltyStatus NVARCHAR(50),
        MonthsAsMember INT,
        CLV DECIMAL(18,2),
        IsActive BIT DEFAULT 1
    );
    PRINT N'  -> Khởi tạo bảng dw.DimCustomer thành công.';
END;
GO

-- 3. Bảng sự kiện trung tâm (FactSales)
IF OBJECT_ID('dw.FactSales', 'U') IS NULL
BEGIN
    CREATE TABLE dw.FactSales (
        SalesKey BIGINT IDENTITY(1,1) PRIMARY KEY,
        CustomerKey INT FOREIGN KEY REFERENCES dw.DimCustomer(CustomerKey),
        ProductKey INT FOREIGN KEY REFERENCES dw.DimProduct(ProductKey),
        OrderYear INT,
        Quarter NVARCHAR(10),
        QuantitySold INT,
        Revenue DECIMAL(18,2),
        Profit DECIMAL(18,2)
    );
    PRINT N'  -> Khởi tạo bảng dw.FactSales thành công.';
END;
GO

-- 4. Bảng Feature Store phục vụ Học Máy (CustomerSnapshot)
IF OBJECT_ID('dw.CustomerSnapshot', 'U') IS NULL
BEGIN
    CREATE TABLE dw.CustomerSnapshot (
        CustomerKey INT PRIMARY KEY,
        LoyaltyNumber BIGINT,
        Gender NVARCHAR(20),
        Education NVARCHAR(100),
        Income DECIMAL(18,2),
        LoyaltyStatus NVARCHAR(50),
        MonthsAsMember INT,
        Frequency INT,
        TotalRevenue DECIMAL(18,2),
        AvgProfit DECIMAL(18,2),
        TotalQuantity INT,
        LastOrderYear INT,
        RecencyYears INT,
        IsChurn INT
    );
    PRINT N'  -> Khởi tạo bảng Feature Store dw.CustomerSnapshot thành công.';
END;
GO

-- 5. Bảng đệm staging nhận điểm rủi ro từ Python đẩy về (Reverse ETL)
IF OBJECT_ID('stg.ChurnScoreRaw', 'U') IS NULL
BEGIN
    CREATE TABLE stg.ChurnScoreRaw (
        LoadBatchId UNIQUEIDENTIFIER,
        SnapshotDate DATE,
        CustomerName NVARCHAR(200),
        ModelName NVARCHAR(100),
        ModelVersion NVARCHAR(50),
        ChurnProb FLOAT,
        RiskScore FLOAT,
        SourceFileName NVARCHAR(250)
    );
    PRINT N'  -> Khởi tạo bảng đệm nhận kết quả stg.ChurnScoreRaw thành công.';
END;
GO

-- 6. Bảng kho lưu vết vĩnh viễn lịch sử Churn Score phục vụ báo cáo xu hướng
IF OBJECT_ID('dw.FactChurnScore', 'U') IS NULL
BEGIN
    CREATE TABLE dw.FactChurnScore (
        ScoreKey BIGINT IDENTITY(1,1) PRIMARY KEY,
        CustomerKey INT FOREIGN KEY REFERENCES dw.DimCustomer(CustomerKey),
        SnapshotDate DATE NOT NULL,
        ModelName NVARCHAR(100),
        ModelVersion NVARCHAR(50),
        ChurnProbability DECIMAL(5,4),
        RiskScore DECIMAL(5,2),
        RiskTier NVARCHAR(50),
        ActionPlan NVARCHAR(200),
        UpdatedAt DATETIME DEFAULT GETDATE()
    );
    PRINT N'  -> Khởi tạo bảng kho lịch sử dự báo dw.FactChurnScore thành công.';
END;
GO


-- =====================================================================
-- KHÍA CẠNH 3: XÂY DỰNG CÁC THỦ TỤC ĐIỀU PHỐI (STORED PROCEDURES)
-- =====================================================================

-- 🌟 THỦ TỤC 1: ETL dịch chuyển dữ liệu thô từ Excel sang Star Schema
CREATE OR ALTER PROCEDURE dw.sp_ETL_LoadDataWarehouse
AS
BEGIN
    SET NOCOUNT ON;

    PRINT N'Bắt đầu tiến trình phân tách dữ liệu sang Star Schema...';

    -- 1. Nạp danh mục Sản phẩm độc nhất vào bảng DimProduct
    INSERT INTO dw.DimProduct (ProductLine)
    SELECT DISTINCT Product_Line 
    FROM stg.CleanDataRaw
    WHERE Product_Line IS NOT NULL 
      AND Product_Line NOT IN (SELECT ProductLine FROM dw.DimProduct);

    -- 2. Nạp thông tin Khách hàng độc nhất vào bảng DimCustomer (Chống trùng lặp LoyaltyNumber)
    INSERT INTO dw.DimCustomer (LoyaltyNumber, CustomerName, Country, Gender, Education, Income, MaritalStatus, LoyaltyStatus, MonthsAsMember, CLV)
    SELECT DISTINCT 
        LoyaltyNumber, 
        Customer_Name, 
        Country, 
        Gender, 
        Education, 
        Income, 
        Marital_Status, 
        LoyaltyStatus, 
        MonthsAsMember, 
        Customer_Lifetime_Value
    FROM stg.CleanDataRaw src
    WHERE src.LoyaltyNumber NOT IN (SELECT LoyaltyNumber FROM dw.DimCustomer);

    -- 3. Làm sạch dữ liệu cũ và nạp mới toàn bộ giao dịch vào bảng trung tâm FactSales
    TRUNCATE TABLE dw.FactSales; 

    INSERT INTO dw.FactSales (CustomerKey, ProductKey, OrderYear, Quarter, QuantitySold, Revenue, Profit)
    SELECT 
        dc.CustomerKey,
        dp.ProductKey,
        stg.Order_Year,
        stg.Quarter,
        stg.Quantity_Sold,
        stg.Revenue,
        stg.Profit
    FROM stg.CleanDataRaw stg
    JOIN dw.DimCustomer dc ON stg.LoyaltyNumber = dc.LoyaltyNumber
    JOIN dw.DimProduct dp ON stg.Product_Line = dp.ProductLine;

    PRINT N' TIẾN TRÌNH HOÀN TẤT: Dữ liệu từ file Excel đã được cấu trúc lại trong Star Schema!';
END;
GO


-- 🌟 THỦ TỤC 2: Feature Engineering - Tính toán biến đặc trưng AI và nhãn mục tiêu IsChurn
CREATE OR ALTER PROCEDURE dw.sp_FE_BuildCustomerSnapshot
AS
BEGIN
    SET NOCOUNT ON;

    PRINT N'Bắt đầu trích xuất biến đặc trưng (Feature Engineering) cho AI...';

    -- Làm sạch bảng Feature Store cũ trước khi cập nhật
    TRUNCATE TABLE dw.CustomerSnapshot;

    -- Tính toán Feature Store tích hợp định nghĩa nhãn Churn (Target Variable)
    INSERT INTO dw.CustomerSnapshot
    SELECT 
        dc.CustomerKey,
        dc.LoyaltyNumber,
        dc.Gender,
        dc.Education,
        dc.Income,
        dc.LoyaltyStatus,
        dc.MonthsAsMember,
        ISNULL(COUNT(fs.SalesKey), 0) AS Frequency,
        ISNULL(SUM(fs.Revenue), 0) AS TotalRevenue,
        ISNULL(AVG(fs.Profit), 0) AS AvgProfit,
        ISNULL(SUM(fs.QuantitySold), 0) AS TotalQuantity,
        ISNULL(MAX(fs.OrderYear), 2014) AS LastOrderYear,
        (2018 - ISNULL(MAX(fs.OrderYear), 2014)) AS RecencyYears,
        -- Định nghĩa luật gán nhãn mục tiêu Churn phục vụ huấn luyện máy học
        CASE WHEN ISNULL(MAX(fs.OrderYear), 2014) < 2017 THEN 1 ELSE 0 END AS IsChurn
    FROM dw.DimCustomer dc
    LEFT JOIN dw.FactSales fs ON dc.CustomerKey = fs.CustomerKey
    GROUP BY dc.CustomerKey, dc.LoyaltyNumber, dc.Gender, dc.Education, dc.Income, dc.LoyaltyStatus, dc.MonthsAsMember;

    PRINT N' HOÀN TẤT: Bảng dữ liệu dw.CustomerSnapshot đã sẵn sàng cho Machine Learning!';
END;
GO


-- 🌟 THỦ TỤC 3: Reverse ETL - Đồng bộ kết quả chấm điểm từ Python và áp Business Rules phân hạng rủi ro
CREATE OR ALTER PROCEDURE dw.sp_Score_LoadFromStaging
    @SnapshotDate DATE,
    @ModelName NVARCHAR(100),
    @ModelVersion NVARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;

    PRINT N' Bắt đầu đồng bộ kết quả dự báo AI vào hệ thống Data Warehouse...';

    -- Loại bỏ dữ liệu cũ của cùng kỳ chấm điểm đó (Idempotent Design)
    DELETE FROM dw.FactChurnScore 
    WHERE SnapshotDate = @SnapshotDate AND ModelName = @ModelName;

    -- Nạp dữ liệu chính thức kết hợp phân loại Business Rules trực tiếp bằng SQL
    INSERT INTO dw.FactChurnScore (CustomerKey, SnapshotDate, ModelName, ModelVersion, ChurnProbability, RiskScore, RiskTier, ActionPlan)
    SELECT 
        dc.CustomerKey,
        stg.SnapshotDate,
        stg.ModelName,
        stg.ModelVersion,
        CAST(stg.ChurnProb AS DECIMAL(5,4)),
        CAST(stg.RiskScore AS DECIMAL(5,2)),
        -- Phân hạng mức độ nguy cơ dựa trên ngưỡng xác suất rời dịch vụ
        CASE 
            WHEN stg.ChurnProb >= 0.70 THEN N'Nguy cơ Cao (High)'
            WHEN stg.ChurnProb >= 0.40 THEN N'Nguy cơ Trung bình (Medium)'
            ELSE N'An toàn (Low)'
        END AS RiskTier,
        -- Đưa ra kịch bản hành động cụ thể cho đội ngũ vận hành
        CASE 
            WHEN stg.ChurnProb >= 0.70 THEN N'Liên hệ trực tiếp + Tặng Coupon đặc biệt'
            WHEN stg.ChurnProb >= 0.40 THEN N'Gửi email khảo sát trải nghiệm + Ưu đãi ngành hàng quan tâm'
            ELSE N'Duy trì chăm sóc tiêu chuẩn'
        END AS ActionPlan
    FROM stg.ChurnScoreRaw stg
    JOIN dw.DimCustomer dc ON stg.CustomerName = dc.CustomerName
    WHERE stg.SnapshotDate = @SnapshotDate;

    PRINT N' Đã đồng bộ và áp đặt Business Rules thành công cho kỳ báo cáo: ' + CAST(@SnapshotDate AS VARCHAR(10));
END;
GO

PRINT '========================================================================';
PRINT N'HỆ THỐNG HOÀN CHỈNH: Toàn bộ cấu trúc DW hiện tại đã được thiết lập!';
PRINT '========================================================================';
GO

EXEC dw.sp_ETL_LoadDataWarehouse;     -- Bước 1: Đổ dữ liệu vào Star Schema
EXEC dw.sp_FE_BuildCustomerSnapshot;   -- Bước 2: Tạo Feature Store cho AI đọc
