-- ============================================================================
-- arcline historian example MS-SQL schema
-- ============================================================================
--
-- Documents the warehouse layout the built-in HistorySpec catalog targets.
-- Runnable on SQL Server 2019+ and Azure SQL (including LocalDB) so users
-- without enterprise SQL Server can exercise /dashboard/history end-to-end.
--
-- After running this script, set:
--   ARCLINE_MSSQL_DSN="mssql+pyodbc://user:pwd@host/arcline?driver=ODBC+Driver+18+for+SQL+Server"
-- and run:
--   arcline history sync ./your_project --since 2024-01-01
--
-- ----------------------------------------------------------------------------

IF SCHEMA_ID(N'dwh') IS NULL EXEC(N'CREATE SCHEMA dwh');
GO

-- Lane lead time (Lane.transitDays) ------------------------------------------
IF OBJECT_ID(N'dwh.fact_lane_lead_time', N'U') IS NOT NULL
    DROP TABLE dwh.fact_lane_lead_time;
GO
CREATE TABLE dwh.fact_lane_lead_time (
    edge_hash_key          NVARCHAR(64)  NOT NULL,
    shipment_date          DATE          NOT NULL,
    actual_lead_time_days  FLOAT         NOT NULL,
    is_active              BIT           NOT NULL DEFAULT 1,
    CONSTRAINT pk_fact_lane_lead_time PRIMARY KEY (edge_hash_key, shipment_date)
);
GO

-- Lane unit cost (Lane.costPerUnit) ------------------------------------------
IF OBJECT_ID(N'dwh.fact_lane_cost', N'U') IS NOT NULL
    DROP TABLE dwh.fact_lane_cost;
GO
CREATE TABLE dwh.fact_lane_cost (
    edge_hash_key          NVARCHAR(64)  NOT NULL,
    invoice_date           DATE          NOT NULL,
    unit_cost              FLOAT         NOT NULL,
    CONSTRAINT pk_fact_lane_cost PRIMARY KEY (edge_hash_key, invoice_date)
);
GO

-- Plant throughput (Plant.productionRatePerHr) -------------------------------
IF OBJECT_ID(N'dwh.fact_plant_throughput', N'U') IS NOT NULL
    DROP TABLE dwh.fact_plant_throughput;
GO
CREATE TABLE dwh.fact_plant_throughput (
    node_hash_key          NVARCHAR(64)  NOT NULL,
    production_date        DATE          NOT NULL,
    units_per_hour         FLOAT         NOT NULL,
    CONSTRAINT pk_fact_plant_throughput PRIMARY KEY (node_hash_key, production_date)
);
GO

-- Warehouse throughput (Warehouse.maxCapacity) -------------------------------
IF OBJECT_ID(N'dwh.fact_warehouse_throughput', N'U') IS NOT NULL
    DROP TABLE dwh.fact_warehouse_throughput;
GO
CREATE TABLE dwh.fact_warehouse_throughput (
    node_hash_key          NVARCHAR(64)  NOT NULL,
    activity_date          DATE          NOT NULL,
    units_handled          FLOAT         NOT NULL,
    CONSTRAINT pk_fact_warehouse_throughput PRIMARY KEY (node_hash_key, activity_date)
);
GO

-- Customer demand (Customer.demandMean) --------------------------------------
IF OBJECT_ID(N'dwh.fact_customer_demand', N'U') IS NOT NULL
    DROP TABLE dwh.fact_customer_demand;
GO
CREATE TABLE dwh.fact_customer_demand (
    node_hash_key          NVARCHAR(64)  NOT NULL,
    order_date             DATE          NOT NULL,
    units_ordered          FLOAT         NOT NULL,
    CONSTRAINT pk_fact_customer_demand PRIMARY KEY (node_hash_key, order_date)
);
GO
