import streamlit as st
import pandas as pd
from presentation.display_file import display_file
from io import BytesIO

st.title('Terralabor File Transformer')

file = st.file_uploader('Please Select the File To Transform', type=['xlsx', 'xls'])

if file:
    pd_file = display_file(file)

    # Ensure column 0 is string if datetime
    if pd.api.types.is_datetime64_any_dtype(pd_file.iloc[:, 0]):
        pd_file.iloc[:, 0] = pd_file.iloc[:, 0].astype(str)

    # Forward fill the first column
    pd_file.iloc[:, 0] = pd_file.iloc[:, 0].ffill()

    # Drop rows where column index 3 is null
    pd_file = pd_file.drop(pd_file.index[(pd_file.index >= 0) & (pd_file.iloc[:, 3].isnull())])

    # Forward fill row 4 horizontally
    pd_file.loc[4] = pd_file.loc[4].ffill(axis=0)

    # Drop specified columns
    columns_to_drop = [1, 2, 4, 5, 6, 7, 8, 9, 10, 12, 13, 15, 17, 19, 21, 23, 24, 26, 28, 30]
    pd_file = pd_file.drop(columns=pd_file.columns[columns_to_drop])

    # Drop rows with null in column index 2
    pd_file = pd_file.dropna(subset=[pd_file.columns[2]])

    # Set the first row as header
    pd_file.columns = pd_file.iloc[0].astype(str).str.strip()
    pd_file = pd_file[1:]

    # Convert entire DataFrame to strings
    pd_file = pd_file.astype(str)

    # Convert column names and index to strings
    pd_file.columns = pd_file.columns.map(str)
    pd_file.index = pd_file.index.map(str)

    # Ensure we have a clean DataFrame
    pd_file = pd_file.reset_index(drop=True)
    pd_file.columns = [str(col) for col in pd_file.columns]
    pd_file = pd_file.convert_dtypes().astype(str)

    # Calculate totals for ST and Totals
    if "ST" in pd_file.columns:
        pd_file["ST"] = pd.to_numeric(pd_file["ST"], errors="coerce")
    else:
        st.error("Column 'ST' not found.")

    if "Totals" in pd_file.columns:
        pd_file["Totals"] = pd.to_numeric(pd_file["Totals"], errors="coerce")
    else:
        st.error("Column 'Totals' not found.")

    st_sum = pd_file["ST"].sum(skipna=True)
    totals_sum = pd_file["Totals"].sum(skipna=True)

    # Convert back to strings for final display
    pd_file = pd_file.astype(str)

    # Convert "Work Day" column to datetime and then format as YYYY-MM-DD
    pd_file["Work Day"] = pd.to_datetime(pd_file["Work Day"], errors="coerce").dt.strftime("%Y-%m-%d")

    # Define the numeric columns
    numeric_columns = ["ST", "OT", "DT", "Other", "Holiday", "VA", "SDO", "Jury/Mil", "Totals"]

    # Convert the specified columns to float
    pd_file[numeric_columns] = pd_file[numeric_columns].apply(pd.to_numeric, errors="coerce")

    # Create the final summary row
    summary_row = {col: "" for col in pd_file.columns}
    summary_row["Work Day"] = "Pay Period Totals"
    summary_row["ST"] = str(st_sum)
    summary_row["Totals"] = str(totals_sum)

    # Append the summary row
    pd_file = pd.concat([pd_file, pd.DataFrame([summary_row])], ignore_index=True)

    # Display the final DataFrame
    st.write(pd_file)

    # Function to convert DataFrame to Excel with formatting
    def to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')

            # Access the workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']

            # Define a header format (black background, white text)
            header_format = workbook.add_format({
                'bold': True,
                'fg_color': 'black',
                'font_color': 'white'
            })

            # Apply the header format and set column widths
            for col_num, col_name in enumerate(df.columns):
                # Set the header format
                worksheet.write(0, col_num, col_name, header_format)

                # Calculate the max length for this column
                col_values = df[col_name].astype(str)
                max_len = max(
                    [len(str(col_name))] +
                    col_values.map(len).tolist()
                )
                # Add some buffer to the column width
                worksheet.set_column(col_num, col_num, max_len + 2)

        processed_data = output.getvalue()
        return processed_data

    excel_data = to_excel(pd_file)

    st.write("Download the transformed file:")
    st.download_button(
        label="Download file to Excel",
        data=excel_data,
        file_name='transformed_file.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )