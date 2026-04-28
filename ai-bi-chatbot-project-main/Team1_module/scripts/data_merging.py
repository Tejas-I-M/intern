def merge_datasets(sales, finance, hr):

    master = sales.copy()

    # Merge finance if date exists
    if 'date' in sales.columns and 'date' in finance.columns:
        master = master.merge(finance, on='date', how='left')

    # Merge HR if employee_id exists
    if 'employee_id' in sales.columns and 'employee_id' in hr.columns:
        master = master.merge(hr, on='employee_id', how='left')

    return master