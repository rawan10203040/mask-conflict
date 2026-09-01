# Excel Data Processing Tools

This repository contains two Streamlit applications for processing and updating Excel files.

## Applications

### 1. PMS – Excel Cleaning & Processing

**File:** `PMS.py`

This application processes Excel input files and performs the following:

* Upload multiple All Input Excel files.
* Upload multiple Low Priority Excel files.
* Search for `-9999999999` in:

  * `DistinctValues`
  * `ItemName`
* Identify `ItemId` values that need to be removed.
* Handle `Mask` rows separately.
* Create `PartNumberPartCompanyName`.
* Create `PartNumberCompanyName` for Low Priority files.
* Match `DieFamily` between the input files and Low Priority files.
* Search for `99999999` in `DieFamily`.
* Remove complete `ItemId` records when required.
* Remove only matching Mask rows when required.
* Generate cleaned output files.
* Generate deleted rows and ItemId lists.
* Split the final output when it exceeds 1,000,000 rows.
* Create a ZIP file containing all generated results.

### 2. QA Comment Updater

**File:** `QA_Comment_Updater.py`

This application updates the `QAComment` column based on:

* `FunctionName`
* `IsMultiValue`
* `HasBlankValue`

The application supports the following rules:

#### Packing

| IsMultiValue | HasBlankValue | QAComment  |
| ------------ | ------------- | ---------- |
| TRUE         | FALSE         | `ok`       |
| TRUE         | TRUE          | `null`     |
| FALSE        | FALSE         | `conflict` |
| FALSE        | TRUE          | `conflict` |

#### Other Functions

| IsMultiValue | HasBlankValue | QAComment  |
| ------------ | ------------- | ---------- |
| TRUE         | FALSE         | `conflict` |
| TRUE         | TRUE          | `conflict` |
| FALSE        | FALSE         | `ok`       |
| FALSE        | TRUE          | `null`     |

The application keeps the original `QAComment` when none of the defined conditions apply.

## Required Libraries

The applications use the following Python packages:

```text
streamlit
polars
fastexcel
openpyxl
xlsxwriter
```

These dependencies are listed in:

`requirements.txt`

## Project Structure

```text
PMS/
│
├── PMS.py
├── QA_Comment_Updater.py
├── requirements.txt
└── README.md
```

## Running Locally

Install the required packages:

```bash
pip install -r requirements.txt
```

Run the PMS application:

```bash
streamlit run PMS.py
```

Run the QA Comment Updater:

```bash
streamlit run QA_Comment_Updater.py
```

## Streamlit Deployment

The applications can be deployed using Streamlit Community Cloud.

For the PMS application:

```text
Main file path: PMS.py
```

For the QA Comment Updater:

```text
Main file path: QA_Comment_Updater.py
```

Branch:

```text
main
```

## Output Files

### PMS

The PMS application can generate:

* `Merged_Cleaned_Output.xlsx`
* `Merged_Cleaned_Output_Part_1.xlsx`
* `Merged_Cleaned_Output_Part_2.xlsx`
* `Deleted_ItemIds_Rows.xlsx`
* `Matched_Rows.xlsx`
* `ItemIds_To_Delete.xlsx`
* `Results.zip`

### QA Comment Updater

The QA application generates:

```text
OriginalFileName_Updated.xlsx
```

When multiple files are processed, they can be downloaded together as:

```text
Updated_Output_Files.zip
```

## Notes

Input Excel files must contain the required columns for the corresponding application.

The applications are designed to process Excel files directly through the Streamlit interface.
