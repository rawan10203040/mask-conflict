import streamlit as st
import polars as pl
import io
import zipfile


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="QA Comment Updater",
    page_icon="📝",
    layout="wide"
)


# ============================================================
# TITLE
# ============================================================

st.title("📝 QA Comment Updater")

st.write(
    "Upload one or more Excel files to update the QAComment column "
    "based on FunctionName, IsMultiValue, and HasBlankValue."
)


# ============================================================
# REQUIRED COLUMNS
# ============================================================

REQUIRED_COLUMNS = [
    "FunctionName",
    "IsMultiValue",
    "HasBlankValue",
    "QAComment"
]


# ============================================================
# PROCESS FUNCTION
# ============================================================

def process_file(uploaded_file):

    filename = uploaded_file.name

    try:

        # --------------------------------------------------------
        # Read Excel
        # --------------------------------------------------------

        file_bytes = uploaded_file.getvalue()

        df = pl.read_excel(
            io.BytesIO(file_bytes)
        )

    except Exception as e:

        return None, None, f"Error reading {filename}: {e}"


    # ------------------------------------------------------------
    # Check required columns
    # ------------------------------------------------------------

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:

        return (
            None,
            None,
            f"Required columns are missing: {missing_columns}"
        )


    # ============================================================
    # CLEAN DATA
    # ============================================================

    df = df.with_columns([

        # --------------------------------------------------------
        # FunctionName
        # --------------------------------------------------------

        pl.col("FunctionName")
        .cast(pl.Utf8, strict=False)
        .fill_null("")
        .str.strip_chars(),

        # --------------------------------------------------------
        # IsMultiValue
        # --------------------------------------------------------

        pl.col("IsMultiValue")
        .cast(pl.Utf8, strict=False)
        .fill_null("")
        .str.strip_chars()
        .str.to_uppercase(),

        # --------------------------------------------------------
        # HasBlankValue
        # --------------------------------------------------------

        pl.col("HasBlankValue")
        .cast(pl.Utf8, strict=False)
        .fill_null("")
        .str.strip_chars()
        .str.to_uppercase()
    ])


    # ============================================================
    # UPDATE QAComment
    # ============================================================

    function_name = (
        pl.col("FunctionName")
        .str.to_lowercase()
    )

    is_multi_value = pl.col("IsMultiValue")
    has_blank_value = pl.col("HasBlankValue")


    df = df.with_columns(

        pl.when(

            # ====================================================
            # PACKING
            # TRUE + FALSE = OK
            # ====================================================

            (function_name == "packing")
            &
            (is_multi_value == "TRUE")
            &
            (has_blank_value == "FALSE")

        )
        .then(
            pl.lit("ok")
        )


        # ========================================================
        # PACKING
        # TRUE + TRUE = NULL
        # ========================================================

        .when(

            (function_name == "packing")
            &
            (is_multi_value == "TRUE")
            &
            (has_blank_value == "TRUE")

        )
        .then(
            pl.lit("null")
        )


        # ========================================================
        # PACKING
        # FALSE + FALSE = CONFLICT
        # ========================================================

        .when(

            (function_name == "packing")
            &
            (is_multi_value == "FALSE")
            &
            (has_blank_value == "FALSE")

        )
        .then(
            pl.lit("conflict")
        )


        # ========================================================
        # PACKING
        # FALSE + TRUE = CONFLICT
        # ========================================================

        .when(

            (function_name == "packing")
            &
            (is_multi_value == "FALSE")
            &
            (has_blank_value == "TRUE")

        )
        .then(
            pl.lit("conflict")
        )


        # ========================================================
        # ANY FUNCTION EXCEPT PACKING
        #
        # TRUE + FALSE = CONFLICT
        # ========================================================

        .when(

            (function_name != "packing")
            &
            (is_multi_value == "TRUE")
            &
            (has_blank_value == "FALSE")

        )
        .then(
            pl.lit("conflict")
        )


        # ========================================================
        # ANY FUNCTION EXCEPT PACKING
        #
        # TRUE + TRUE = CONFLICT
        # ========================================================

        .when(

            (function_name != "packing")
            &
            (is_multi_value == "TRUE")
            &
            (has_blank_value == "TRUE")

        )
        .then(
            pl.lit("conflict")
        )


        # ========================================================
        # ANY FUNCTION EXCEPT PACKING
        #
        # FALSE + FALSE = OK
        # ========================================================

        .when(

            (function_name != "packing")
            &
            (is_multi_value == "FALSE")
            &
            (has_blank_value == "FALSE")

        )
        .then(
            pl.lit("ok")
        )


        # ========================================================
        # ANY FUNCTION EXCEPT PACKING
        #
        # FALSE + TRUE = NULL
        # ========================================================

        .when(

            (function_name != "packing")
            &
            (is_multi_value == "FALSE")
            &
            (has_blank_value == "TRUE")

        )
        .then(
            pl.lit("null")
        )


        # ========================================================
        # KEEP ORIGINAL QAComment
        # ========================================================

        .otherwise(
            pl.col("QAComment")
        )


        .alias("QAComment")
    )


    # ============================================================
    # CREATE OUTPUT FILE NAME
    # ============================================================

    if filename.lower().endswith(".xlsx"):

        output_name = (
            filename[:-5]
            + "_Updated.xlsx"
        )

    else:

        output_name = (
            filename
            + "_Updated.xlsx"
        )


    # ============================================================
    # WRITE EXCEL TO MEMORY
    # ============================================================

    output_buffer = io.BytesIO()

    try:

        df.write_excel(
            output_buffer
        )

    except Exception as e:

        return (
            None,
            None,
            f"Error creating output for {filename}: {e}"
        )


    output_buffer.seek(0)

    return (
        output_name,
        output_buffer.getvalue(),
        None
    )


# ============================================================
# FILE UPLOADER
# ============================================================

st.subheader("📂 Upload Excel File(s)")

uploaded_files = st.file_uploader(
    "Choose Excel file(s)",
    type=["xlsx"],
    accept_multiple_files=True
)


# ============================================================
# PROCESS BUTTON
# ============================================================

if uploaded_files:

    st.info(
        f"{len(uploaded_files)} file(s) selected."
    )

    if st.button(
        "🚀 Process Files",
        type="primary"
    ):

        generated_files = []

        errors = []

        progress = st.progress(0)

        status_text = st.empty()


        # ========================================================
        # PROCESS EACH FILE
        # ========================================================

        for index, uploaded_file in enumerate(uploaded_files):

            filename = uploaded_file.name

            status_text.write(
                f"Processing: **{filename}**"
            )


            output_name, output_bytes, error = process_file(
                uploaded_file
            )


            if error:

                errors.append(
                    f"{filename}: {error}"
                )

            else:

                generated_files.append(
                    (
                        output_name,
                        output_bytes
                    )
                )


            progress.progress(
                (index + 1)
                / len(uploaded_files)
            )


        status_text.empty()


        # ========================================================
        # DISPLAY ERRORS
        # ========================================================

        if errors:

            st.error("Some files could not be processed.")

            for error in errors:

                st.write(
                    f"❌ {error}"
                )


        # ========================================================
        # NO OUTPUT
        # ========================================================

        if len(generated_files) == 0:

            st.warning(
                "No files were generated."
            )


        # ========================================================
        # ONE OUTPUT FILE
        # ========================================================

        elif len(generated_files) == 1:

            output_name, output_bytes = (
                generated_files[0]
            )


            st.success(
                f"Finished successfully: {output_name}"
            )


            st.download_button(
                label="⬇️ Download Updated File",
                data=output_bytes,
                file_name=output_name,
                mime=(
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                )
            )


        # ========================================================
        # MULTIPLE OUTPUT FILES
        # ========================================================

        else:

            zip_buffer = io.BytesIO()


            with zipfile.ZipFile(
                zip_buffer,
                mode="w",
                compression=zipfile.ZIP_DEFLATED
            ) as zip_file:

                for output_name, output_bytes in generated_files:

                    zip_file.writestr(
                        output_name,
                        output_bytes
                    )


            zip_buffer.seek(0)


            st.success(
                f"Finished successfully. "
                f"{len(generated_files)} files were generated."
            )


            st.download_button(
                label="📦 Download All Results (ZIP)",
                data=zip_buffer.getvalue(),
                file_name="Updated_Output_Files.zip",
                mime="application/zip"
            )


            # ====================================================
            # SHOW GENERATED FILES
            # ====================================================

            st.subheader("📄 Generated Files")

            for output_name, _ in generated_files:

                st.write(
                    f"✅ {output_name}"
                )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "QA Comment Updater | Streamlit"
)