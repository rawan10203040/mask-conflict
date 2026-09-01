!pip install -q polars fastexcel openpyxl xlsxwriter
 
import polars as pl
from google.colab import files
import io
import zipfile
import os
 
# ==========================================
# Upload Excel files
# ==========================================
 
print("Upload output file(s)...")
 
uploaded = files.upload()
 
generated_files = []
 
 
# ==========================================
# Process each file
# ==========================================
 
for filename, content in uploaded.items():
 
    print(f"\nProcessing: {filename}")
 
    # Read Excel
    df = pl.read_excel(
        io.BytesIO(content)
    )
 
    # ======================================
    # Required columns
    # ======================================
 
    required = [
        "FunctionName",
        "IsMultiValue",
        "HasBlankValue",
        "QAComment"
    ]
 
    # Check columns
    if not all(
        c in df.columns
        for c in required
    ):
 
        print(
            f"Skipping {filename} - "
            "Required columns are missing."
        )
 
        print(
            "Available columns:"
        )
 
        print(df.columns)
 
        continue
 
 
    # ======================================
    # Clean data
    # ======================================
 
    df = df.with_columns([
 
        pl.col("FunctionName")
        .cast(pl.Utf8, strict=False)
        .fill_null("")
        .str.strip_chars(),
 
        pl.col("IsMultiValue")
        .cast(pl.Utf8, strict=False)
        .fill_null("")
        .str.strip_chars()
        .str.to_uppercase(),
 
        pl.col("HasBlankValue")
        .cast(pl.Utf8, strict=False)
        .fill_null("")
        .str.strip_chars()
        .str.to_uppercase()
    ])
 
 
    # ======================================
    # Update QAComment
    # ======================================
 
    df = df.with_columns(
 
        pl.when(
 
            # ------------------------------
            # Packing
            # TRUE + FALSE = OK
            # ------------------------------
 
            (pl.col("FunctionName")
             .str.to_lowercase()
             == "packing")
&
            (pl.col("IsMultiValue") == "TRUE")
&
            (pl.col("HasBlankValue") == "FALSE")
 
        )
        .then(pl.lit("ok"))
 
        # ------------------------------
        # Packing
        # TRUE + TRUE = NULL
        # ------------------------------
 
        .when(
 
            (pl.col("FunctionName")
             .str.to_lowercase()
             == "packing")
&
            (pl.col("IsMultiValue") == "TRUE")
&
            (pl.col("HasBlankValue") == "TRUE")
 
        )
        .then(pl.lit("null"))
 
        # ------------------------------
        # Packing
        # FALSE + FALSE = CONFLICT
        # ------------------------------
 
        .when(
 
            (pl.col("FunctionName")
             .str.to_lowercase()
             == "packing")
&
            (pl.col("IsMultiValue") == "FALSE")
&
            (pl.col("HasBlankValue") == "FALSE")
 
        )
        .then(pl.lit("conflict"))
 
        # ------------------------------
        # Packing
        # FALSE + TRUE = CONFLICT
        # ------------------------------
 
        .when(
 
            (pl.col("FunctionName")
             .str.to_lowercase()
             == "packing")
&
            (pl.col("IsMultiValue") == "FALSE")
&
            (pl.col("HasBlankValue") == "TRUE")
 
        )
        .then(pl.lit("conflict"))
 
        # =================================
        # Any Function except Packing
        # =================================
 
        # ------------------------------
        # TRUE + FALSE = CONFLICT
        # ------------------------------
 
        .when(
 
            (pl.col("FunctionName")
             .str.to_lowercase()
             != "packing")
&
            (pl.col("IsMultiValue") == "TRUE")
&
            (pl.col("HasBlankValue") == "FALSE")
 
        )
        .then(pl.lit("conflict"))
 
        # ------------------------------
        # TRUE + TRUE = CONFLICT
        # ------------------------------
 
        .when(
 
            (pl.col("FunctionName")
             .str.to_lowercase()
             != "packing")
&
            (pl.col("IsMultiValue") == "TRUE")
&
            (pl.col("HasBlankValue") == "TRUE")
 
        )
        .then(pl.lit("conflict"))
 
        # ------------------------------
        # FALSE + FALSE = OK
        # ------------------------------
 
        .when(
 
            (pl.col("FunctionName")
             .str.to_lowercase()
             != "packing")
&
            (pl.col("IsMultiValue") == "FALSE")
&
            (pl.col("HasBlankValue") == "FALSE")
 
        )
        .then(pl.lit("ok"))
 
        # ------------------------------
        # FALSE + TRUE = NULL
        # ------------------------------
 
        .when(
 
            (pl.col("FunctionName")
             .str.to_lowercase()
             != "packing")
&
            (pl.col("IsMultiValue") == "FALSE")
&
            (pl.col("HasBlankValue") == "TRUE")
 
        )
        .then(pl.lit("null"))
 
        # ------------------------------
        # Keep original value
        # ------------------------------
 
        .otherwise(
            pl.col("QAComment")
        )
 
        .alias("QAComment")
    )
 
 
    # ======================================
    # Save Updated File
    # ======================================
 
    if filename.lower().endswith(".xlsx"):
 
        output_name = filename[
            :-5
        ] + "_Updated.xlsx"
 
    else:
 
        output_name = filename + "_Updated.xlsx"
 
 
    df.write_excel(
        output_name
    )
 
    generated_files.append(
        output_name
    )
 
    print(
        f"Created: {output_name}"
    )
 
 
# ==========================================
# Download Results
# ==========================================
 
if len(generated_files) > 1:
 
    zip_name = "Updated_Output_Files.zip"
 
    with zipfile.ZipFile(
        zip_name,
        "w",
        zipfile.ZIP_DEFLATED
    ) as z:
 
        for f in generated_files:
 
            if os.path.exists(f):
 
                z.write(f)
 
    print(
        f"\nCreated ZIP: {zip_name}"
    )
 
    files.download(
        zip_name
    )
 
 
elif len(generated_files) == 1:
 
    print(
        f"\nDownloading: "
        f"{generated_files[0]}"
    )
 
    files.download(
        generated_files[0]
    )
 
 
else:
 
    print(
        "\nNo files were generated."
    )
 
 
print("\nFinished Successfully.")