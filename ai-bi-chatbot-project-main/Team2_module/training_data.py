# nlp/training_data.py
#
# Phase 2 - Step 1: Training dataset
#
# 160 labelled query examples across 5 intents.
# Column names are aligned to Team 1 (Data Engineering) master_dataset.csv
# after standardize_columns() is applied in data_cleaning.py.
#
# Confirmed columns from eda_analysis.py:
#   sales, month_id, qtr_id, year_id, productline,
#   country, dealsize, customername, territory, status
#
# Engineered columns from feature_engineering.py:
#   month, quarter, year, revenue, profit

training_data = [

    # -- Sales query ----------------------------------------------------------
    # Queries asking for revenue or sales figures.
    # Maps to: df["sales"] or df["revenue"]
    # Grouped by: month_id, qtr_id, year_id, month, quarter, year

    ("Show last month revenue",                           "sales_query"),
    ("What is total sales?",                              "sales_query"),
    ("How much did we earn last year?",                   "sales_query"),
    ("Give me revenue for 2003",                          "sales_query"),
    ("What were sales in month 1?",                       "sales_query"),
    ("Show last month sales figures",                     "sales_query"),
    ("Total sales in qtr_id 3",                           "sales_query"),
    ("How much was sold in month 11?",                    "sales_query"),
    ("What is the monthly revenue?",                      "sales_query"),
    ("Sales for the last quarter",                        "sales_query"),
    ("Revenue in year_id 2004",                           "sales_query"),
    ("Show sales for quarter 1",                          "sales_query"),
    ("Give me yearly revenue",                            "sales_query"),
    ("What are total earnings this year?",                "sales_query"),
    ("How did we perform in Q3?",                         "sales_query"),
    ("Show me this quarter sales",                        "sales_query"),
    ("What was revenue in month 10?",                     "sales_query"),
    ("Monthly sales breakdown",                           "sales_query"),
    ("Show annual revenue figures",                       "sales_query"),
    ("Revenue from Classic Cars product line",            "sales_query"),
    ("How much did USA contribute to sales?",             "sales_query"),
    ("Sales from EMEA territory",                         "sales_query"),
    ("What is total revenue from large deals?",           "sales_query"),
    ("Show profit for this quarter",                      "sales_query"),
    ("What is the total profit?",                         "sales_query"),
    ("Revenue breakdown by month_id",                     "sales_query"),
    ("Show me sales in 2004",                             "sales_query"),
    ("Total revenue in qtr_id 4",                         "sales_query"),
    ("What were earnings in year_id 2003?",               "sales_query"),
    ("How much profit did we make?",                      "sales_query"),

    # -- Ranking query --------------------------------------------------------
    # Queries asking for top or bottom ranked results.
    # Maps to: groupby + sort_values + head()
    # Grouped by: productline, country, customername, dealsize, territory

    ("Top 5 products by revenue",                         "ranking_query"),
    ("Which productline sells the most?",                 "ranking_query"),
    ("Best performing country",                           "ranking_query"),
    ("Show top 10 customers by sales",                    "ranking_query"),
    ("Which dealsize brings most revenue?",               "ranking_query"),
    ("Rank productline by sales",                         "ranking_query"),
    ("Top customers this year",                           "ranking_query"),
    ("Which territory performs best?",                    "ranking_query"),
    ("Best selling product line",                         "ranking_query"),
    ("Most profitable country",                           "ranking_query"),
    ("Bottom 3 performing regions",                       "ranking_query"),
    ("Lowest sales by productline",                       "ranking_query"),
    ("Top 5 countries by revenue",                        "ranking_query"),
    ("Which customername bought the most?",               "ranking_query"),
    ("Rank territories by performance",                   "ranking_query"),
    ("Show me the top 3 product lines",                   "ranking_query"),
    ("Who are our top 10 customers?",                     "ranking_query"),
    ("Top productline by number of orders",               "ranking_query"),
    ("Which country has the highest sales?",              "ranking_query"),
    ("Best customer by total spend",                      "ranking_query"),
    ("Top dealsize by profit",                            "ranking_query"),
    ("Which city orders the most?",                       "ranking_query"),
    ("Worst performing productline",                      "ranking_query"),
    ("Top 5 customername by revenue",                     "ranking_query"),
    ("Which country contributes most to sales?",          "ranking_query"),
    ("Show highest revenue territory",                    "ranking_query"),
    ("Best performing dealsize category",                 "ranking_query"),
    ("Top 10 orders by sales value",                      "ranking_query"),
    ("Which productline has highest profit?",             "ranking_query"),
    ("Rank countries by total sales",                     "ranking_query"),
    ("Top 5 productline by sales",                        "ranking_query"),
    ("Top 3 productline by revenue",                      "ranking_query"),
    ("Which dealsize generates most revenue?",            "ranking_query"),
    ("Which dealsize has the highest sales?",             "ranking_query"),
    ("Which country generates most profit?",              "ranking_query"),
    ("Which productline generates highest revenue?",      "ranking_query"),

    # -- Comparison query -----------------------------------------------------
    # Queries comparing two values, periods, or categories.
    # Maps to: groupby + side-by-side aggregation
    # Compares: year_id, qtr_id, month_id, productline, country, dealsize, territory

    ("Compare 2003 vs 2004 sales",                        "comparison_query"),
    ("How does qtr_id 1 compare to qtr_id 2?",            "comparison_query"),
    ("Difference between USA and France revenue",         "comparison_query"),
    ("Classic Cars vs Motorcycles sales",                 "comparison_query"),
    ("Compare small vs large dealsize",                   "comparison_query"),
    ("How did EMEA compare to NA territory?",             "comparison_query"),
    ("Year over year revenue comparison",                 "comparison_query"),
    ("Sales this year vs last year",                      "comparison_query"),
    ("Compare revenue across productline",                "comparison_query"),
    ("qtr_id 3 vs qtr_id 4 performance",                  "comparison_query"),
    ("How does Europe compare to America?",               "comparison_query"),
    ("Medium vs large dealsize revenue",                  "comparison_query"),
    ("Month on month growth comparison",                  "comparison_query"),
    ("Compare year_id 2003 and year_id 2004",             "comparison_query"),
    ("Shipped vs cancelled order count",                  "comparison_query"),
    ("Revenue difference between quarter 2 and 3",       "comparison_query"),
    ("Compare Trains versus Ships sales",                 "comparison_query"),
    ("How does month 1 compare to month 12?",             "comparison_query"),
    ("Side by side comparison of territories",            "comparison_query"),
    ("Vintage Cars vs Classic Cars revenue",              "comparison_query"),
    ("NA versus EMEA territory sales",                    "comparison_query"),
    ("2003 revenue against 2004 revenue",                 "comparison_query"),
    ("Compare this quarter to previous quarter",          "comparison_query"),
    ("Profit comparison across productline",              "comparison_query"),
    ("Compare dealsize performance by country",           "comparison_query"),
    ("How did APAC compare to Japan territory?",          "comparison_query"),
    ("Sales comparison between month_id 6 and 12",        "comparison_query"),
    ("Contrast revenue in different territories",         "comparison_query"),
    ("Classic Cars versus Motorcycles revenue",           "comparison_query"),
    ("Trucks versus Ships sales comparison",              "comparison_query"),
    ("France versus Germany revenue",                     "comparison_query"),
    ("Small versus large dealsize profit",                "comparison_query"),
    ("Compare customer spending across years",            "comparison_query"),
    ("Revenue difference small vs medium dealsize",       "comparison_query"),

    # -- Forecast query -------------------------------------------------------
    # Queries asking for predictions or future projections.
    # Maps to: ARIMA or Linear Regression on sales or revenue column

    ("Predict next month sales",                          "forecast_query"),
    ("Forecast revenue for qtr_id 4",                     "forecast_query"),
    ("What will sales look like next year?",              "forecast_query"),
    ("Project revenue for next quarter",                  "forecast_query"),
    ("Estimate sales for month 12",                       "forecast_query"),
    ("What is the sales trend going forward?",            "forecast_query"),
    ("Predict annual revenue",                            "forecast_query"),
    ("Sales forecast for 2005",                           "forecast_query"),
    ("What is the growth trend?",                         "forecast_query"),
    ("Forecast next month performance",                   "forecast_query"),
    ("Will sales increase next quarter?",                 "forecast_query"),
    ("Revenue prediction for next year",                  "forecast_query"),
    ("Predict qtr_id 1 sales",                            "forecast_query"),
    ("Show expected sales trend",                         "forecast_query"),
    ("What does the sales trajectory look like?",         "forecast_query"),
    ("What will revenue be next year?",                   "forecast_query"),
    ("Estimate future revenue",                           "forecast_query"),
    ("Predict what sales will look like",                 "forecast_query"),
    ("Expected revenue next quarter",                     "forecast_query"),
    ("Forecast future performance",                       "forecast_query"),
    ("What are projected earnings for 2005?",             "forecast_query"),
    ("Revenue outlook for next year",                     "forecast_query"),
    ("Predict month 12 sales figures",                    "forecast_query"),
    ("What is the predicted growth rate?",                "forecast_query"),
    ("Sales projection for next 3 months",                "forecast_query"),
    ("Forecast profit for next quarter",                  "forecast_query"),
    ("What will Classic Cars revenue be next year?",      "forecast_query"),
    ("Predict revenue trend by productline",              "forecast_query"),
    ("Expected sales for EMEA territory next quarter",    "forecast_query"),
    ("Project USA sales for next year",                   "forecast_query"),

    # -- HR query -------------------------------------------------------------
    # Queries about employee data.
    # Note: HR data is only available if employee_id exists after the merge
    # in data_merging.py. The analytics engine should handle missing HR data.

    ("What is the attrition rate?",                       "hr_query"),
    ("Show employee turnover",                            "hr_query"),
    ("How many employees left last quarter?",             "hr_query"),
    ("Department with highest attrition",                 "hr_query"),
    ("Average salary by department",                      "hr_query"),
    ("Which department has the most employees?",          "hr_query"),
    ("Show workforce breakdown",                          "hr_query"),
    ("What is the employee retention rate?",              "hr_query"),
    ("How many staff were hired this year?",              "hr_query"),
    ("Gender distribution across departments",            "hr_query"),
    ("What is the average employee age?",                 "hr_query"),
    ("Show salary comparison by department",              "hr_query"),
    ("Which role has the highest turnover?",              "hr_query"),
    ("How many employees are in sales department?",       "hr_query"),
    ("Employee count by job level",                       "hr_query"),
    ("What is the HR attrition percentage?",              "hr_query"),
    ("Show monthly attrition trend",                      "hr_query"),
    ("Which department pays the most?",                   "hr_query"),
    ("How many employees left this year?",                "hr_query"),
    ("Attrition rate by age group",                       "hr_query"),
    ("Show performance rating distribution",              "hr_query"),
    ("What is total headcount?",                          "hr_query"),
    ("How satisfied are employees?",                      "hr_query"),
    ("Show work life balance scores",                     "hr_query"),
    ("Which department has lowest satisfaction?",         "hr_query"),
    ("What is the average years at company?",             "hr_query"),
    ("How many employees got promoted?",                  "hr_query"),
    ("Show overtime distribution by department",          "hr_query"),
    ("Which job role has best performance rating?",       "hr_query"),
    ("What percent of employees work overtime?",          "hr_query"),
]